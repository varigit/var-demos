# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from helper.config import FONT

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from telemetry import draw_soc_temperature
from runtime import display_view
import vision_window
import vision_overlay as ui


PANEL_COLOR = (24, 28, 32)
TEXT_COLOR = (242, 244, 246)
MUTED_COLOR = (184, 190, 196)
ACCENT_COLOR = (167, 211, 34)


def create_window(title, windowed=False):
    vision_window.namedWindow(title, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    if not windowed:
        vision_window.setWindowProperty(
            title, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        )


@lru_cache(maxsize=1)
def _display_size():
    size = os.environ.get('VAR_AI_DISPLAY_SIZE')
    if not size:
        try:
            with open(
                '/sys/class/graphics/fb0/virtual_size',
                encoding='utf-8'
            ) as size_file:
                size = size_file.read().strip()
        except OSError:
            return None
    try:
        return tuple(
            int(value) for value in size.replace('x', ',').split(',')
        )
    except ValueError:
        return None


def fit_to_display(frame, windowed=False):
    if windowed:
        return frame

    display_size = _display_size()
    if display_size is None:
        return frame
    target_width, target_height = display_size

    frame_height, frame_width = frame.shape[:2]
    target_ratio = target_width / target_height
    frame_ratio = frame_width / frame_height
    if frame_ratio > target_ratio:
        crop_width = round(frame_height * target_ratio)
        left = (frame_width - crop_width) // 2
        frame = frame[:, left:left + crop_width]
    elif frame_ratio < target_ratio:
        crop_height = round(frame_width / target_ratio)
        top = (frame_height - crop_height) // 2
        frame = frame[top:top + crop_height, :]

    return cv2.resize(frame, (target_width, target_height))




def _inference_ms(value):
    hours, minutes, seconds = str(value).split(':')
    total = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return total * 1000


def _model_title(model_name):
    name = os.path.basename(str(model_name)).lower()
    if 'mobilenet_v1' in name:
        return 'MobileNet V1 | NPU'
    return f"{os.path.splitext(name)[0].replace('_', ' ')} | NPU"








def put_info_on_frame(frame, top_result, labels,
                      inference_time, model_name, _source_file, camera_size=None,
                      video_size=None):
    frame, _ = display_view(frame)
    ui.results(frame, [(labels[index], score) for index, score in top_result])
    ui.statistics(frame, _inference_ms(inference_time))
    if camera_size is not None:
        ui.camera_resolution(frame, camera_size)
    elif video_size is not None:
        ui.video_resolution(frame, video_size)
    ui.model(frame, _model_title(model_name).replace(' | NPU', ' | VIP8000'))
    draw_soc_temperature(frame, PANEL_COLOR, TEXT_COLOR)
    return frame


def put_fps_on_frame(frame, fps):
    ui.fps(frame, fps)
    return frame
