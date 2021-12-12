# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import glob
import os

import numpy as np
import PIL
from PIL import Image
from tflite_runtime.interpreter import Interpreter

def convert_to_8b_grayscale(image_path, maxsize):
	image = Image.open(image_path).convert('L')
	image_width, image_height = image.size
	if image_width != image_height:
		m_min_d = min(image_width, image_height)
		image = image.crop((0, 0, m_min_d, m_min_d))
	image.thumbnail(maxsize, PIL.Image.ANTIALIAS)
	return np.asarray(image)

def read_labels(labels_file_path):
    with open(labels_file_path, 'r', encoding='utf-8') as f:
        labels_list = [line.strip() for line in f.readlines()]
    return labels_list

if __name__ == "__main__":
    DATA_DIR = os.path.join(os.getcwd(), "data")
    TFLITE_MODEL_DIR = os.path.join(os.getcwd(), "model")

    class_names = read_labels(labels_file_path=f"{TFLITE_MODEL_DIR}/tflite.txt")
    maxsize = 50, 50
    maxsize_w, maxsize_h = maxsize
    reshape_size = (maxsize_w, maxsize_h, 1)

    images = [f for f in glob.glob(f"{DATA_DIR}/*.jpg")]

    for image in images:
        input_image = convert_to_8b_grayscale(image, maxsize)
        input_image = input_image.reshape(reshape_size)

        interpreter = Interpreter(model_path=f"{TFLITE_MODEL_DIR}/tflite_model_32bit.tflite")
        interpreter.allocate_tensors()

        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        input_image = np.array(input_image, dtype=np.float32) / 255.0
        input_image = np.expand_dims(input_image, axis=0)
        print(input_image.shape)

        print(input_details[0]['shape'])
        print(input_details[0]['dtype'])
        print(output_details[0]['dtype'])

        interpreter.set_tensor(input_details[0]["index"], input_image)

        interpreter.invoke()
        result = interpreter.tensor(output_details[0]["index"])()[0]

        prediction = np.argmax(result)
        print("===============================================================")
        print(f"Image: {image}\n")
        print(prediction)
        print(f"Prediction: {class_names[prediction]}\n")
        print(f"Confidence: {result[prediction]}\n\n")
