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

from helper import Timer, put_info_on_frame
from config import *

class SampleApplication(Gtk.Window):
    def __init__(self):
        super().__init__(title="Sample Application")
        self.set_border_width(1)
        self.fullscreen()

        container = Gtk.Notebook()
        container.set_show_tabs(False)
        self.add(container)

        get_started_page = GetStarted(container)
        container.append_page(get_started_page)
        
        loading_page = Loading(container)
        container.append_page(loading_page)

        realtime_page = RealTimeDetection(container)
        container.append_page(realtime_page)

class GetStarted(Gtk.Box):
    def __init__(self, parent):
        super().__init__(spacing=10)
        self.__parent = parent
        self.get_started_button = Gtk.Button("GET STARTED")
        self.get_started_button.connect("clicked", self.loading)
        self.get_started_button.set_border_width(20)
        self.get_started_button.set_valign(Gtk.Align.CENTER)
        self.pack_start(self.get_started_button, True, False, 0)

    def loading(self, widget):
        self.__parent.set_current_page(1)

class  Loading(Gtk.Box):
    def __init__(self, parent):
        super().__init__(spacing=10)
        self.__parent = parent        
        self.progressbar = Gtk.ProgressBar()
        self.pack_start(self.progressbar, True, True, 0)
        self.__parent.timeout_id = GLib.timeout_add(50, self.on_timeout, None)
        
    def on_timeout(self, user_data):
        if (self.__parent.get_current_page() == 1):
            new_value = self.progressbar.get_fraction() + 0.01
            if (new_value > 1):
                new_value = 0
                self.__parent.set_current_page(2)
            self.progressbar.set_fraction(new_value)
        return True

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
        self.start_interpreter()

        self.grid = Gtk.Grid(row_spacing=10, column_spacing=10, border_width=18)
        self.add(self.grid)

        check_button_box = Gtk.Box(spacing=6)
        image_box = Gtk.Box(spacing=6)

        self.displayed_image = Gtk.Image()
        image_box.pack_start(self.displayed_image, True, True, 0)

        button = Gtk.CheckButton(label="BUS")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "bus")
        check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="PERSON")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "person")
        check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="CAR")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "car")
        check_button_box.pack_start(button, True, True, 0)

        button = Gtk.CheckButton(label="DOG")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "dog")
        check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CAT")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cat")
        check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CUP")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cup")
        check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="CELL PHONE")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "cell phone")
        check_button_box.pack_start(button, True, True, 0)
        
        button = Gtk.CheckButton(label="ORANGE")
        button.set_active(False)
        button.connect("toggled", self.on_check_button_toggled, "orange")
        check_button_box.pack_start(button, True, True, 0)

        self.grid.attach(image_box, 0, 10, 10, 1)
        self.grid.attach(check_button_box, 0, 3, 2, 1)
        
        GLib.idle_add(self.run_application)

    def on_check_button_toggled(self, button, name):
        if button.get_active():
            if name in self.exclude_list:
                self.exclude_list.remove(name)
        else:
            if name not in self.exclude_list:
                self.exclude_list.append(name)

    def set_displayed_image(self, image):
        image = cv2.resize(image, (430, 350))
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
        video_capture = cv2.VideoCapture(pipeline)
        while video_capture.isOpened():
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
            self.set_displayed_image(frame)

if __name__ == "__main__":
    app = SampleApplication()
    app.connect("delete-event", Gtk.main_quit)
    app.show_all()
    Gtk.main()
