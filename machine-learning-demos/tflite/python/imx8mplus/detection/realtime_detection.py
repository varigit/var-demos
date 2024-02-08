# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse
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
from helper.opencv import put_info_on_frame, put_fps_on_frame
from helper.utils import get_tensor, load_labels, Timer, Framerate

# Constants
EXT_DELEGATE_PATH = "/usr/lib/libvx_delegate.so"

def open_video_capture(width = 640, height = 480, framerate = "30/1"):
    pipeline = "v4l2src device={} ! video/x-raw,width={},height={}," \
               "framerate={} ! queue leaky=downstream " \
               "max-size-buffers=1 ! videoconvert ! " \
               "appsink".format(args['camera'], width, height, framerate)
    return cv2.VideoCapture(pipeline)

def image_detection(args):
    labels = load_labels(args['label'])

    ext_delegate_options = {}
    ext_delegate = [load_delegate(EXT_DELEGATE_PATH, ext_delegate_options)]

    interpreter = Interpreter(model_path=args['model'], experimental_delegates=ext_delegate, num_threads=1)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    model_height, model_width = input_details[0]['shape'][1:3]

    video_capture = open_video_capture()
    framerate = Framerate()
    while video_capture.isOpened():
        with framerate.fpsit():
            check, frame = video_capture.read()
            if check is not True:
                break

            resized_frame = cv2.resize(frame, (model_width, model_height))
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
                    result.append({'pos': positions[idx], '_id': classes[idx]})

            frame = put_info_on_frame(frame, result, timer.time, labels,
                                      args['model'], args['camera'])
            frame = put_fps_on_frame(frame, framerate.fps)
            cv2.imshow(TITLE, frame)
            cv2.waitKey(1)

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
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
    args = vars(parser.parse_args())
    image_detection(args)
