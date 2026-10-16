# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import argparse
import sys

import cv2
import numpy as np
from PIL import Image

try:
    from tflite_runtime.interpreter import Interpreter
    from tflite_runtime.interpreter import load_delegate
except ImportError:
    sys.exit("No TensorFlow Lite Runtime module found!")

from helper.config import TITLE
from helper.opencv import create_window, put_info_on_frame, put_fps_on_frame
from helper.utils import load_labels, Timer, Framerate

from runtime import demo_session, managed_capture, ThermalPacer, register_cleanup, warm_up_model, startup_step, video_work_size, video_source_size

# Constants
import vision_window

EXT_DELEGATE_PATH = "/usr/lib/libvx_delegate.so"

def open_video_capture(args):
    if (args['videofmw'] == "opencv"):
        pipeline = "{}".format(args['video'])
    elif (args['videofmw'] == "gstreamer"):
        size = video_work_size(args['video'])
        dimensions = f',width={size[0]},height={size[1]}' if size else ''
        pipeline = "filesrc location={} ! qtdemux name=d d.video_0 ! " \
                   "decodebin ! imxvideoconvert_g2d ! " \
                   f"video/x-raw,format=RGBx{dimensions} ! " \
                   "videoconvert ! video/x-raw,format=BGR ! " \
                   "appsink name=opencvsink max-buffers=1 drop=true sync=true".format(args['video'])
    else:
        raise SystemExit("videofmw: invalid value. Use 'opencv' or 'gstreamer'")
    return managed_capture(pipeline)

@demo_session()
def video_classification(args):
    labels = load_labels(args['label'])

    ext_delegate_options = {}
    ext_delegate = [load_delegate(EXT_DELEGATE_PATH, ext_delegate_options)]

    interpreter = Interpreter(model_path=args['model'], experimental_delegates=ext_delegate, num_threads=1)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    warm_up_model(interpreter)

    _, height, width, _ = input_details[0]['shape']

    video_capture = open_video_capture(args)
    video_size = video_source_size(args['video'])
    window_created = False
    ready = False
    framerate = Framerate()
    pacer = ThermalPacer(clock_paced=True)
    while video_capture.isOpened():
        with framerate.fpsit():
            if not pacer.wait(lambda: pacer.cooling and vision_window.waitKey(1) == 27):
                break
            check, frame = video_capture.read()
            if check is not True:
                break
            resized_frame = cv2.resize(frame, (width, height))
            resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            resized_frame = np.expand_dims(resized_frame, axis = 0)

            interpreter.set_tensor(input_details[0]['index'], resized_frame)
            timer = Timer()
            with timer.timeit():
                interpreter.invoke()

            output_details = interpreter.get_output_details()[0]
            output = np.squeeze(interpreter.get_tensor(output_details['index']))

            k = int(args['kresults'])
            top_k = output.argsort()[-k:][::-1]
            result = []
            for i in top_k:
                score = float(output[i] / 255.0)
                result.append((i, score))

            frame = put_info_on_frame(frame, result, labels,
                                      timer.time, args['model'], args['video'],
                                      video_size=video_size)
            frame = put_fps_on_frame(frame, framerate.fps)
            if not window_created:
                create_window(TITLE, args['windowed'])
                window_created = True
            vision_window.imshow(TITLE, frame)
            if not ready:
                vision_window.waitKey(1)
                startup_step('Frames and NPU inference ready', ready=True)
                ready = True
            if vision_window.waitKey(1) == 27:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
          '--model',
          default='model/mobilenet_v1_1.0_224_quant.tflite',
          help='.tflite model to be executed')
    parser.add_argument(
          '--label',
          default='model/labels_mobilenet_quant_v1_224.txt',
          help='name of file containing labels')
    parser.add_argument(
          '--video',
          default='media/video.mp4',
          help='video file to be classified')
    parser.add_argument(
          '--videofmw',
          default='opencv',
          help='opencv or gstreamer')
    parser.add_argument(
          '--kresults',
          default='3',
          help='number of displayed results')
    parser.add_argument(
          '--windowed',
          action='store_true',
          help='open the video in a window instead of fullscreen')
    args = vars(parser.parse_args())
    video_classification(args)
