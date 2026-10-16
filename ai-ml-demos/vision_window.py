# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""GTK presentation: populate the first frame before mapping a fullscreen window.

The small HighGUI-compatible surface keeps image processing in OpenCV while
avoiding its briefly mapped, decorated Qt window during fullscreen startup.
GTK is loaded only when a display is requested; headless inference stays usable.
"""

from collections import deque
from functools import lru_cache
import time
import cv2
import os
from pathlib import Path

_windows = {}
_keys = deque()


@lru_cache(maxsize=1)
def _bindings():
    runtime = Path(os.environ.setdefault('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
    if not os.environ.get('WAYLAND_DISPLAY'):
        sockets = sorted(path for path in runtime.glob('wayland-*') if path.is_socket())
        if sockets:
            os.environ['WAYLAND_DISPLAY'] = sockets[0].name
            os.environ.setdefault('GDK_BACKEND', 'wayland')
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib
    if not Gtk.init_check()[0]:
        raise RuntimeError('Board display unavailable')
    return Gtk, Gdk, GdkPixbuf, GLib


class _Window:
    def __init__(self, title):
        Gtk, Gdk, _, _ = _bindings()
        self.window = Gtk.Window(title=title)
        self.area = Gtk.DrawingArea()
        self.window.add(self.area)
        self.pixbuf = None
        self.shown = False
        self.closed = False
        self.fullscreen = False
        style = Gtk.CssProvider()
        style.load_from_data(b'.vision-window { background-color: #000; }')
        self.window.get_style_context().add_class('vision-window')
        self.window.get_style_context().add_provider(style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window.connect('destroy', self.close)
        self.window.connect('key-press-event', self.key)
        self.area.connect('draw', self.draw)

    def close(self, *_):
        self.closed = True
        _keys.append(27)

    def key(self, _, event):
        _, Gdk, _, _ = _bindings()
        _keys.append(27 if event.keyval == Gdk.KEY_Escape else Gdk.keyval_to_unicode(event.keyval))
        return True

    def draw(self, widget, context):
        context.set_source_rgb(0, 0, 0)
        context.paint()
        if self.pixbuf is None:
            return False
        _, Gdk, _, _ = _bindings()
        allocation = widget.get_allocation()
        width, height = self.pixbuf.get_width(), self.pixbuf.get_height()
        scale = min(allocation.width / width, allocation.height / height)
        context.translate((allocation.width - width * scale) / 2,
                          (allocation.height - height * scale) / 2)
        context.scale(scale, scale)
        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, 0, 0)
        context.paint()
        return False


def namedWindow(title, flags=0):
    if title not in _windows or _windows[title].closed:
        _windows[title] = _Window(title)


def setWindowProperty(title, prop, value):
    namedWindow(title)
    item = _windows[title]
    item.fullscreen = bool(value)
    item.window.set_decorated(not item.fullscreen)
    if item.fullscreen:
        item.window.fullscreen()
    else:
        item.window.unfullscreen()


def imshow(title, frame):
    namedWindow(title)
    item = _windows[title]
    _, _, GdkPixbuf, GLib = _bindings()
    height, width = frame.shape[:2]
    # Own the RGB bytes until GTK has drawn them; the inference loop reuses BGR.
    pixels = GLib.Bytes.new(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).tobytes())
    item.pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        pixels, GdkPixbuf.Colorspace.RGB, False, 8, width, height, width * 3)
    if not item.shown:
        item.window.set_default_size(width, height)
        item.window.show_all()
        item.shown = True
    item.area.queue_draw()


def waitKey(delay=0):
    deadline = time.monotonic() + delay / 1000 if delay > 0 else None
    while True:
        if _windows:
            Gtk, _, _, _ = _bindings()
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
        if _keys:
            return _keys.popleft()
        if deadline is not None and time.monotonic() >= deadline:
            return -1
        time.sleep(.001)


def getWindowProperty(title, prop):
    item = _windows.get(title)
    return float(item is not None and item.shown and not item.closed)


def destroyAllWindows():
    for item in list(_windows.values()):
        if not item.closed:
            item.window.destroy()
    _windows.clear()
    _keys.clear()
