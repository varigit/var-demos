# Copyright 2025 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import collections
import os
import re
import sys
from pathlib import Path
from contextlib import contextmanager
from datetime import timedelta
from time import monotonic

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from telemetry import draw_soc_temperature
from runtime import record_inference, display_view, display_box
import vision_overlay as ui


FONT = {
    'hershey': cv2.FONT_HERSHEY_SIMPLEX,
    'size': 0.8,
    'color': {
        'black': (0, 0, 0),
        'blue': (255, 0, 0),
        'green': (0, 255, 0),
        'orange': (0, 127, 255),
        'red': (0, 0, 255),
        'white': (255, 255, 255)
    },
    'thickness': 2
}

PALETTE = (
    (34, 211, 167),
    (56, 189, 248),
    (251, 191, 36),
    (167, 139, 250),
    (251, 113, 133),
    (163, 230, 53),
)
PANEL_COLOR = (24, 28, 32)
TEXT_COLOR = (242, 244, 246)

COMBINATIONS = [
    ("assets/videos/video_1280x720.mp4", (1280, 720), "lvds_small", (800, 480), "windowed"),
    ("assets/videos/video_1280x720.mp4", (1280, 720), "lvds_small", (800, 480), "fullscreen"),
    ("assets/videos/video_1280x720.mp4", (1280, 720), "lvds_large", (1280, 800), "windowed"),
    ("assets/videos/video_1280x720.mp4", (1280, 720), "lvds_large", (1280, 800), "fullscreen"),
    ("assets/videos/video_1280x720.mp4", (1280, 720), "monitor_4k", (3840, 2160), "windowed"),
    ("assets/videos/video_1280x720.mp4", (1280, 720), "monitor_4k", (3840, 2160), "fullscreen"),

    ("assets/videos/video_1280x800.mp4", (1280, 800), "lvds_small", (800, 480), "windowed"),
    ("assets/videos/video_1280x800.mp4", (1280, 800), "lvds_small", (800, 480), "fullscreen"),
    ("assets/videos/video_1280x800.mp4", (1280, 800), "lvds_large", (1280, 800), "windowed"),
    ("assets/videos/video_1280x800.mp4", (1280, 800), "lvds_large", (1280, 800), "fullscreen"),
    ("assets/videos/video_1280x800.mp4", (1280, 800), "monitor_4k", (3840, 2160), "windowed"),
    ("assets/videos/video_1280x800.mp4", (1280, 800), "monitor_4k", (3840, 2160), "fullscreen"),

    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "lvds_small", (800, 480), "windowed"),
    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "lvds_small", (800, 480), "fullscreen"),
    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "lvds_large", (1280, 800), "windowed"),
    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "lvds_large", (1280, 800), "fullscreen"),
    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "monitor_4k", (3840, 2160), "windowed"),
    ("assets/videos/video_1920x1080.mp4", (1920, 1080), "monitor_4k", (3840, 2160), "fullscreen"),
]

PROFILE_ENABLED = False

def profile(func):
    def wrapper(*args, **kwargs):
        if not PROFILE_ENABLED:
            return func(*args, **kwargs)
        start = monotonic()
        result = func(*args, **kwargs)
        duration = (monotonic() - start) * 1000
        print(f"[PROFILE] {func.__name__}: {duration:.2f} ms")
        return result
    return wrapper

class Timer:
    def __init__(self):
        self.time = 0

    @contextmanager
    def timeit(self):
        begin = monotonic()
        try:
            yield
        except BaseException:
            raise
        else:
            record_inference(monotonic() - begin)
        finally:
            end = monotonic()
            self.convert(end - begin)

    def convert(self, elapsed):
        self.time = str(timedelta(seconds=elapsed))


class Framerate:
    def __init__(self):
        self.fps = 0.0
        self.last_update = monotonic()
        self.window = collections.deque(maxlen=30)

    def update(self):
        now = monotonic()
        self.window.append(now - self.last_update)
        self.last_update = now
        self.fps = len(self.window) / sum(self.window)
        return self.fps

@contextmanager
def debug_profile(name, enabled):
    start = monotonic()
    yield
    if enabled:
        print(f"[DEBUG] {name}: {(monotonic() - start) * 1000:.2f} ms")

def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}



def _inference_ms(value):
    hours, minutes, seconds = str(value).split(':')
    total = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return total * 1000




def _model_title(model_name):
    name = os.path.basename(str(model_name)).lower()
    if 'ssd_mobilenet_v1' in name:
        return 'SSD MobileNet V1 | NPU'
    return f"{os.path.splitext(name)[0].replace('_', ' ')} | NPU"






def put_info_on_frame(frame, results, inf_time, labels, model_name,
                      _source_file, fps=None, display_res=None, video_size=None):
    frame, box_area = display_view(frame, display_res)
    for obj in results:
        class_id = int(obj['class'])
        left, top, right, bottom = display_box(obj['box'], box_area)
        if right <= left or bottom <= top:
            continue
        name = labels.get(class_id, f'class {class_id}')
        ui.box(frame, (left, top, right, bottom), name, obj['score'], rgb=True)

    ui.statistics(frame, _inference_ms(inf_time), fps, rgb=True)
    if video_size is not None:
        ui.video_resolution(frame, video_size, rgb=True)
    ui.model(frame, _model_title(model_name).replace(' | NPU', ' | VIP8000'),
             rgb=True)
    draw_soc_temperature(frame, PANEL_COLOR, TEXT_COLOR, rgb=True)
    return frame


def resize_with_letterbox(frame, display_res):
    target_width, target_height = display_res
    frame_height, frame_width = frame.shape[:2]
    scale = min(target_width / frame_width, target_height / frame_height)
    resized_width = max(1, int(frame_width * scale))
    resized_height = max(1, int(frame_height * scale))
    resized = cv2.resize(frame, (resized_width, resized_height))

    output = np.zeros((target_height, target_width, 3), dtype=frame.dtype)
    x_offset = (target_width - resized_width) // 2
    y_offset = (target_height - resized_height) // 2
    output[
        y_offset:y_offset + resized_height,
        x_offset:x_offset + resized_width
    ] = resized
    return output

def show_available_combinations():
    print("Available combinations:\n")
    print(
        f"{'ID':<4} {'Video':<42} {'Video size':<12} "
        f"{'Display':<12} {'Display size':<14} {'Mode'}"
    )
    print("-" * 103)
    for index, combination in enumerate(COMBINATIONS, start=1):
        video, video_res, display, display_res, mode = combination
        video_size = f"{video_res[0]}x{video_res[1]}"
        display_size = f"{display_res[0]}x{display_res[1]}"
        print(
            f"{index:<4} {video:<42} {video_size:<12} "
            f"{display:<12} {display_size:<14} {mode}"
        )
    exit(0)
