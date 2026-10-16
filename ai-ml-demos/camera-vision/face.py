# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import numpy as np


def prepare_face_input(rgb, source):
    """UltraFace expects normalized RGB, then its declared quantization."""
    if source['dtype'] != np.uint8:
        raise ValueError('Expected UINT8 UltraFace input')
    scale, zero = source['quantization']
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('UltraFace input needs valid quantization parameters')
    normalized = (rgb.astype(np.float32) - 127.0) / 128.0
    return np.clip(np.rint(normalized / scale + zero), 0, 255).astype(np.uint8)[None]


def decode_faces(value, threshold=.5):
    """Rows are [background score, face score, x0, y0, x1, y1].

    NMS is already in this model graph. Our overlay uses y/x box order.
    """
    value = np.asarray(value)
    if value.ndim != 2 or value.shape[1] != 6:
        raise ValueError('Expected UltraFace output with shape [N,6]')
    if not np.isfinite(value).all():
        raise ValueError('Non-finite face detector output')
    if not 0 <= threshold <= 1:
        raise ValueError('Confidence threshold must be between zero and one')
    result = []
    for row in value:
        score = float(row[1])
        if score < threshold:
            continue
        box = np.clip(row[[3, 2, 5, 4]], 0, 1)
        if box[2] > box[0] and box[3] > box[1]:
            result.append((box, 0, score))
    return result


def load_face_model(root, platform):
    from tflite_runtime.interpreter import Interpreter, load_delegate
    from runtime import startup_step

    names = {'imx8mplus': ('ultraface.tflite', 'vx'),
             'imx93': ('ultraface_vela.tflite', 'ethosu'),
             'imx95': ('ultraface_neutron.tflite', 'neutron')}
    filename, delegate = names[platform]
    startup_step(f'Loading UltraFace and {delegate} delegate')
    interpreter = Interpreter(model_path=str(root / 'model' / filename),
        num_threads=1, experimental_delegates=[load_delegate(
            f'/usr/lib/lib{delegate}_delegate.so')])
    interpreter.allocate_tensors()
    source = interpreter.get_input_details()[0]
    outputs = interpreter.get_output_details()
    operations = interpreter._get_ops_details()
    if (tuple(source['shape']) != (1, 240, 320, 3)
            or source['dtype'] != np.uint8 or len(outputs) != 1
            or outputs[0]['dtype'] != np.float32
            or not any(op['op_name'] == 'DELEGATE'
                       and source['index'] in op['inputs'] for op in operations)):
        raise RuntimeError('Expected UltraFace UINT8 input delegated to its NPU')
    custom = {'imx93': 'ethos-u', 'imx95': 'NeutronGraph'}.get(platform)
    if custom and not any(op['op_name'] == custom for op in operations):
        raise RuntimeError('UltraFace was not compiled for the selected NPU')
    startup_step('Warming up the NPU with a model-sized frame')
    interpreter.set_tensor(source['index'], prepare_face_input(
        np.full((240, 320, 3), 127, np.uint8), source))
    interpreter.invoke()
    decode_faces(interpreter.get_tensor(outputs[0]['index']))
    return interpreter, source, outputs, {0: 'face'}, None
