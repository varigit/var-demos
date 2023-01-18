# Copyright 2023 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import collections
from contextlib import contextmanager
from datetime import timedelta
import re
from time import monotonic

import numpy as np

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

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}

def get_tensor(index, interpreter, output_details, squeeze=False):
    if squeeze:
        return np.squeeze(interpreter.get_input(output_details[index]['index']))
