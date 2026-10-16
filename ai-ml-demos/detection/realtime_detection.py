# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse
import sys
from contextlib import contextmanager
from datetime import timedelta
from time import monotonic

import cv2
import numpy as np
from PIL import Image

try:
    from tflite_runtime.interpreter import Interpreter
    from tflite_runtime.interpreter import load_delegate
except ImportError:
    sys.exit("No TensorFlow Lite Runtime module found!")

from helper.config import TITLE
from helper.opencv import (
    create_window, fit_to_display, put_info_on_frame, put_fps_on_frame
)
from helper.utils import get_tensor, load_labels, Timer, Framerate

from runtime import demo_session, managed_capture, ThermalPacer, register_cleanup, warm_up_model, startup_step
from runtime import check_camera

# Constants
import vision_window

EXT_DELEGATE_PATH = "/usr/lib/libvx_delegate.so"

def open_video_capture(width=720, height=480, framerate="30/1"):
    pipeline = "v4l2src device={} ! video/x-raw,width={},height={}," \
               "framerate={} ! queue leaky=downstream " \
               "max-size-buffers=1 ! videoconvert ! video/x-raw,format=BGR ! " \
               "appsink name=opencvsink max-buffers=1 drop=true".format(
                   args['camera'], width, height, framerate
               )
    return managed_capture(pipeline)

@demo_session()
def image_detection(args):
    check_camera('imx8mplus', args['camera'])
    labels = load_labels(args['label'])

    ext_delegate_options = {}
    ext_delegate = [load_delegate(EXT_DELEGATE_PATH, ext_delegate_options)]

    interpreter = Interpreter(model_path=args['model'], experimental_delegates=ext_delegate, num_threads=1)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    warm_up_model(interpreter)

    model_height, model_width = input_details[0]['shape'][1:3]

    camera_width, camera_height = map(int, args['resolution'].split('x'))
    video_capture = open_video_capture(camera_width, camera_height)
    window_created = False
    ready = False
    framerate = Framerate()
    pacer = ThermalPacer()
    while video_capture.isOpened():
        with framerate.fpsit():
            if not pacer.wait(lambda: vision_window.waitKey(1) == 27):
                break
            check, frame = video_capture.read()
            if check is not True:
                raise RuntimeError('Camera stopped delivering frames')
            frame = fit_to_display(frame, args['windowed'])

            resized_frame = cv2.resize(frame, (model_width, model_height))
            resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            resized_frame = np.expand_dims(resized_frame, axis = 0)

            interpreter.set_tensor(input_details[0]['index'], resized_frame)
            timer = Timer()
            with timer.timeit():
                interpreter.invoke()

            positions = get_tensor(0, interpreter, output_details, squeeze=True)
            classes = get_tensor(1, interpreter,  output_details, squeeze=True)
            scores = get_tensor(2, interpreter, output_details, squeeze=True)

            result = []
            for idx, score in enumerate(scores):
                if score > 0.5:
                    result.append({
                        'pos': positions[idx],
                        '_id': classes[idx],
                        'score': float(score),
                    })

            frame = put_info_on_frame(frame, result, timer.time, labels,
                                      args['model'], args['camera'],
                                      camera_size=(camera_width, camera_height))
            frame = put_fps_on_frame(frame, framerate.fps)
            if not window_created:
                create_window(TITLE, args['windowed'])
                window_created = True
            vision_window.imshow(TITLE, frame)
            if not ready:
                vision_window.waitKey(1)
                startup_step('Frames and NPU inference ready', ready=True)
                ready = True
            if vision_window.waitKey(1) == 27:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--resolution', default='720x480',
                        choices=['640x480', '720x480', '1280x720', '1920x1080'])
    parser.add_argument(
          '--model',
          default='model/ssd_mobilenet_v1_1_default_1.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='model/labels_ssd_mobilenet_v1.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--camera',
          default='/dev/video1',
          help='device path to camera, e.g.: /dev/video<x>')
    parser.add_argument(
          '--windowed',
          action='store_true',
          help='open the camera feed in a window instead of fullscreen')
    args = vars(parser.parse_args())
    image_detection(args)
