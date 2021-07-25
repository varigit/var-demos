# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import re
import threading
import time

import cv2
import gi
import numpy as np
from PIL import Image
from tflite_runtime.interpreter import Interpreter

gi.require_versions({'GdkPixbuf': "2.0", 'Gtk': "3.0"})
from gi.repository.GdkPixbuf import Colorspace, Pixbuf
from gi.repository import GLib, Gtk

from helper import Framerate, Timer, put_info_on_frame
from config import *

class RealTimeDetection(Gtk.Box):
    def __init__(self, parent):
        super().__init__(spacing=10)
        self.model_path = TFLITE_MODEL_FILE_PATH
        self.labels_path = TFLITE_LABEL_FILE_PATH
        self.exclude_list = SSD_LABELS_LIST

        self.labels = self.load_labels()
        self.interpreter = " "
        self.input_details = " "
        self.output_details = " "
        self.set_homogeneous(False)
        self.start_interpreter()

        self.grid = Gtk.Grid(row_spacing=10, column_spacing=10, border_width=10)
        self.add(self.grid)

        # LABELS TO CHECK
        self.check_button_box = Gtk.Box(Gtk.Orientation.HORIZONTAL,spacing=1)

        button = Gtk.CheckButton(label="BUS")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "bus")
        self.check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="PERSON")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "person")
        self.check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="CAR")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "car")
        self.check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="DOG")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "dog")
        self.check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CAT")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cat")
        self.check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CUP")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cup")
        self.check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CELL PHONE")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cell phone")
        self.check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="BANANA")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "banana")
        self.check_button_box.pack_start(button, True, True, 0)

        self.grid.attach(self.check_button_box, 0, 0, 2, 1)

         # IMAGE BOX
        self.displayed_image = Gtk.Image()
        self.image_box = Gtk.Box(spacing=1)
        self.image_box.pack_start(self.displayed_image, True, True, 0)
        self.grid.attach(self.image_box, 0, 1, 2, 1)

        # SCREENSHOT
        self.screenshot_value_label = Gtk.Label.new(None)
        # Screenshot Box
        self.screenshot_button = Gtk.Button(label="SCREENSHOT")
        self.screenshot_button.connect("clicked", self.on_screenshot_button_clicked)
        self.screenshot_box = Gtk.Box(spacing=10)
        self.screenshot_box.pack_start(self.screenshot_button, True, False, 0)
        self.grid.attach(self.screenshot_box, 0, 3, 2, 1)
        # Screenshot Value Box
        self.screenshot_value_box = Gtk.Box(spacing=10)
        self.screenshot_value_box.pack_start(self.screenshot_value_label, True, True, 0)
        self.grid.attach(self.screenshot_value_box, 0, 4, 2, 1)
        self.add(self.screenshot_value_label)

        # Inference Value Label
        self.inference_value_label = Gtk.Label.new(None)
        # Inferente Time Box
        self.inference_label = Gtk.Label()
        self.inference_label.set_markup("INFERENCE TIME")
        self.inference_box = Gtk.Box(spacing=10)
        self.inference_box.pack_start(self.inference_label, True, True, 0)
        self.grid.attach(self.inference_box, 1, 3, 2, 1)
        # Inferente Time Value Box
        self.inference_value_box = Gtk.Box(spacing=10)
        self.inference_value_box.pack_start(self.inference_value_label, True, True, 0)
        self.grid.attach(self.inference_value_box, 1, 4, 2, 1)

        # FPS Label
        self.fps_value_label = Gtk.Label.new(None)
        # FPS Box
        self.fps_label = Gtk.Label()
        self.fps_label.set_markup("FPS")
        self.fps_box = Gtk.Box(spacing=10)
        self.fps_box.pack_start(self.fps_label, True, True, 0)
        self.grid.attach(self.fps_box, 2, 3, 2, 1)
        # FPS Value Box
        self.fps_value_box = Gtk.Box(spacing=10)
        self.fps_value_box.pack_start(self.fps_value_label, True, True, 0)
        self.grid.attach(self.fps_value_box, 2, 4, 2, 1)

        # Start
        GLib.idle_add(self.run_application)

    def on_screenshot_button_clicked(self, widget):
        print("Screenshot")
        self.screenshot_value_label.set_text("{}".format("aaa"))

    def on_check_button_toggled(self, button, name):
        if button.get_active():
            if name in self.exclude_list:
                self.exclude_list.remove(name)
        else:
            if name not in self.exclude_list:
                self.exclude_list.append(name)

    def set_displayed_image(self, image):
        image = cv2.resize(image, (320, 240))
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        height, width = image.shape[:2]
        arr = np.ndarray.tobytes(image)
        pixbuf = Pixbuf.new_from_data(arr, Colorspace.RGB, False, 8, width, height, width * 3, None, None)
        self.displayed_image.set_from_pixbuf(pixbuf)
    
    def run_application(self):
        thread = threading.Thread(target=self.image_detection)
        thread.daemon = True
        thread.start()

    def load_labels(self):
        p = re.compile(r'\s*(\d+)(.+)')
        with open(self.labels_path, 'r', encoding='utf-8') as f:
            lines = (p.match(line).groups() for line in f.readlines())
            return {int(num): text.strip() for num, text in lines}
    
    def start_interpreter(self):
        self.interpreter = Interpreter(model_path=self.model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def get_tensor(self,index, squeeze=False):
        if squeeze:
            return np.squeeze(self.interpreter.get_tensor(self.output_details[index]['index']))

    def image_detection(self):
        model_height, model_width = self.input_details[0]['shape'][1:3]
        pipeline = "v4l2src device={} ! video/x-raw,width=320,height=240,framerate=30/1 ! queue leaky=downstream "\
                   "max-size-buffers=1 ! videoconvert ! appsink".format("/dev/video1")
        framerate = Framerate()
        video_capture = cv2.VideoCapture(pipeline)
        while video_capture.isOpened():
            with framerate.fpsit():
                _, frame = video_capture.read()

                resized_frame = cv2.resize(frame, (model_width, model_height))
                resized_frame = np.expand_dims(resized_frame, axis = 0)

                self.interpreter.set_tensor(self.input_details[0]['index'], resized_frame)
                timer = Timer()
                with timer.timeit():
                    self.interpreter.invoke()

                positions = self.get_tensor(0, squeeze=True)
                classes = self.get_tensor(1, squeeze=True)
                scores = self.get_tensor(2, squeeze=True)

                result = []
                for idx, score in enumerate(scores):
                    if score > 0.5 and (self.labels[classes[idx]] not in self.exclude_list):
                        result.append({'pos': positions[idx], '_id': classes[idx]})

                frame = put_info_on_frame(frame, result, self.labels)
            self.inference_value_label.set_text("{}".format(timer.time))
            self.fps_value_label.set_text("{}".format(int(framerate.fps)))
            self.set_displayed_image(frame)

