#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Single-hand palm detection, landmarks and geometric gestures."""
import argparse
from pathlib import Path
import sys
from time import monotonic

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import vision_window
from runtime import demo_session, managed_capture, record_inference, ThermalPacer
from runtime import startup_step
from runtime import display_view
from runtime import check_camera
from telemetry import draw_soc_temperature, SOC_TEMPERATURE
from gestures import classify, SmoothLandmarks, StableGesture
from hand_tracker import HandTracker
import vision_overlay as ui

TITLE = 'Variscite | Hand and gestures'
COLOR = ui.color_for('person')
TEXT = (242, 244, 246)
PANEL = (24, 28, 32)
CONNECTIONS = [(0, 5), (5, 9), (9, 13), (13, 17), (17, 0)]
for chain in ((0, 1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12),
              (13, 14, 15, 16), (17, 18, 19, 20)):
    CONNECTIONS.extend(zip(chain, chain[1:]))


def display_frame(frame, windowed):
    if windowed:
        return frame
    try:
        width, height = map(int, Path(
            '/sys/class/graphics/fb0/virtual_size').read_text().split(','))
    except (OSError, ValueError):
        return frame
    if not (0 < width <= 7680 and 0 < height <= 4320):
        return frame
    rows, columns = frame.shape[:2]
    ratio = width / height
    if columns / rows > ratio:
        cropped = max(1, round(rows * ratio))
        left = (columns - cropped) // 2
        frame = frame[:, left:left + cropped]
    else:
        cropped = max(1, round(columns / ratio))
        top = (rows - cropped) // 2
        frame = frame[top:top + cropped]
    return cv2.resize(frame, (width, height))


def draw(frame, points, gesture, fps, inference, camera_size=None):
    source_height, source_width = frame.shape[:2]
    frame, (x, y, width, height) = display_view(frame)
    if points is not None:
        points = np.asarray(points) * np.array(
            [width / source_width, height / source_height]) + np.array([x, y])
        # Clip drawing coordinates, never wrap overflowing integer values.
        bounds = np.array([frame.shape[1] - 1, frame.shape[0] - 1])
        xy = np.clip(points, 0, bounds).astype(int)
        for a, b in CONNECTIONS:
            cv2.line(frame, tuple(xy[a]), tuple(xy[b]), COLOR, 2, cv2.LINE_AA)
        for point in xy:
            cv2.circle(frame, tuple(point), 3, TEXT, -1, cv2.LINE_AA)
    ui.results(frame, [(gesture, None)])
    ui.statistics(frame, inference * 1000, fps)
    if camera_size is not None:
        ui.camera_resolution(frame, camera_size)
    ui.model(frame, 'Palm + 21 landmarks | VIP8000')
    draw_soc_temperature(frame, PANEL, TEXT)
    return frame


@demo_session()
def run(args):
    startup_step('Checking camera and model assets')
    if not args.sample:
        check_camera('imx8mplus', args.camera)
        if (not args.camera.startswith('/dev/video') or
                not args.camera.removeprefix('/dev/video').isdigit()):
            raise ValueError('Expected a /dev/video camera device')
        if not Path(args.camera).is_char_device():
            raise RuntimeError(f'Camera unavailable: {args.camera}')
    print('Preparing palm and landmark models; first inference may take '
          'several seconds.', flush=True)
    pacer = ThermalPacer()
    startup_step('Checking thermal readiness')
    if not pacer.wait():
        return
    tracker = HandTracker(
        str(ROOT / 'model/palm.tflite'), str(ROOT / 'model/landmark.tflite'),
        str(ROOT / 'model/anchors.csv'), '/usr/lib/libvx_delegate.so',
        box_enlarge=1.3, progress=startup_step)
    reference = cv2.imread(str(ROOT / 'media/hand.bmp'))
    if reference is None:
        raise RuntimeError('Missing or unreadable hand sample')
    # Prepare both delegates before capture. Otherwise the first hand in a
    # long-running feed triggers landmark compilation and freezes playback.
    points, _ = tracker(cv2.cvtColor(reference, cv2.COLOR_BGR2RGB))
    if points is None:
        raise RuntimeError('Model warmup failed to detect the reference hand')
    print('Models ready. Starting capture.', flush=True)
    sample = None
    if args.sample:
        sample = reference
    else:
        startup_step('Models ready; opening camera')
        capture_width, capture_height = map(int, args.resolution.split('x'))
        pipeline = (f'v4l2src device={args.camera} ! '
                    f'video/x-raw,width={capture_width},height={capture_height},framerate=30/1 ! '
                    'queue leaky=downstream max-size-buffers=1 ! '
                    'videoconvert ! video/x-raw,format=BGR ! '
                    'appsink max-buffers=1 drop=true')
        capture = managed_capture(pipeline)
    startup_step('Waiting for the first valid frame')
    stable = StableGesture()
    smooth = SmoothLandmarks()
    started = monotonic()
    previous = started
    fps = 0.0
    window = False
    next_log = started
    ready = False
    while not args.duration or monotonic() - started < args.duration:
        if not pacer.wait(lambda: not args.headless and vision_window.waitKey(1) == 27):
            break
        if sample is not None:
            frame = sample.copy()
        else:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError('Camera stopped delivering frames')
        if not args.headless and not args.sample:
            frame = display_frame(frame, args.windowed)
        points, _ = tracker(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        record_inference(tracker.inference_seconds)
        points = smooth.update(points)
        now = monotonic()
        fps = .8 * fps + .2 / max(now - previous, 1e-6)
        previous = now
        gesture = stable.update(classify(points))
        if args.headless:
            if not ready:
                startup_step('Inference and capture ready', ready=True)
                ready = True
            if now >= next_log:
                print(f'gesture={gesture}; fps={fps:.1f}; '
                      f'inference_ms={tracker.inference_seconds * 1000:.1f}',
                      f'soc_c={SOC_TEMPERATURE.read()}',
                      flush=True)
                next_log = now + 1
            continue
        frame = draw(frame, points, gesture, fps, tracker.inference_seconds,
                     camera_size=None if args.sample else (capture_width, capture_height))
        if not window:
            vision_window.namedWindow(TITLE, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
            if not args.windowed:
                vision_window.setWindowProperty(TITLE, cv2.WND_PROP_FULLSCREEN,
                                      cv2.WINDOW_FULLSCREEN)
            window = True
        vision_window.imshow(TITLE, frame)
        if not ready:
            vision_window.waitKey(1)
            startup_step('Video displayed; demo ready', ready=True)
            ready = True
        if vision_window.waitKey(1) == 27:
            break


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', default='/dev/video4')
    parser.add_argument('--resolution', default='640x480',
                        choices=['720x480', '640x480', '1280x720', '1920x1080'])
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--duration', type=float, default=0)
    args = parser.parse_args()
    if args.duration < 0 or not np.isfinite(args.duration):
        parser.error('--duration must be finite and non-negative')
    run(args)


if __name__ == '__main__':
    main()
