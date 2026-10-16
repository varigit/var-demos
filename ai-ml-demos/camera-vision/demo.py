#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from time import monotonic

import cv2
import numpy as np
from tflite_runtime.interpreter import Interpreter, load_delegate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vision_window
from runtime import (demo_session, managed_capture, record_inference,
                     register_cleanup, startup_step, ThermalPacer,
                     display_view, display_box, video_work_size, video_source_size,
                     display_size, viewport_geometry)
from runtime import check_camera, CameraUnavailable
from telemetry import SoCTemperature
import vision_overlay as ui
from postprocess import decode_postprocessed, decode_ssdlite
from face import load_face_model, prepare_face_input, decode_faces
from segmentation import (load_segmentation_model, prepare_segmentation_input,
                          decode_segmentation, read_segmentation, paint_segmentation, legend)
from people_segmentation import (load_people_model, prepare_people_input, read_people,
                                 legend as people_legend)

ROOT = Path(__file__).resolve().parent
COLORS = [(52, 211, 153), (245, 189, 66), (223, 147, 70), (194, 133, 246)]


def capture_tail(video):
    # OpenCV discovers manual-pipeline sinks by name, unlike our GI reader.
    name = 'frames' if video else 'opencvsink'
    return ('videoconvert ! video/x-raw,format=BGR ! '
            f'appsink name={name} max-buffers=1 drop=true')


def gpu_video_conversion(size=None):
    # Force a GL render before download. The BSP's direct conversion path
    # negotiates RGBA but can return entirely zeroed CPU pixels. Native size
    # is the default; scaled output is opt-in on MX95 pending a cooled retest.
    dimensions = f',width={size[0]},height={size[1]}' if size else ''
    return ('glupload ! glcolorconvert ! glcolorscale ! '
            f'video/x-raw(memory:GLMemory),format=RGBA{dimensions} ! gldownload ! '
            'video/x-raw,format=RGBA ! ')


def face_camera_conversion(platform, size):
    if platform == 'imx8mplus':
        converter, pixel_format = 'imxvideoconvert_g2d', 'RGBx'
    elif platform == 'imx93':
        converter, pixel_format = 'imxvideoconvert_pxp', 'BGR'
    else:
        return ''
    return (f'{converter} ! video/x-raw,format={pixel_format},'
            f'width={size[0]},height={size[1]} ! ')


def video_decoder(platform):
    if platform == 'imx93':
        return 'avidemux ! jpegdec'
    if platform == 'imx8mplus':
        return 'qtdemux ! h264parse ! decodebin'
    # Automatic DMA_DRM import returned future/stale images despite increasing
    # PTS. MMAP NV12 plus GL upload was checked against a CPU-decoded reference.
    return ('qtdemux ! h264parse ! v4l2h264dec capture-io-mode=2 ! '
            'video/x-raw,format=NV12')


def board():
    compatible = Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
    for name, identifier in (('imx8mplus', 'imx8mp'), ('imx93', 'imx93'),
                             ('imx95', 'imx95')):
        if ('fsl,' + identifier).encode() in compatible:
            return name
    raise RuntimeError('This demo requires i.MX 8M Plus, i.MX 93 or i.MX 95')


def configure_camera(platform, device, resolution):
    if platform == 'imx8mplus':
        if device != '/dev/video4':
            raise RuntimeError('Only the tested MPlus OV5640 /dev/video4 is supported')
        return
    if device != '/dev/video0':
        raise RuntimeError('Only the tested OV5640 /dev/video0 is supported')
    if platform == 'imx93':
        topology = subprocess.check_output(['media-ctl', '-p'], text=True)
        if 'ov5640 4-003c' not in topology:
            raise RuntimeError('The tested MX93 OV5640 camera was not found')
        subprocess.run(['media-ctl', '-V',
            f'"ov5640 4-003c":0 [fmt:UYVY8_1X16/{resolution} field:none]'],
            check=True)
        return
    if not Path('/dev/media0').exists():
        raise RuntimeError('MX95 camera media-controller is missing. Check the '
                           'OV5640 cable with the board powered off and inspect '
                           'the kernel sensor probe errors before retrying.')
    topology = subprocess.check_output(['media-ctl', '-p'], text=True)
    sensor = 'ov5640 2-003c'
    if sensor not in topology:
        raise RuntimeError('The tested MX95 CSI0 OV5640 camera was not found')
    subprocess.run(['media-ctl', '-l',
        f'"{sensor}":0 -> "csidev-4ad30000.csi":0 [1]'], check=True)
    pads = [(sensor, 0), ('csidev-4ad30000.csi', 0),
            ('4ac10000.syscon:formatter@20', 0), ('crossbar', 2)]
    pads.extend((f'mxc_isi.{index}', 0) for index in range(8))
    pads.append(('mxc_isi.0', 1))
    for entity, pad in pads:
        subprocess.run(['media-ctl', '-V',
            f'"{entity}":{pad} [fmt:UYVY8_1X16/{resolution} field:none]'],
            check=True)


