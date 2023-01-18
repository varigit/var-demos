# Copyright 2023 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse

import cv2
import numpy as np
from PIL import Image
import ethosu.interpreter as ethosu

from helper.config import TITLE
from helper.opencv import put_info_on_frame
from helper.utils import get_tensor, load_labels, Timer

def image_detection(args):
    labels = load_labels(args['label'])

    interpreter = ethosu.Interpreter(args['model'])

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    with Image.open(args['image']) as im:
        _, height, width, _ = input_details[0]['shape']
        image = np.array(im)
        image = image[:, :, ::-1].copy()
        image_resized = im.resize((width, height))
        image_resized = np.expand_dims(image_resized, axis = 0)

    interpreter.set_input(input_details[0]['index'], image_resized)

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

    image = put_info_on_frame(image, result, timer.time, labels,
                              args['model'], args['image'])
    cv2.imshow(TITLE, image)
    cv2.waitKey()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='model/ssd_mobilenet_v1_1_default_1_vela.tflite',
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
