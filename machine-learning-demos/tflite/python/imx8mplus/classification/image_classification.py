# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse

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
from helper.utils import load_labels, Timer

# Constants
EXT_DELEGATE_PATH = "/usr/lib/libvx_delegate.so"

def image_classification(args):
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

    output_details = interpreter.get_output_details()[0]
    output = np.squeeze(interpreter.get_tensor(output_details['index']))

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
