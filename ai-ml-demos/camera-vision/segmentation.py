# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""DeepLabV3 semantic masks for people and vehicles, not instance tracking."""

import cv2
import numpy as np
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import os

PERSON = 15
VEHICLES = (2, 6, 7, 14, 19)  # bicycle, bus, car, motorbike, train (PASCAL VOC)


def prepare_segmentation_input(rgb, source):
    if source['dtype'] != np.float32:
        raise ValueError('This DeepLab artifact expects normalized FLOAT32 RGB')
    normalized = rgb.astype(np.float32)
    np.subtract(normalized, 127.5, out=normalized)
    np.divide(normalized, 127.5, out=normalized)
    return normalized[None]


def decode_segmentation(scores):
    scores = np.asarray(scores)
    if scores.ndim != 4 or scores.shape[0] != 1 or scores.shape[-1] != 21:
        raise ValueError('Expected DeepLab scores [1,height,width,21]')
    if not np.isfinite(scores).all():
        raise ValueError('Non-finite segmentation scores')
    return np.argmax(scores[0], axis=-1).astype(np.uint8)


def read_segmentation(interpreter, output):
    # The 513x513x21 FLOAT32 scores occupy about 21 MiB. Use a short-lived
    # view rather than copying them each frame. Only the independent class
    # mask leaves this function; no tensor view survives the next invoke.
    scores = interpreter.tensor(output['index'])()
    if scores.ndim == 4 and scores.shape[0] == 1 and scores.shape[1] >= 128:
        workers = min(4, os.cpu_count() or 1)
        if workers > 1:
            # Join workers before dropping the TFLite view: queued worker
            # arguments must not retain that view across the next invoke.
            with ThreadPoolExecutor(max_workers=workers) as pool:
                masks = list(pool.map(decode_segmentation,
                                      np.array_split(scores, workers, axis=1)))
            return np.concatenate(masks, axis=0)
    return decode_segmentation(scores)


@lru_cache(maxsize=1)
def paint_tables():
    import vision_overlay as ui
    colors = np.zeros((256, 1, 3), np.uint8)
    selected = np.zeros(256, np.uint8)
    colors[PERSON, 0] = ui.color_for('person')
    colors[list(VEHICLES), 0] = ui.color_for('car')
    selected[[PERSON, *VEHICLES]] = 255
    vehicles = np.zeros(256, np.uint8)
    vehicles[list(VEHICLES)] = 255
    return colors, selected, vehicles


def paint_segmentation(frame, classes, area, opacity=.45):
    """Paint only the viewport; panels and letterbox bars stay untouched."""
    if not 0 <= opacity <= 1:
        raise ValueError('Mask opacity must be between zero and one')
    x, y, width, height = area
    mask = cv2.resize(classes, (width, height), interpolation=cv2.INTER_NEAREST)
    region = frame[y:y + height, x:x + width]
    colors, selected, vehicles = paint_tables()
    # Keep blending in optimized OpenCV loops; boolean indexing previously
    # allocated and converted several arrays for each category on every frame.
    tint = cv2.applyColorMap(mask, colors)
    blended = cv2.addWeighted(region, 1 - opacity, tint, opacity, 0)
    cv2.copyTo(blended, cv2.LUT(mask, selected), region)
    pixels = mask.size
    return (cv2.countNonZero(cv2.inRange(mask, PERSON, PERSON)) / pixels,
            cv2.countNonZero(cv2.LUT(mask, vehicles)) / pixels)


def legend(frame):
    import vision_overlay as ui
    ui.legend(frame, [('People', 'person'), ('Vehicles', 'car')])


def load_segmentation_model(root, platform):
    from tflite_runtime.interpreter import Interpreter, load_delegate, OpResolverType
    from runtime import startup_step
    backends = {'imx8mplus': ('deeplabv3.tflite', 'vx'),
                'imx93': ('deeplabv3_vela.tflite', 'ethosu'),
                'imx95': ('deeplabv3_neutron.tflite', 'neutron')}
    if platform not in backends:
        raise RuntimeError('Unsupported DeepLab platform')
    filename, delegate = backends[platform]
    startup_step(f'Loading DeepLabV3 and {delegate} delegate')
    options = dict(model_path=str(root / 'model' / filename),
                   num_threads=6 if platform == 'imx95' else 2,
                   experimental_delegates=[load_delegate(f'/usr/lib/lib{delegate}_delegate.so')])
    if platform != 'imx95':
        options['experimental_op_resolver_type'] = OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES
    # MX95's dilated/float tail benefits from XNNPACK on the CPU. A generic
    # DELEGATE alone is therefore insufficient proof of Neutron acceleration.
    interpreter = Interpreter(**options)
    interpreter.allocate_tensors()
    source = interpreter.get_input_details()[0]
    outputs = interpreter.get_output_details()
    ops = interpreter._get_ops_details()
    if (tuple(source['shape']) != (1, 513, 513, 3)
            or source['dtype'] != np.float32 or len(outputs) != 1
            or tuple(outputs[0]['shape']) != (1, 513, 513, 21)
            or outputs[0]['dtype'] != np.float32
            or not any(op['op_name'] == 'DELEGATE' for op in ops)):
        raise RuntimeError('Expected DeepLab with 513x513 RGB input and NPU delegation')
    if platform == 'imx93' and not any(op['op_name'] == 'ethos-u' for op in ops):
        raise RuntimeError('DeepLab was not compiled for Ethos-U65')
    if platform == 'imx95' and not any(op['op_name'] == 'NeutronGraph' for op in ops):
        raise RuntimeError('DeepLab was not compiled for Neutron; CPU-only models are rejected')
    startup_step('Warming up DeepLab; some operators also run on the CPU')
    interpreter.set_tensor(source['index'], np.zeros(source['shape'], np.float32))
    interpreter.invoke()
    decode_segmentation(interpreter.get_tensor(outputs[0]['index']))
    return interpreter, source, outputs, {}, None
