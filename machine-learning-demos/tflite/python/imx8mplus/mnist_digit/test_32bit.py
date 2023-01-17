# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import os

import cv2
import numpy as np
from tflite_runtime.interpreter import Interpreter

from utils import Timer

DATA_DIR = os.path.join(os.getcwd(), "data")
TFLITE_MODEL_DIR = os.path.join(os.getcwd(), "model")

input_image = cv2.imread(f"{DATA_DIR}/zero.png")
input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
input_image = cv2.resize(input_image, (28, 28), interpolation = cv2.INTER_LINEAR)
input_image = np.expand_dims(np.array(input_image, dtype=np.float32) / 255.0, 0)

interpreter = Interpreter(model_path=f"{TFLITE_MODEL_DIR}/mnist_32bit.tflite")

input_type = interpreter.get_input_details()[0]['dtype']
print('input: ', input_type)
output_type = interpreter.get_output_details()[0]['dtype']
print('output: ', output_type)

interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

interpreter.set_tensor(input_details[0]["index"], input_image)

timer = Timer()

interpreter.invoke()
with timer.timeit():
    interpreter.invoke()
result = interpreter.tensor(output_details[0]["index"])()[0]

digit = np.argmax(result)
print(f"Predicted Digit: {digit}\nConfidence: {result[digit]}")
print(f"Inference Time: {timer.time}")
