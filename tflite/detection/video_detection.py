# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse
from contextlib import contextmanager
from datetime import timedelta
from time import monotonic

import cv2
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

from helper.config import TITLE
from helper.opencv import put_info_on_frame
from helper.utils import get_tensor, load_labels, Timer

def open_video_capture(args):
    if (args['videofmw'] == "opencv"):
        pipeline = "{}".format(args['video'])
    elif (args['videofmw'] == "gstreamer"):
        pipeline = "filesrc location={} ! qtdemux name=d d.video_0 ! " \
                   "decodebin ! queue leaky=downstream max-size-buffers=1 ! " \
                   "queue ! imxvideoconvert_g2d ! " \
                   "videoconvert ! appsink".format(args['video'])
    else:
        raise SystemExit("videofmw: invalid value. Use 'opencv' or 'gstreamer'")
    return cv2.VideoCapture(pipeline)

def image_detection(args):
    labels = load_labels(args['label'])

    interpreter = Interpreter(model_path=args['model'])
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    model_height, model_width = input_details[0]['shape'][1:3]
    
    video_capture = open_video_capture(args)
    while video_capture.isOpened():
        check, frame = video_capture.read()
        if check is not True:
            break
        
        resized_frame = cv2.resize(frame, (model_width, model_height))
        resized_frame = np.expand_dims(resized_frame, axis = 0)  
            
        interpreter.set_tensor(input_details[0]['index'], resized_frame)
        timer = Timer()
        with timer.timeit():
            interpreter.invoke()

        positions = get_tensor(0, interpreter, output_details, squeeze=True)
        classes = get_tensor(1, interpreter,  output_details, squeeze=True)
        scores = get_tensor(2, interpreter, output_details, squeeze=True)

        result = []
        for idx, score in enumerate(scores):
            if score > 0.5:
                result.append({'pos': positions[idx], '_id': classes[idx]})

        frame = put_info_on_frame(frame, result, timer.time, labels,
                                  args['model'], args['video'])
        cv2.imshow(TITLE, frame)
        cv2.waitKey(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='model/ssd_mobilenet_v1_1_default_1.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='model/labels_ssd_mobilenet_v1.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--video',
          default='media/video.mp4',
          help='image file to be classified')
    parser.add_argument(
          '--videofmw',
          default='opencv',
          help='opencv or gstreamer')
    args = vars(parser.parse_args())
    image_detection(args)