def load_model(platform, task):
    if task == 'people':
        return load_people_model(ROOT, platform)
    if task == 'face':
        return load_face_model(ROOT, platform)
    if task == 'segmentation':
        return load_segmentation_model(ROOT, platform)
    if platform == 'imx8mplus':
        raise RuntimeError('Use the existing MPlus classification/detection demos')
    suffix = 'vela' if platform == 'imx93' else 'neutron'
    filename = ('mobilenet' if task == 'classification' else 'ssd')
    delegate = ('ethosu' if platform == 'imx93' else 'neutron')
    startup_step(f'Loading {filename} and {delegate} delegate')
    interpreter = Interpreter(
        model_path=str(ROOT / 'model' / f'{filename}_{suffix}.tflite'),
        num_threads=1, experimental_delegates=[load_delegate(
            f'/usr/lib/lib{delegate}_delegate.so')])
    interpreter.allocate_tensors()
    source = interpreter.get_input_details()[0]
    outputs = interpreter.get_output_details()
    ops = interpreter._get_ops_details()
    custom = 'ethos-u' if platform == 'imx93' else 'NeutronGraph'
    if (source['dtype'] != np.uint8
            or not any(op['op_name'] == custom for op in ops)
            or not any(op['op_name'] == 'DELEGATE'
                       and source['index'] in op['inputs'] for op in ops)):
        raise RuntimeError('Expected compiled uint8 model delegated to its NPU')
    labels_file = 'classification-labels.txt' if task == 'classification' else (
        'detection-labels.txt' if platform == 'imx93' else 'coco-labels.txt')
    lines = (ROOT / 'model' / labels_file).read_text().splitlines()
    if task == 'detection' and platform == 'imx93':
        labels = {int(match[1]): match[2].strip() for line in lines
                  if (match := re.match(r'\s*(\d+)\s+(.+)', line))}
    elif task == 'detection':
        # NXP coco_labels.txt omits the background at output class zero.
        labels = dict(enumerate(lines, start=1))
    else:
        labels = dict(enumerate(lines))
    if task == 'classification' and len(labels) != outputs[0]['shape'][-1]:
        raise RuntimeError('Classification labels do not match model output')
    priors = None
    if task == 'detection' and platform == 'imx95':
        priors = np.loadtxt(ROOT / 'model/box-priors.txt')
        if priors.shape != (4, 1917) or len(labels) != 90:
            raise RuntimeError('Expected SSD-Lite anchors and 90 COCO labels')
    startup_step('Warming up the NPU with a model-sized frame')
    interpreter.set_tensor(source['index'], np.zeros(source['shape'], np.uint8))
    interpreter.invoke()
    return interpreter, source, outputs, labels, priors




def overlay(frame, detections, labels, title, fps, ms, thermal, sensor,
            box_area=None, faces=False):
    height, width = frame.shape[:2]
    box_area = box_area or (0, 0, width, height)
    for box, class_id, score in detections:
        left, top, right, bottom = display_box(box, box_area)
        ui.box(frame, (left, top, right, bottom),
               labels.get(class_id, 'object'), score, show_label=not faces)
    if faces:
        ui.results(frame, [(f'Faces detected: {len(detections)}', None)])
    ui.statistics(frame, ms, fps)
    ui.model(frame, title)
    ui.temperature(frame, thermal.read())


