# Copyright 2023 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import ethosu.interpreter as ethosu
from PIL import Image
import numpy as np
import sys
import time

MODEL_PATH = "model/mobilenet_v1_1.0_224_quant_vela.tflite"
LABEL_PATH = "model/labels_mobilenet_quant_v1_224.txt"
IMAGE_PATH = "media/car.jpg"

def load_labels(filename):
        with open(filename, 'r') as f:
                return [line.strip() for line in f.readlines()]

interpreter = ethosu.Interpreter(MODEL_PATH)

inputs_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

w, h = inputs_details[0]['shape'][1], inputs_details[0]['shape'][2]
img = Image.open(IMAGE_PATH).resize((w, h))

data = np.expand_dims(img, axis=0)
interpreter.set_input(0, data)

startTime = time.time()
interpreter.invoke()
delta = time.time() - startTime

print("Inference time:", '%.1f' % (delta * 1000), "ms\n")

output_data = interpreter.get_output(output_details[0]['index'])

results = np.squeeze(output_data)
top_k = results.argsort()[-5:][::-1]

labels = load_labels(LABEL_PATH)
for i in top_k:
        print('{:08.6f}: {}'.format(float(results[i] / 255.0), labels[i]))
