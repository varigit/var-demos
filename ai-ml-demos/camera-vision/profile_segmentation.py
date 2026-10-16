#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Diagnostic frame-stage timings; forward demo arguments unchanged."""

import collections
import json
from pathlib import Path
import runpy
import sys
from time import perf_counter


def main():
    target = Path(__file__).with_name('demo.py').resolve()
    sys.path.insert(0, str(target.parent))
    sys.path.insert(0, str(target.parent.parent))
    import cv2
    import runtime
    import segmentation
    import people_segmentation
    import capture
    from tflite_runtime.interpreter import Interpreter
    measurements = collections.defaultdict(list)
    originals = []

    def instrument(owner, name, label):
        original = getattr(owner, name)
        originals.append((owner, name, original))
        def timed(*args, **kwargs):
            started = perf_counter()
            result = original(*args, **kwargs)
            measurements[label].append((perf_counter() - started) * 1000)
            return result
        setattr(owner, name, timed)

    for owner, name, label in (
        (capture.VideoCapture, 'read', 'capture_read'),
        (runtime, 'display_view', 'display_resize'),
        (runtime.ThermalPacer, 'wait', 'thermal_wait'),
        (segmentation, 'prepare_segmentation_input', 'normalize'),
        (segmentation, 'read_segmentation', 'mask_decode'),
        (people_segmentation, 'prepare_people_input', 'normalize'),
        (people_segmentation, 'read_people', 'mask_decode'),
        (segmentation, 'paint_segmentation', 'paint'),
        (Interpreter, 'set_tensor', 'input_copy'),
        (Interpreter, 'invoke', 'invoke'),
        (cv2, 'resize', 'resize_all'),
        (cv2, 'cvtColor', 'color_conversion'),
        (cv2, 'imshow', 'imshow'),
        (cv2, 'waitKey', 'waitKey')):
        instrument(owner, name, label)
    previous_argv = sys.argv
    try:
        sys.argv = [str(target)] + previous_argv[1:]
        runpy.run_path(str(target), run_name='__main__')
    finally:
        sys.argv = previous_argv
        for owner, name, original in originals:
            setattr(owner, name, original)
    report = {}
    for label, times in measurements.items():
        samples = times[1:] if len(times) > 1 else times
        report[label] = dict(calls=len(times), mean_ms=sum(samples) / len(samples),
                             max_ms=max(samples))
    print('FRAME_PROFILE ' + json.dumps(report))


if __name__ == '__main__':
    main()
