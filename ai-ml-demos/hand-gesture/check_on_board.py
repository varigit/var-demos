# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Hardware regression: CPU/NPU parity, input changes and empty frames."""
from pathlib import Path
from time import monotonic

import cv2
import numpy as np

from gestures import classify
from hand_tracker import HandTracker

ROOT = Path(__file__).resolve().parent


def main():
    image = cv2.imread(str(ROOT / 'media/hand.bmp'))
    if image is None:
        raise RuntimeError('Install the verified hand assets first')
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    inputs = (image, cv2.flip(image, 1), np.zeros_like(image), image)
    reference = []
    for delegate in ('', '/usr/lib/libvx_delegate.so'):
        tracker = HandTracker(
            str(ROOT / 'model/palm.tflite'),
            str(ROOT / 'model/landmark.tflite'),
            str(ROOT / 'model/anchors.csv'), delegate, box_enlarge=1.3)
        for index, frame in enumerate(inputs):
            started = monotonic()
            points, _ = tracker(frame)
            print(delegate or 'CPU', index, classify(points),
                  f'{1000 * (monotonic() - started):.1f} ms', flush=True)
            if index == 2:
                assert points is None, 'Hand detected in empty image'
            else:
                assert points is not None and np.isfinite(points).all()
                assert classify(points) == 'Open hand'
            if not delegate:
                reference.append(points)
            elif points is not None:
                delta = points - reference[index]
                print(f'CPU/NPU max error {abs(delta).max():.2f} px; '
                      f'RMS {np.sqrt(np.mean(delta ** 2)):.2f} px', flush=True)
                # Agreement for the known sample, not an accuracy benchmark.
                assert classify(points) == classify(reference[index])
    print('Hand model hardware regression passed', flush=True)


if __name__ == '__main__':
    main()
