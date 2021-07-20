# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import collections
import colorsys
from contextlib import contextmanager
import random
import re
from datetime import timedelta
from time import monotonic

import cv2
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

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}

def generate_colors(labels):
    hsv_tuples = [(x / len(labels), 1., 1.) for x in range(len(labels))]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255),
                                 int(x[2] * 255)), colors))
    random.seed(10101)
    random.shuffle(colors)
    random.seed(None)
    return colors

def get_tensor(index, interpreter, output_details, squeeze=False):
    if squeeze:
        return np.squeeze(interpreter.get_tensor(output_details[index]['index']))
