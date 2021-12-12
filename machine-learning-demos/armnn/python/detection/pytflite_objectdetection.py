# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import cv2
import numpy as np

from tflite_runtime.interpreter import Interpreter

from utils import Timer

timer = Timer()

interpreter = Interpreter(model_path="model/ssd_mobilenet_v1_1_default_1.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
_,height,width,_ = input_details[0]['shape']

image = cv2.imread("data/car.jpg")
image = cv2.resize(image, (300, 300))
image = np.array(image, dtype=np.uint8)
image = np.expand_dims(image, axis=0)

print(f"Input shape: {image.shape}")
print(f"Input Details: {input_details[0]['dtype']}")
print(f"Output Details: {output_details[0]['dtype']}")

interpreter.set_tensor(input_details[0]['index'], image)
interpreter.invoke()
with timer.timeit():
    interpreter.invoke()
print(f"Inference time: {timer.time}")

output_data = interpreter.get_tensor(output_details[0]['index'])
print(output_data)
