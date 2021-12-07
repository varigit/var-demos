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
        """
        The time is storage in the **time** attribute.
        """
        begin = monotonic()
        try:
            yield
        finally:
            end = monotonic()
            self.convert(end - begin)

    def convert(self, elapsed):
        """
        Convert time from monotonic to seconds.
        """
        self.time = str(timedelta(seconds=elapsed))
