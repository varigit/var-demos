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
from helper.opencv import put_info_on_frame
from helper.utils import get_tensor, load_labels, Timer

# Constants
EXT_DELEGATE_PATH = "/usr/lib/libvx_delegate.so"

def image_detection(args):
    labels = load_labels(args['label'])

    ext_delegate_options = {}
    ext_delegate = [load_delegate(EXT_DELEGATE_PATH, ext_delegate_options)]

    interpreter = Interpreter(model_path=args['model'], experimental_delegates=ext_delegate, num_threads=1)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    with Image.open(args['image']) as im:
        _, height, width, _ = input_details[0]['shape']
        image = np.array(im)
        image = image[:, :, ::-1].copy()
        image_resized = im.resize((width, height))
        image_resized = np.expand_dims(image_resized, axis = 0)

    interpreter.set_tensor(input_details[0]['index'], image_resized)

    timer = Timer()
    interpreter.invoke()
    with timer.timeit():
        interpreter.invoke()

    positions = get_tensor(0, interpreter, output_details, squeeze=True)
    classes = get_tensor(1, interpreter,  output_details, squeeze=True)
    scores = get_tensor(2, interpreter, output_details, squeeze=True)

    result = []
    for idx, score in enumerate(scores):
        if score > 0.5:
            result.append({'pos': positions[idx], '_id': classes[idx]})

    image = put_info_on_frame(image, result, timer.time, labels,
                              args['model'], args['image'])
    cv2.imshow(TITLE, image)
    cv2.waitKey()

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
          '--image',
          default='media/image.png',
          help='image file to be classified')
    args = vars(parser.parse_args())
    image_detection(args)
