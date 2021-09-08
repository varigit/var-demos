# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import numpy as np
import tensorflow as tf
from tensorflow import keras

mnist_digits = keras.datasets.mnist
(train_images, train_labels), (test_images, test_labels) = mnist_digits.load_data()

train_images = train_images / 255.0
test_images = test_images / 255.0
            
model = keras.Sequential([
    keras.layers.Flatten(input_shape = (28, 28)),
    keras.layers.Dense(128, activation = tf.nn.relu),
    keras.layers.Dense(10)
])

model.compile(optimizer = 'adam',
              loss = tf.keras.losses.SparseCategoricalCrossentropy(from_logits = True),
              metrics = ['accuracy'])

model.fit(train_images, train_labels, epochs = 10)

test_loss, test_acc = model.evaluate(test_images, test_labels)

print(f"Test accuracy: {test_acc}")
print(f"Test loss: {test_loss}")

converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

f = open("model/mnist.tflite", "wb")
f.write(tflite_model)
f.close()
