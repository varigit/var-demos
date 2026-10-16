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
from runtime import display_view, display_box
import vision_window
import vision_overlay as ui


PALETTE = (
    (167, 211, 34),
    (248, 189, 56),
    (36, 191, 251),
    (250, 139, 167),
    (133, 113, 251),
    (53, 230, 163),
)
PANEL_COLOR = (24, 28, 32)
TEXT_COLOR = (242, 244, 246)


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
    try:
        hours, minutes, seconds = str(value).split(':')
        total = float(hours) * 3600 + float(minutes) * 60 + float(seconds)
        return total * 1000
    except (TypeError, ValueError):
        return float(value)


def _model_title(model_name):
    name = os.path.basename(str(model_name)).lower()
    if 'ssd_mobilenet_v1' in name:
        return 'SSD MobileNet V1 | NPU'
    return f"{os.path.splitext(name)[0].replace('_', ' ')} | NPU"








def put_info_on_frame(frame, result, time, labels, model_name, _source_file,
                      video_size=None, camera_size=None):
    frame, box_area = display_view(frame)
    for obj in result:
        class_id = int(obj['_id'])
        left, top, right, bottom = display_box(obj['pos'], box_area)
        if right <= left or bottom <= top:
            continue

        name = labels.get(class_id, f'class {class_id}')
        score = obj.get('score')
        ui.box(frame, (left, top, right, bottom), name, score)

    ui.statistics(frame, _inference_ms(time))
    if video_size is not None:
        ui.video_resolution(frame, video_size)
    elif camera_size is not None:
        ui.camera_resolution(frame, camera_size)
    ui.model(frame, _model_title(model_name).replace(' | NPU', ' | VIP8000'))
    draw_soc_temperature(frame, PANEL_COLOR, TEXT_COLOR)
    return frame


def put_fps_on_frame(frame, fps):
    ui.fps(frame, fps)
    return frame
