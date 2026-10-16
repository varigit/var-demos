# Copyright 2023 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse

import cv2
import ethosu.interpreter as ethosu
from PIL import Image
import numpy as np
import sys
import time

from helper.config import TITLE
from helper.opencv import put_info_on_frame
from helper.utils import load_labels, Timer

def image_classification(args):
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

    output = np.squeeze(interpreter.get_output(output_details[0]['index']))

    k = int(args['kresults'])
    top_k = output.argsort()[-k:][::-1]
    result = []
    for i in top_k:
        score = float(output[i] / 255.0)
        result.append((i, score))

    image = put_info_on_frame(image, result, labels,
                              timer.time, args['model'], args['image'])
    cv2.imshow(TITLE, image)
    cv2.waitKey()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='model/mobilenet_v1_1.0_224_quant_vela.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='model/labels_mobilenet_quant_v1_224.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--image',
          default='media/car.jpg',
          help='image file to be classified')
    parser.add_argument(
          '--kresults',
          default='3',
          help='number of displayed results')
    args = vars(parser.parse_args())
    image_classification(args)
