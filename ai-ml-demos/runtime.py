# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
from functools import lru_cache
import json
import os
from pathlib import Path
import signal
from time import monotonic, sleep
from typing import NamedTuple

from telemetry import SOC_TEMPERATURE, SoCTemperature


RESOURCES = ContextVar('demo_resources')
STATISTICS = ContextVar('demo_statistics', default=None)
CPU_TEMPERATURE = SoCTemperature(sensor_name='cpu-thermal')
A55_TEMPERATURE = SoCTemperature(sensor_name='a55-thermal')
ANA_TEMPERATURE = SoCTemperature(sensor_name='ana-thermal')
CLOCK_SCALE = Path('/sys/bus/platform/drivers/galcore/gpu3DClockScale')
THERMAL_ROOT = Path('/sys/class/thermal')


class CameraUnavailable(RuntimeError):
    """An expected input condition, not a demo crash."""


def check_camera(platform, device=None):
    """Check the tested native sensor before allocating models or capture."""
    import subprocess
    device = device or ('/dev/video4' if platform == 'imx8mplus' else '/dev/video0')
    message = ('No camera is available. Connect the OV5640 with the board '
               'powered off, boot again, then retry. Image and video demos '
               'remain available.')
    if not Path(device).is_char_device():
        raise CameraUnavailable(message)
    if platform in ('imx93', 'imx95'):
        # ISI capture nodes can exist even when no camera sensor is connected.
        if not Path('/dev/media0').exists():
            raise CameraUnavailable(message)
        try:
            topology = subprocess.run(['media-ctl', '-d', '/dev/media0', '-p'],
                                      capture_output=True, text=True, timeout=3,
                                      check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CameraUnavailable('Camera could not be checked. Verify the '
                                    'BSP media-controller tools and retry.') from error
        sensor = 'ov5640 4-003c' if platform == 'imx93' else 'ov5640 2-003c'
        if topology.returncode or sensor not in topology.stdout:
            raise CameraUnavailable(message)
    return device


class ThermalLimits(NamedTuple):
    warm: float = 80
    pause: float = 82
    resume: float = 78


@lru_cache(maxsize=1)
def thermal_limits():
    """Read kernel policy; keep headroom and never write its trip points.

    Defaults remain conservative when a recognized SoC zone lacks a policy.
    The 95 C ceiling is our application limit, not a vendor specification.
    """
    pauses = []
    for zone in THERMAL_ROOT.glob('thermal_zone*'):
        try:
            name = (zone / 'type').read_text().strip()
        except OSError:
            continue
        if name not in ('soc-thermal', 'cpu-thermal', 'a55-thermal', 'ana-thermal'):
            continue
        passive, critical = [], []
        for path in zone.glob('trip_point_*_type'):
            try:
                kind = path.read_text().strip()
                value = float(path.with_name(path.name.removesuffix('type') + 'temp').read_text()) / 1000
            except (OSError, ValueError):
                continue
            if 40 <= value <= 150:
                if kind == 'passive':
                    passive.append(value)
                elif kind == 'critical':
                    critical.append(value)
        if not passive:
            return ThermalLimits()
        pause = min(min(passive) - 3, 95)
        if critical:
            pause = min(pause, min(critical) - 10)
        pauses.append(pause)
    if not pauses:
        return ThermalLimits()
    pause = min(pauses)
    return ThermalLimits(warm=pause - 2, pause=pause, resume=pause - 4)


def warm_up_model(interpreter):
    """Exclude first-invocation graph compilation from measured inference."""
    import numpy as np
    startup_step('Warming up the NPU with a model-sized frame')
    source = interpreter.get_input_details()[0]
    interpreter.set_tensor(source['index'], np.zeros(source['shape'], source['dtype']))
    interpreter.invoke()
    startup_step('Opening video; waiting for the first frame')


@lru_cache(maxsize=1)
def display_size():
    """Use display pixels, not source-video pixels, for presentation."""
    size = os.environ.get('VAR_AI_DISPLAY_SIZE')
    if not size:
        try:
            size = Path('/sys/class/graphics/fb0/virtual_size').read_text()
        except OSError:
            return (800, 480)
    try:
        width, height = (int(part) for part in
                         size.strip().lower().replace('x', ',').split(','))
        if 160 <= width <= 7680 and 120 <= height <= 4320:
            return width, height
    except (ValueError, TypeError):
        pass
    return (800, 480)


def viewport_geometry(shape, target):
    """Return the image rectangle inside an aspect-preserving viewport."""
    height, width = shape[:2]
    target_width, target_height = target
    if min(height, width, target_width, target_height) <= 0:
        raise ValueError('Image and display dimensions must be positive')
    scale = min(target_width / width, target_height / height)
    resized_width = max(1, min(target_width, round(width * scale)))
    resized_height = max(1, min(target_height, round(height * scale)))
    return ((target_width - resized_width) // 2,
            (target_height - resized_height) // 2,
            resized_width, resized_height)


@lru_cache(maxsize=16)
def video_source_size(source):
    """Read original stream dimensions, independently of working/display size."""
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstPbutils', '1.0')
    from gi.repository import Gst, GstPbutils
    Gst.init(None)
    info = GstPbutils.Discoverer.new(3 * Gst.SECOND).discover_uri(
        Path(source).resolve().as_uri())
    streams = info.get_video_streams()
    if not streams:
        raise RuntimeError('The selected file has no video stream')
    width, height = streams[0].get_width(), streams[0].get_height()
    if width <= 0 or height <= 0:
        raise RuntimeError('The selected video has invalid stream dimensions')
    return width, height


def video_work_size(source):
    """Decode native video, then scale in the BSP converter for processing.

    Native-frame mode retains the older one-step model resize for comparison.
    """
    if os.environ.get('VAR_AI_NATIVE_FRAMES') == '1':
        return None
    width, height = video_source_size(source)
    _, _, out_width, out_height = viewport_geometry((height, width), display_size())
    if out_width >= width and out_height >= height:
        return None
    print(f'Video preprocessing: {width}x{height} decoded, '
          f'{out_width}x{out_height} accelerated working frame.', flush=True)
    return out_width, out_height


def display_view(frame, target=None):
    """Fit a copy for annotation after inference; keep the source untouched."""
    import cv2
    import numpy as np

    target = target or display_size()
    x, y, width, height = viewport_geometry(frame.shape, target)
    canvas = np.zeros((target[1], target[0], frame.shape[2]), dtype=frame.dtype)
    canvas[y:y + height, x:x + width] = (
        frame if frame.shape[:2] == (height, width)
        else cv2.resize(frame, (width, height)))
    return canvas, (x, y, width, height)


def display_box(box, area):
    """Project normalized model coordinates into the letterboxed image."""
    y0, x0, y1, x1 = box
    x, y, width, height = area
    return (x + round(max(0., min(1., x0)) * (width - 1)),
            y + round(max(0., min(1., y0)) * (height - 1)),
            x + round(max(0., min(1., x1)) * (width - 1)),
            y + round(max(0., min(1., y1)) * (height - 1)))


def startup_step(message, ready=False):
    """Report completed/starting stages, never invented percentages."""
    print('VAR_DEMO_STARTUP ' + json.dumps({
        'message': message, 'ready': bool(ready)}), flush=True)


class StartupProgress:
    def __init__(self, expected=False):
        self.message = 'Starting process'
        self.ready = not expected
        self.offset = 0
        self.pending = b''

    def read(self, path):
        with Path(path).open('rb') as output:
            output.seek(0, 2)
            end = output.tell()
            if end < self.offset:
                self.offset, self.pending = 0, b''
            if end - self.offset > 65536:
                self.offset, self.pending = end - 65536, b''
            output.seek(self.offset)
            data = self.pending + output.read(65536)
            self.offset = output.tell()
        lines = data.split(b'\n')
        self.pending = lines.pop()[-4096:]
        for line in lines:
            if not line.startswith(b'VAR_DEMO_STARTUP '):
                continue
            try:
                event = json.loads(line.removeprefix(b'VAR_DEMO_STARTUP '))
                if not isinstance(event.get('message'), str):
                    continue
                if not isinstance(event.get('ready'), bool):
                    continue
                self.message = ''.join(c for c in event['message'][:240]
                                       if c.isprintable())
                self.ready = event['ready']
            except (ValueError, TypeError, AttributeError):
                continue


class RunStatistics:
    def __init__(self):
        self.frames = 0
        self.total_inference = 0.0
        self.first_frame = None
        self.last_frame = None
        self.soc_peak = None

    def record(self, seconds):
        now = monotonic()
        if self.first_frame is None:
            self.first_frame = now - seconds
        self.last_frame = now
        self.frames += 1
        self.total_inference += seconds
        value = temperature()
        if value is not None:
            self.soc_peak = max(value, self.soc_peak or value)

    def summary(self, ended_at=None):
        elapsed = ((self.last_frame if ended_at is None else ended_at)
                   - self.first_frame
                   if self.frames else 0)
        return {
            'frames': self.frames,
            'processing_fps': (self.frames / elapsed
                               if self.frames > 1 and elapsed > 0 else None),
            'inference_ms': (1000 * self.total_inference / self.frames
                             if self.frames else None),
            'soc_peak_c': self.soc_peak,
        }


def record_inference(seconds):
    statistics = STATISTICS.get()
    if statistics is not None:
        statistics.record(seconds)


def clock_is_limited():
    try:
        return int(CLOCK_SCALE.read_text()) == 1
    except (OSError, ValueError):
        return False


def temperature():
    values = [SOC_TEMPERATURE.read(), CPU_TEMPERATURE.read(),
              A55_TEMPERATURE.read(), ANA_TEMPERATURE.read()]
    return max((value for value in values if value is not None), default=None)


def register_cleanup(callback, *args):
    RESOURCES.get().callback(callback, *args)


def prepare_opencv_display():
    # The tested BSPs ship Qt's xcb plugin, not its Wayland plugin. Direct
    # execution must use XWayland too, not depend on the launcher's exports.
    if Path('/tmp/.X11-unix/X0').is_socket():
        os.environ.setdefault('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')
        os.environ.setdefault('DISPLAY', ':0')
        platform = os.environ.get('QT_QPA_PLATFORM', '')
        if not platform or platform.startswith('wayland'):
            os.environ['QT_QPA_PLATFORM'] = 'xcb'


@contextmanager
def demo_session():
    prepare_opencv_display()
    import cv2

    def terminate(_signal, _frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, terminate)
    statistics = RunStatistics()
    stats_token = STATISTICS.set(statistics)
    try:
        with ExitStack() as resources:
            token = RESOURCES.set(resources)
            resources.callback(cv2.destroyAllWindows)
            from vision_window import destroyAllWindows
            resources.callback(destroyAllWindows)
            try:
                if clock_is_limited():
                    raise RuntimeError(
                        'GPU/NPU is thermally limited. Let the board cool '
                        'before restarting the demo; check heatsink and fan.'
                    )
                yield
            except CameraUnavailable as error:
                print(f'Camera unavailable. {error}', flush=True)
            except KeyboardInterrupt:
                pass
            finally:
                RESOURCES.reset(token)
    finally:
        STATISTICS.reset(stats_token)
        print('VAR_AI_STATS ' + json.dumps(statistics.summary(monotonic())),
              flush=True)
        signal.signal(signal.SIGTERM, previous)


def managed_capture(source):
    import cv2

    backend = (
        cv2.CAP_GSTREAMER if isinstance(source, str) and ' ! ' in source
        else cv2.CAP_ANY
    )
    capture = cv2.VideoCapture(source, backend, [
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
        cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000,
    ])
    register_cleanup(capture.release)
    if not capture.isOpened():
        raise RuntimeError('Cannot open the requested camera or video stream')
    return capture


class ThermalPacer:
    """Bound continuous load using the shared, read-only kernel-aware policy."""

    def __init__(self, clock_paced=False, limits=None):
        self.last_frame = monotonic()
        self.cooling = False
        self.warm = False
        self.next_check = 0
        self.limited = False
        self.clock_paced = clock_paced
        self.limits = limits if limits is not None else thermal_limits()

    def wait(self, poll_stop=lambda: False, on_cooling=None):
        while True:
            now = monotonic()
            if now >= self.next_check:
                self.limited = clock_is_limited()
                self.next_check = now + 1
            value = temperature()
            if value is not None:
                if value >= self.limits.warm:
                    if not self.warm:
                        print(f'Thermal rate limit: hottest SoC zone {value:.1f} C; '
                              'processing capped at 15 FPS.', flush=True)
                    self.warm = True
                elif value < self.limits.resume:
                    if self.warm:
                        print('Thermal rate limit cleared: normal processing resumed.',
                              flush=True)
                    self.warm = False
            if self.limited or (value is not None and value >= self.limits.pause):
                if not self.cooling:
                    if on_cooling:
                        on_cooling(True)
                    print(f'Cooling: inference paused until below {self.limits.resume:g} C.',
                          flush=True)
                self.cooling = True
            if self.cooling:
                if not self.limited and value is not None and value < self.limits.resume:
                    self.cooling = False
                    if on_cooling:
                        on_cooling(False)
                    print('Cooling complete: inference resumed.', flush=True)
                else:
                    if poll_stop():
                        return False
                    sleep(0.1)
                    continue
            rate = 15 if self.warm else None if self.clock_paced else 30
            remaining = (1 / rate - (now - self.last_frame)) if rate else 0
            if remaining > 0:
                sleep(remaining)
            self.last_frame = monotonic()
            return not poll_stop()
