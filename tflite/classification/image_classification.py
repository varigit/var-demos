# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

from utils import Timer, arguments

def image_classification(model_name, label_name, image_name, k = 3):

    with open(label_name) as f:
        labels = f.read().splitlines()

    interpreter = Interpreter(model_path=model_name)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    with Image.open(image_name) as im:
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
    results = output.argsort()[-3:][::-1]
    for i in results:
        score = float(output[i] / 255.0)
        print("[{:.2%}]: {}".format(score, labels[i]))

    print("WARM-UP TIME:   {} seconds".format(warm_up_time))
    print("INFERENCE TIME: {} seconds".format(timer.time))

if __name__ == "__main__":
    args = arguments()
    image_classification(args.model, args.label, args.image)