@demo_session()
def run(args):
    platform = board()
    args.camera = args.camera or ('/dev/video4' if platform == 'imx8mplus'
                                 else '/dev/video0')
    if not args.video and not args.image:
        try:
            check_camera(platform, args.camera)
        except CameraUnavailable as error:
            print(f'Camera unavailable. {error}', flush=True)
            return
    pacer = ThermalPacer(clock_paced=bool(args.video))
    # Do not start a decoder that keeps the GPU busy while waiting to cool.
    if not pacer.wait():
        return
    interpreter, source, outputs, labels, priors = load_model(platform, args.task)
    size = (int(source['shape'][2]), int(source['shape'][1]))
    if args.image:
        still_image = cv2.imread(args.image)
        if still_image is None:
            raise RuntimeError('Cannot read the selected image')
    elif args.video:
        path = Path(args.video).resolve()
        if not path.is_file():
            raise RuntimeError('Selected video does not exist')
        location = str(path).replace('\\', '\\\\').replace('"', '\\"')
        decoder = video_decoder(platform)
        # Keep the previously validated MX95 native-frame path as the default
        # until scaled EGL output is retested with adequate cooling.
        working_size = (None if platform == 'imx95' and
                        os.environ.get('VAR_AI_ACCELERATED_VIDEO') != '1'
                        else video_work_size(path))
        pipeline = f'filesrc location="{location}" ! {decoder} ! '
        if platform == 'imx95':
            runtime = Path(os.environ.setdefault('XDG_RUNTIME_DIR', '/run/user/0'))
            sockets = sorted(path for path in runtime.glob('wayland-*')
                             if path.is_socket())
            if not sockets:
                raise RuntimeError('MX95 GPU video conversion needs Wayland')
            os.environ.setdefault('WAYLAND_DISPLAY', sockets[0].name)
            os.environ.setdefault('GST_GL_PLATFORM', 'egl')
            os.environ.setdefault('GST_GL_WINDOW', 'wayland')
            os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
            pipeline += gpu_video_conversion(working_size)
        elif working_size:
            converter = ('imxvideoconvert_g2d' if platform == 'imx8mplus'
                         else 'imxvideoconvert_pxp')
            pixel_format = 'RGBx' if platform == 'imx8mplus' else 'BGR'
            pipeline += (f'{converter} ! video/x-raw,format={pixel_format},'
                         f'width={working_size[0]},height={working_size[1]} ! ')
    else:
        resolution = args.resolution or ('1280x720' if platform == 'imx95' else
                                        '720x480' if platform == 'imx8mplus' else '640x480')
        configure_camera(platform, args.camera, resolution)
        width, height = map(int, resolution.split('x'))
        dimensions = f'width={width},height={height}'
        if platform == 'imx95':
            dimensions = 'format=YUY2,' + dimensions
        pipeline = (f'v4l2src device={args.camera} ! '
                    f'video/x-raw,{dimensions} ! ')
    # A leaky queue BEFORE a clocked video sink discards the clip while it is
    # being decoded and leaves a future-timestamped final frame waiting. Keep
    # files clocked, and drop only late sink samples. Live cameras may leak.
    if not args.video and not args.image:
        pipeline += 'queue leaky=downstream max-size-buffers=1 ! '
        if args.task in ('face', 'segmentation', 'people'):
            _, _, work_width, work_height = viewport_geometry(
                (height, width, 3), display_size())
            pipeline += face_camera_conversion(platform, (work_width, work_height))
    if not args.image:
        pipeline += capture_tail(bool(args.video))
        startup_step('Opening video; waiting for the first frame')
    if args.image:
        cap = None
    elif args.video:
        from capture import VideoCapture
        cap = VideoCapture(pipeline)
        register_cleanup(cap.release)
    else:
        cap = managed_capture(pipeline)
    thermal = SoCTemperature(sensor_name=(
        'cpu-thermal' if platform == 'imx93' else
        'soc-thermal' if platform == 'imx8mplus' else 'a55-thermal'))
    started, frames = monotonic(), 0
    video_size = video_source_size(path) if args.video else None
    # Caps above require the selected capture mode. Face conversion may resize
    # afterward, so cap/frame dimensions are not the camera's resolution.
    camera_size = (width, height) if not args.video and not args.image else None
    title = ('Selfie Segmenter | People' if args.task == 'people' else
             'DeepLabV3 | People and vehicles' if args.task == 'segmentation' else
             'UltraFace Slim' if args.task == 'face' else
             'MobileNet V1' if args.task == 'classification' else
             'SSD MobileNet V1' if platform == 'imx93' else 'SSD-Lite V2')
    title += ' | ' + ('Ethos-U65' if platform == 'imx93' else
                      'VIP8000' if platform == 'imx8mplus' else 'Neutron')
    most_faces = 0
    while not args.seconds or monotonic() - started < args.seconds:
        def stop_requested():
            return (bool(args.seconds and monotonic() - started >= args.seconds)
                    or (pacer.cooling and not args.headless and frames > 0
                        and vision_window.waitKey(1) & 0xff == 27))

        if not pacer.wait(stop_requested, cap.set_paused if args.video else None):
            break
        ok, frame = ((True, still_image.copy()) if args.image else cap.read())
        if not ok:
            if args.video and frames:
                break
            raise RuntimeError('Capture stopped delivering frames')
        rgb = cv2.cvtColor(cv2.resize(frame, size), cv2.COLOR_BGR2RGB)
        tensor = (prepare_face_input(rgb, source) if args.task == 'face' else
                  prepare_people_input(rgb, source) if args.task == 'people' else
                  prepare_segmentation_input(rgb, source) if args.task == 'segmentation'
                  else rgb[None])
        interpreter.set_tensor(source['index'], tensor)
        before = monotonic()
        interpreter.invoke()
        ms = (monotonic() - before) * 1000
        record_inference(ms / 1000)
        # Segmentation validates its large score tensor once, through a
        # temporary view; other tasks retain their small owned output arrays.
        classes = (read_people(interpreter, outputs[0], args.threshold) if args.task == 'people' else
                   read_segmentation(interpreter, outputs[0]) if args.task == 'segmentation' else None)
        values = [] if classes is not None else [interpreter.get_tensor(item['index']) for item in outputs]
        if not all(np.isfinite(value).all() for value in values):
            raise RuntimeError('Invalid model output')
        detections = []
        if args.task == 'face':
            detections = decode_faces(values[0], args.threshold)
            most_faces = max(most_faces, len(detections))
        elif args.task == 'detection':
            detections = (decode_postprocessed(values) if priors is None else
                          decode_ssdlite(values[0], values[1], priors))
        frames += 1
        if frames == 1:
            if not args.headless:
                vision_window.namedWindow(title, cv2.WINDOW_NORMAL)
                if not args.windowed:
                    vision_window.setWindowProperty(title, cv2.WND_PROP_FULLSCREEN,
                                          cv2.WINDOW_FULLSCREEN)
        if args.headless:
            if frames == 1:
                startup_step('Frames and NPU inference ready', ready=True)
            if args.image:
                break
            continue
        frame, box_area = display_view(frame)
        if classes is not None:
            paint_segmentation(frame, classes, box_area)
            (people_legend if args.task == 'people' else legend)(frame)
        overlay(frame, detections, labels, title,
                None if args.image else frames / max(monotonic() - started, .001), ms, thermal, 'CPU',
                box_area, faces=args.task == 'face')
        if video_size is not None:
            ui.video_resolution(frame, video_size)
        elif camera_size is not None:
            ui.camera_resolution(frame, camera_size)
        if args.task == 'classification':
            scores = values[0][0].astype(np.float32)
            scale, zero = outputs[0]['quantization']
            if scale:
                scores = (scores - zero) * scale
            ui.results(frame, [(labels[int(index)], float(scores[index]))
                               for index in np.argsort(scores)[-3:][::-1]])
        vision_window.imshow(title, frame)
        if frames == 1:
            startup_step('Frames and NPU inference ready', ready=True)
        if args.image:
            while not args.seconds or monotonic() - started < args.seconds:
                if vision_window.waitKey(50) & 0xff == 27:
                    break
                if vision_window.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
                    break
            break
        if vision_window.waitKey(1) & 0xff == 27:
            break
    if not frames:
        raise RuntimeError('No frames processed')
    print(f'Processed {frames} frames in {monotonic() - started:.2f} seconds',
          flush=True)
    if args.task == 'face':
        print(f'Maximum faces in a frame: {most_faces}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', choices=['classification', 'detection', 'face', 'segmentation', 'people'],
                        default='detection')
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument('--camera')
    sources.add_argument('--video')
    sources.add_argument('--image')
    parser.add_argument('--resolution', choices=['720x480', '640x480', '1280x720', '1920x1080'])
    parser.add_argument('--threshold', type=float, default=.5)
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--seconds', type=float, default=0)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error('--threshold must be between zero and one')
    run(args)
