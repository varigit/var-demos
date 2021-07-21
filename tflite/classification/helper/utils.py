# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import collections
from contextlib import contextmanager
from datetime import timedelta
from time import monotonic

class Timer:
    def __init__(self):
        self.time = 0

    @contextmanager
    def timeit(self):
        begin = monotonic()
        try:
            yield
        finally:
            end = monotonic()
            self.convert(end - begin)

    def convert(self, elapsed):
        self.time = str(timedelta(seconds=elapsed))

class Framerate:
    def __init__(self):
        self.fps = 0
        self.window = collections.deque(maxlen=30)

    @contextmanager
    def fpsit(self):
        begin = monotonic()
        try:
            yield
        finally:
            end = monotonic()
            self.window.append(end - begin)
            self.fps = len(self.window) / sum(self.window)

def load_labels(labels_file: str) -> list:
    with open(labels_file, 'r') as f:
        return [line.strip() for line in f.readlines()]


