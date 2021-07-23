# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause

import cv2

TFLITE_MODEL_FILE_PATH = "model/ssd_mobilenet_v1_1_default_1.tflite"
TFLITE_LABEL_FILE_PATH = "model/labels_ssd_mobilenet_v1.txt"      

FONT = {'hershey': cv2.FONT_HERSHEY_SIMPLEX,
        'size': 0.8,
        'color': {'black': (0, 0, 0),
                  'blue': (255, 0, 0),
                  'green': (0, 255, 0),
                  'orange': (0, 127, 255),
                  'red': (0, 0, 255),
                  'white': (255, 255, 255)},
        'thickness': 2}
