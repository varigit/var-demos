# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse
from contextlib import contextmanager
from datetime import timedelta
from time import monotonic

import cv2
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

from config import FONT, TITLE
from utils import generate_colors, get_tensor, load_labels
from utils import Timer

def image_detection(args):
    labels = load_labels(args['label'])
    colors = generate_colors(labels)

    interpreter = Interpreter(model_path=args['model'])
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
    with timer.timeit():
        interpreter.invoke()
    warm_up_time = timer.time

    with timer.timeit():
        interpreter.invoke()

    positions = get_tensor(0, interpreter, output_details, squeeze=True)
    classes = get_tensor(1, interpreter,  output_details, squeeze=True)
    scores = get_tensor(2, interpreter, output_details, squeeze=True)

    result = []
    for idx, score in enumerate(scores):
        if score > 0.5:
            result.append({'pos': positions[idx], '_id': classes[idx]})

    height, width, _ = image.shape
    for obj in result:
        pos = obj['pos']
        _id = obj['_id']

        x1 = int(pos[1] * width)
        x2 = int(pos[3] * width)
        y1 = int(pos[0] * height)
        y2 = int(pos[2] * height)

        top = max(0, np.floor(y1 + 0.5).astype('int32'))
        left = max(0, np.floor(x1 + 0.5).astype('int32'))
        bottom = min(height, np.floor(y2 + 0.5).astype('int32'))
        right = min(width, np.floor(x2 + 0.5).astype('int32'))

        label_size = cv2.getTextSize(labels[_id], FONT['hershey'],
                                     FONT['size'], FONT['thickness'])[0]
        label_rect_left = int(left - 3)
        label_rect_top = int(top - 3)
        label_rect_right = int(left + 3 + label_size[0])
        label_rect_bottom = int(top - 5 - label_size[1])
        cv2.rectangle(image, (left, top), (right, bottom),
                      colors[int(_id) % len(colors)], 6)
        cv2.rectangle(image, (label_rect_left, label_rect_top),
                             (label_rect_right, label_rect_bottom),
                              colors[int(_id) % len(colors)], -1)
        cv2.putText(image, labels[_id], (left, int(top - 4)),
                    FONT['hershey'], FONT['size'],
                    FONT['color']['black'], FONT['thickness'])
    cv2.imshow(TITLE, image)
    cv2.waitKey()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='ssd_mobilenet_v1_1_default_1.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='labels_ssd_mobilenet_v1.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--image',
          default='media/image.png',
          help='image file to be classified')
    parser.add_argument(
          '--kresults',
          default='3',
          help='number of displayed results')
    args = vars(parser.parse_args())
    image_detection(args)
