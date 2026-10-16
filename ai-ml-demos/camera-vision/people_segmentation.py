# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Lightweight Selfie Segmenter landscape: person versus background."""

import cv2
import numpy as np
from segmentation import PERSON


def prepare_people_input(rgb, source):
    if source['dtype'] != np.float32:
        raise ValueError('Selfie Segmenter expects FLOAT32 RGB in [0,1]')
    value = rgb.astype(np.float32)
    np.divide(value, 255, out=value)
    return value[None]


def decode_people(scores, threshold=.5):
    scores = np.asarray(scores)
    if not 0 <= threshold <= 1:
        raise ValueError('Person threshold must be between zero and one')
    if scores.shape != (1, 144, 256, 1):
        raise ValueError('Expected person probabilities [1,144,256,1]')
    if not np.isfinite(scores).all() or np.any(scores < 0) or np.any(scores > 1):
        raise ValueError('Invalid person probabilities')
    return np.where(scores[0, :, :, 0] > threshold, PERSON, 0).astype(np.uint8)


def read_people(interpreter, output, threshold=.5):
    return decode_people(interpreter.tensor(output['index'])(), threshold)


def legend(frame):
    import vision_overlay as ui
    ui.legend(frame, [('People', 'person')])


def load_people_model(root, platform):
    from tflite_runtime.interpreter import Interpreter, load_delegate, OpResolverType
    from runtime import startup_step
    backends = {'imx8mplus': ('people.tflite', 'vx'),
                'imx93': ('people_vela.tflite', 'ethosu'),
                'imx95': ('people_neutron.tflite', 'neutron')}
    filename, delegate = backends[platform]
    startup_step(f'Loading Selfie Segmenter and {delegate} delegate')
    engine = Interpreter(model_path=str(root / 'model' / filename), num_threads=2,
        experimental_op_resolver_type=OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES,
        experimental_delegates=[load_delegate(f'/usr/lib/lib{delegate}_delegate.so')])
    engine.allocate_tensors()
    source, = engine.get_input_details()
    output, = engine.get_output_details()
    names = {op['op_name'] for op in engine._get_ops_details()}
    if (tuple(source['shape']) != (1, 144, 256, 3) or source['dtype'] != np.float32
            or tuple(output['shape']) != (1, 144, 256, 1)
            or output['dtype'] != np.float32 or 'DELEGATE' not in names):
        raise RuntimeError('Expected landscape Selfie Segmenter with NPU delegation')
    if platform == 'imx93' and 'ethos-u' not in names:
        raise RuntimeError('People model was not compiled for Ethos-U65')
    if platform == 'imx95' and 'NeutronGraph' not in names:
        raise RuntimeError('People model was not compiled for Neutron')
    startup_step('Warming up person segmentation')
    engine.set_tensor(source['index'], np.zeros(source['shape'], np.float32))
    engine.invoke()
    read_people(engine, output)
    return engine, source, [output], {}, None
