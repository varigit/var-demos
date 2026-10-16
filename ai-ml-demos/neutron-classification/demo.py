#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
from pathlib import Path
import subprocess
import sys
from time import monotonic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from tflite_runtime.interpreter import Interpreter, load_delegate
from runtime import demo_session, managed_capture, ThermalPacer, record_inference
from telemetry import SoCTemperature


def configure_camera(device):
    """Configure the tested Sonata CSI0 OV5640 path, not arbitrary cameras."""
    if device != '/dev/video0':
        return
    topology = subprocess.check_output(
        ['media-ctl', '-d', '/dev/media0', '-p'], text=True)
    sensor = 'ov5640 2-003c'
    if sensor not in topology:
        raise RuntimeError('CSI0 OV5640 not found; use a configured camera')
    subprocess.run(['media-ctl', '-d', '/dev/media0', '-l',
        f'"{sensor}":0 -> "csidev-4ad30000.csi":0 [1]'], check=True)
    pads = [(sensor, 0), ('csidev-4ad30000.csi', 0),
            ('4ac10000.syscon:formatter@20', 0), ('crossbar', 2)]
    pads.extend((f'mxc_isi.{index}', 0) for index in range(8))
    pads.append(('mxc_isi.0', 1))
    for entity, pad in pads:
        subprocess.run(['media-ctl', '-d', '/dev/media0', '-V',
            f'"{entity}":{pad} [fmt:UYVY8_1X16/1280x720 field:none]'],
            check=True)


def load_model():
    print('Loading MobileNet and the Neutron delegate...', flush=True)
    interpreter = Interpreter(
        model_path='model/mobilenet_neutron.tflite', num_threads=1,
        experimental_delegates=[load_delegate('/usr/lib/libneutron_delegate.so')])
    interpreter.allocate_tensors()
    source = interpreter.get_input_details()[0]
    output = interpreter.get_output_details()[0]
    operations = interpreter._get_ops_details()
    if (source['dtype'] != np.uint8 or list(source['shape']) != [1, 224, 224, 3]
            or not any(op['op_name'] == 'NeutronGraph' for op in operations)
            or not any(op['op_name'] == 'DELEGATE'
                       and source['index'] in op['inputs'] for op in operations)):
        raise RuntimeError('Expected a compiled and delegated Neutron graph')
    labels = Path('model/labels.txt').read_text().splitlines()
    if len(labels) != int(output['shape'][-1]):
        raise RuntimeError('Labels do not match model output')
    return interpreter, source, output, labels


@demo_session()
def run(args):
    compatible = Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
    if b'fsl,imx95' not in compatible:
        raise RuntimeError('This demo requires i.MX 95')
    configure_camera(args.camera)
    model = None if args.preview else load_model()
    print('Opening camera; waiting for the first frame...', flush=True)
    pipeline = (f'v4l2src device={args.camera} ! '
                'video/x-raw,format=YUY2,width=1280,height=720 ! '
                'queue leaky=downstream max-size-buffers=1 ! videoconvert ! '
                'video/x-raw,format=BGR ! appsink max-buffers=1 drop=true')
    cap = managed_capture(pipeline)
    pacer = ThermalPacer()
    analog = SoCTemperature(sensor_name='ana-thermal')
    started = monotonic()
    frames = 0
    title = 'Variscite - Neutron classification' if model else 'Variscite - Camera'
    while cap.isOpened():
        if args.seconds and monotonic() - started >= args.seconds:
            break
        if not pacer.wait():
            break
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError('Camera stopped delivering frames')
        lines = []
        if model:
            interpreter, source, output, labels = model
            rgb = cv2.cvtColor(cv2.resize(frame, (224, 224)), cv2.COLOR_BGR2RGB)
            interpreter.set_tensor(source['index'], rgb[None])
            before = monotonic()
            interpreter.invoke()
            elapsed = monotonic() - before
            record_inference(elapsed)
            scores = interpreter.get_tensor(output['index'])[0]
            lines = [f'{labels[index]}  {scores[index]:.0%}'
                     for index in np.argsort(scores)[-3:][::-1]]
            lines.insert(0, f'MobileNet V1 | Neutron | {elapsed * 1000:.1f} ms')
        frames += 1
        if frames == 1:
            print('Camera frames and inference ready.' if model
                  else 'Camera frames ready.', flush=True)
        if args.headless:
            continue
        if frames == 1:
            cv2.namedWindow(title, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(title, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN)
        fps = frames / max(monotonic() - started, 0.001)
        value = analog.read()
        lines.append(f'{fps:.1f} FPS' + (
            f' | Analog sensor {value:.1f} C' if value is not None else ''))
        for index, text in enumerate(lines):
            y = 32 + index * 32
            cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (15, 20, 24), 4, cv2.LINE_AA)
            cv2.putText(frame, text, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (240, 245, 250), 1, cv2.LINE_AA)
        cv2.imshow(title, frame)
        if cv2.waitKey(1) == 27:
            break
    if not frames:
        raise RuntimeError('No camera frames captured')
    print(f'Captured {frames} frames in {monotonic() - started:.1f} s', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera', default='/dev/video0')
    parser.add_argument('--preview', action='store_true')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--seconds', type=float, default=0)
    args = parser.parse_args()
    if args.camera != '/dev/video0':
        parser.error('Only the tested CSI0 camera /dev/video0 is supported')
    run(args)
