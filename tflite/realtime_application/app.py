# Copyright 2021 Variscite LTD
# SPDX-License-Identifier: BSD-3-Clause
import gi
gi.require_versions({'Gtk': "3.0"})
from gi.repository import GLib, Gtk

from config import *
from detection import RealTimeDetection

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

if __name__ == "__main__":
    app = SampleApplication()
    app.connect("delete-event", Gtk.main_quit)
    app.show_all()
    Gtk.main()
