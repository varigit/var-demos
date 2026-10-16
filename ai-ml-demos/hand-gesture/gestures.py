# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Conservative geometric gestures, not a learned gesture classifier."""
from time import monotonic

import numpy as np


def classify(points):
    if points is None:
        return 'No hand'
    points = np.asarray(points)
    if points.shape != (21, 2) or not np.isfinite(points).all():
        return 'Unknown'
    extended = []
    for base, middle, tip in ((5, 6, 8), (9, 10, 12),
                              (13, 14, 16), (17, 18, 20)):
        first = points[middle] - points[base]
        second = points[tip] - points[middle]
        lengths = np.linalg.norm(first) * np.linalg.norm(second)
        straight = lengths > 1e-6 and np.dot(first, second) / lengths > .5
        farther = (np.linalg.norm(points[tip] - points[0])
                   > 1.15 * np.linalg.norm(points[middle] - points[0]))
        extended.append(bool(straight and farther))
    if all(extended):
        return 'Open hand'
    if extended == [True, False, False, False]:
        return 'Pointing'
    if extended == [True, True, False, False]:
        return 'Victory'
    if not any(extended):
        # The thumb must also be near the palm to label a closed fist.
        palm = np.linalg.norm(points[9] - points[0])
        if palm > 1e-6 and np.linalg.norm(points[4] - points[9]) < palm:
            return 'Closed fist'
    return 'Unknown'


class SmoothLandmarks:
    """Light smoothing; clear lost hands and reset on large hand changes."""
    def __init__(self, alpha=.6):
        self.alpha = alpha
        self.previous = None

    def update(self, points):
        if points is None:
            self.previous = None
            return None
        points = np.asarray(points)
        if points.shape != (21, 2) or not np.isfinite(points).all():
            raise ValueError('Invalid hand landmarks')
        if self.previous is not None:
            palm = np.linalg.norm(points[9] - points[0])
            movement = np.linalg.norm(points[0] - self.previous[0])
            if palm > 1e-6 and movement < 1.5 * palm:
                points = (self.alpha * points
                          + (1 - self.alpha) * self.previous)
        self.previous = points.copy()
        return points


class StableGesture:
    def __init__(self, hold_seconds=.35, clock=monotonic):
        self.clock = clock
        self.hold = hold_seconds
        self.candidate = 'No hand'
        self.since = clock()
        self.label = 'No hand'

    def update(self, candidate):
        now = self.clock()
        if candidate == 'No hand':
            self.label = candidate
        if candidate != self.candidate:
            self.candidate = candidate
            self.since = now
        if now - self.since >= self.hold:
            self.label = candidate
        # Never retain a previous gesture while another one is settling.
        return self.label if self.label == candidate else 'Recognizing...'
