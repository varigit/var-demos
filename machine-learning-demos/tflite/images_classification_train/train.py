# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import glob
import os
import re

import numpy as np
import PIL
from PIL import Image
import tensorflow as tf
from tensorflow import keras

def convert_to_8b_grayscale(image_path, maxsize):
	image = Image.open(image_path).convert('L')
	image_width, image_height = image.size
	if image_width != image_height:
		m_min_d = min(image_width, image_height)
		image = image.crop((0, 0, m_min_d, m_min_d))
	image.thumbnail(maxsize, PIL.Image.ANTIALIAS)
	return np.asarray(image)

def load_image_dataset(path_dir, maxsize, reshape_size):
	images = []
	labels = []
	os.chdir(path_dir)
	for file in glob.glob("*.jpg"):
		img = convert_to_8b_grayscale(file, maxsize)
		if re.match('orange.*', file):
			images.append(img.reshape(reshape_size))
			labels.append(0)
		elif re.match('banana.*', file):
			images.append(img.reshape(reshape_size))
			labels.append(1)
	return (np.asarray(images), np.asarray(labels))

if __name__ == "__main__":
    DATASET_DIR = os.path.join(os.getcwd(), "dataset")
    DATASET_TEST_DIR = os.path.join(os.getcwd(), "dataset", "test")
    TFLITE_MODEL_DIR = os.path.join(os.getcwd(), "model")

    maxsize = 50, 50
    maxsize_w, maxsize_h = maxsize

    (train_images, train_labels) = load_image_dataset(
                   path_dir = DATASET_DIR,
                   maxsize = maxsize,
                   reshape_size = (maxsize_w, maxsize_h, 1))

    (test_images, test_labels) = load_image_dataset(
                   path_dir = DATASET_TEST_DIR,
                   maxsize = maxsize,
                   reshape_size = (maxsize_w, maxsize_h, 1))

    train_images = train_images / 255.0
    test_images = test_images / 255.0

    model = keras.Sequential([
        keras.layers.Flatten(input_shape = (maxsize_w, maxsize_h , 1)),
      	keras.layers.Dense(128, activation = tf.nn.sigmoid),
      	keras.layers.Dense(16, activation = tf.nn.sigmoid),
        keras.layers.Dense(2, activation = tf.nn.softmax)
    ])

    sgd = keras.optimizers.SGD(lr = 0.01, decay = 1e-6,
                               momentum = 0.04, nesterov = True)
    model.compile(optimizer = sgd,
                  loss = 'sparse_categorical_crossentropy',
                  metrics = ['accuracy'])

    model.fit(train_images, train_labels, epochs = 100)

    test_loss, test_acc = model.evaluate(test_images, test_labels)

    print(f"Test accuracy: {test_acc}")
    print(f"Test loss: {test_loss}")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()

    f = open(f"{TFLITE_MODEL_DIR}/mnist.tflite", "wb")
    f.write(tflite_model)
    f.close()
