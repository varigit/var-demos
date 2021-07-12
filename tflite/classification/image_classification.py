# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

from time import time

import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

with open("labels_mobilenet_quant_v1_224.txt") as f:
    labels = f.read().splitlines()

interpreter = Interpreter(model_path="mobilenet_v1_1.0_224_quant.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

with Image.open("image.jpg") as im:
    _, height, width, _ = input_details[0]['shape']
    image = im.resize((width, height))
    image = np.expand_dims(image, axis=0)

interpreter.set_tensor(input_details[0]['index'], image)
interpreter.invoke()
start = time()
interpreter.invoke()
final = time()

output_details = interpreter.get_output_details()[0]
output = np.squeeze(interpreter.get_tensor(output_details['index']))
results = output.argsort()[-3:][::-1]
for i in results:
    score = float(output[i] / 255.0)
    print("[{:.2%}]: {}".format(score, labels[i]))

print("INFERENCE TIME: {:.6f} seconds".format(final-start))
