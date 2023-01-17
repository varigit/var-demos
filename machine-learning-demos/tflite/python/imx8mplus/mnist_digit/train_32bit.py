# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import os

import numpy as np
import tensorflow as tf
from tensorflow import keras

TFLITE_MODEL_DIR = os.path.join(os.getcwd(), "model")

mnist_digits = keras.datasets.mnist
(train_images, train_labels), (test_images, test_labels) = mnist_digits.load_data()

train_images = train_images.astype(np.float32) / 255.0
test_images = test_images.astype(np.float32) / 255.0

model = keras.Sequential([
    keras.layers.Flatten(input_shape = (28, 28)),
    keras.layers.Dense(128, activation = tf.nn.relu),
    keras.layers.Dense(10)
])

model.compile(optimizer = 'adam',
              loss = tf.keras.losses.SparseCategoricalCrossentropy(
                  from_logits = True),
              metrics = ['accuracy'])

model.fit(
    train_images,
    train_labels,
    epochs=5,
)
model.summary()

test_loss, test_acc = model.evaluate(test_images, test_labels)

print(f"Test accuracy: {test_acc}")
print(f"Test loss: {test_loss}")

converter = tf.lite.TFLiteConverter.from_keras_model(model)

tflite_model = converter.convert()

f = open(f"{TFLITE_MODEL_DIR}/mnist_32bit.tflite", "wb")
f.write(tflite_model)
f.close()
