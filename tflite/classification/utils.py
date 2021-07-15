# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

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
