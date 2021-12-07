# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import os

import numpy as np
import PIL
from PIL import Image
import tensorflow as tf
from tensorflow import keras

import os

DATASET_DIR = os.path.join(os.getcwd(), "dataset")
DATASET_TRAIN_DIR = os.path.join(os.getcwd(), "dataset", "train")
DATASET_TEST_DIR = os.path.join(os.getcwd(), "dataset", "test")
TFLITE_MODEL_DIR = os.path.join(os.getcwd(), "model")

train_images = 0

def representative_dataset_gen():
  for input_value in tf.data.Dataset.from_tensor_slices(train_images).batch(1).take(100):
    yield [input_value]

def convert_to_8b_grayscale(image_path, maxsize):
	image = Image.open(image_path).convert('L')
	image_width, image_height = image.size
	if image_width != image_height:
		m_min_d = min(image_width, image_height)
		image = image.crop((0, 0, m_min_d, m_min_d))
	image.thumbnail(maxsize, PIL.Image.ANTIALIAS)
	return np.asarray(image, dtype=np.float32)

def load_image_dataset(path_dir, maxsize, reshape_size):
    images_list = []
    labels_list = []
    labels_dict = {}

    for root, directories, files in os.walk(path_dir, topdown=True):
        for idx, directory in enumerate(directories):
            labels_dict[directory] = idx

        for file in files:
            img = convert_to_8b_grayscale(os.path.join(root, file), maxsize)
            images_list.append(img.reshape(reshape_size))
            labels_list.append(labels_dict[os.path.basename(root)])

    with open(f"{TFLITE_MODEL_DIR}/tflite.txt", "w") as labels_file:
        for key, _ in labels_dict.items():
            labels_file.write(str(key) + "\n")

    return (np.asarray(images_list), np.asarray(labels_list))

def main():
    global train_images
    maxsize = 50, 50
    maxsize_w, maxsize_h = maxsize

    (train_images, train_labels) = load_image_dataset(
                                        path_dir=DATASET_TRAIN_DIR,
                                        maxsize=maxsize,
                                        reshape_size=(maxsize_w, maxsize_h, 1))

    (test_images, test_labels) = load_image_dataset(
                                        path_dir=DATASET_TEST_DIR,
                                        maxsize=maxsize,
                                        reshape_size=(maxsize_w, maxsize_h, 1))

    train_images = train_images / 255.0
    test_images = test_images / 255.0

    model = keras.Sequential([
        keras.layers.Flatten(input_shape = (maxsize_w, maxsize_h , 1)),
      	keras.layers.Dense(128, activation = tf.nn.sigmoid),
      	keras.layers.Dense(16, activation = tf.nn.sigmoid),
        keras.layers.Dense(max(train_labels) + 1, activation = tf.nn.softmax)
    ])

    sgd = keras.optimizers.SGD(
                           lr=0.01,
                           decay=1e-6,
                           momentum=0.04,
                           nesterov=True)
    model.compile(
          optimizer=sgd,
          loss='sparse_categorical_crossentropy',
          metrics=['accuracy'])

    model.fit(train_images, train_labels, epochs=10000)
    model.summary()

    test_loss, test_acc = model.evaluate(test_images, test_labels)

    print(f"Test accuracy: {test_acc}")
    print(f"Test loss: {test_loss}")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.experimental_new_converter = True

    converter.target_spec.supported_types = [tf.int8]
    converter.inference_input_type = tf.int8 
    converter.inference_output_type = tf.int8 
    quantized_tflite_model = converter.convert()
    
    f = open(f"{TFLITE_MODEL_DIR}/quantized_tflite_model.tflite", "wb")
    f.write(quantized_tflite_model)
    f.close()

if __name__ == "__main__":
    main()
