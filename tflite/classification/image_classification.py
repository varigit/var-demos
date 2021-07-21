# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse

import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

from utils import load_labels
from utils import Timer

def image_classification(args):
    labels = load_labels(args['label'])

    interpreter = Interpreter(model_path=args['model'])
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    with Image.open(args['image']) as im:
        _, height, width, _ = input_details[0]['shape']
        image = im.resize((width, height))
        image = np.expand_dims(image, axis = 0)

    interpreter.set_tensor(input_details[0]['index'], image)

    timer = Timer()
    with timer.timeit():
        interpreter.invoke()
    warm_up_time = timer.time

    with timer.timeit():
        interpreter.invoke()

    output_details = interpreter.get_output_details()[0]
    output = np.squeeze(interpreter.get_tensor(output_details['index']))

    k = int(args['kresults'])
    results = output.argsort()[-k:][::-1]
    for i in results:
        score = float(output[i] / 255.0)
        print("[{:.2%}]: {}".format(score, labels[i]))

    print("WARM-UP TIME:   {} seconds".format(warm_up_time))
    print("INFERENCE TIME: {} seconds".format(timer.time))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='model/mobilenet_v1_1.0_224_quant.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='model/labels_mobilenet_quant_v1_224.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--image',
          default='media/image.jpg',
          help='image file to be classified')
    parser.add_argument(
          '--kresults',
          default='3',
          help='number of displayed results')
    args = vars(parser.parse_args())
    image_classification(args)
