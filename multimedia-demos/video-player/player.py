#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import os
from pathlib import Path
import signal
import sys

runtime = Path(os.environ.setdefault('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
if not os.environ.get('WAYLAND_DISPLAY'):
    sockets = sorted(path for path in runtime.glob('wayland-*') if path.is_socket())
    if sockets:
        os.environ['WAYLAND_DISPLAY'] = sockets[0].name

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gdk, GdkPixbuf, GLib, Gst, GstVideo, Gtk
except (ImportError, ValueError) as error:
    raise SystemExit(f'GTK 3 / GStreamer Python bindings required: {error}')

Gst.init(None)


def clock_text(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 60:02d}:{seconds % 60:02d}'


def processor_name():
    try:
        compatible = Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
    except OSError:
        return 'i.MX SoM'
    for identifier, title in ((b'fsl,imx8mp', 'i.MX 8M Plus'),
                              (b'fsl,imx93', 'i.MX 93'), (b'fsl,imx95', 'i.MX 95')):
        if identifier in compatible:
            return title
    return 'i.MX SoM'


def video_converter():
    if Gst.ElementFactory.find('imxvideoconvert_g2d'):
        return 'imxvideoconvert_g2d'
    # MX93 has PXP, not a 3D GPU. GL plugins may be installed without usable
    # hardware, so do not select EGL just because their factories exist.
    if Gst.ElementFactory.find('imxvideoconvert_pxp'):
        return ('imxvideoconvert_pxp ! '
                'video/x-raw,format=BGRx,width=640,height=360 ! videoconvert')
    # MX95's decoder emits DMA_DRM buffers. Its OCL converter cannot negotiate
    # this RGBA appsink path; import and scale those buffers with EGL instead.
    if all(Gst.ElementFactory.find(name) for name in
           ('glupload', 'glcolorconvert', 'glcolorscale', 'gldownload')):
        os.environ.setdefault('GST_GL_PLATFORM', 'egl')
        os.environ.setdefault('GST_GL_WINDOW', 'wayland')
        return ('glupload ! glcolorconvert ! glcolorscale ! '
                'video/x-raw(memory:GLMemory),format=RGBA,width=640,height=360 ! '
                'gldownload')
    raise RuntimeError('Missing tested accelerated i.MX video conversion path')


def check_runtime():
    for name in ('playbin', 'appsink'):
        if Gst.ElementFactory.find(name) is None:
            raise RuntimeError(f'Missing GStreamer element: {name}')
    video_converter()


class Player(Gtk.Window):
    def __init__(self, filename=None, windowed=False):
        super().__init__(title='Variscite video player')
        self.set_default_size(800, 480)
        self.connect('destroy', self.shutdown)
        self.connect('key-press-event', self.on_key)
        self.uri = None
        self.playing = False
        self.finished = False
        self.seeking = False
        self.full = not windowed
        self.requested_full = self.full
        self.connect('window-state-event', self.window_state)
        self.connect('map-event', self.mapped)
        self.frames = 0
        self.tick_id = None
        self.closed = False
        self.pipeline = Gst.ElementFactory.make('playbin', 'player')
        # Resize and convert with the BSP accelerator, not on the CPU. Keep only
        # the latest display-sized frame so the UI cannot accumulate latency.
        video_bin = Gst.parse_bin_from_description(
            video_converter() + ' ! '
            'video/x-raw,format=RGBA,width=640,height=360 ! '
            # PXP can provide valid RGB with alpha=0. Video is opaque, so
            # discard that channel rather than render fully transparent frames.
            'videoconvert ! video/x-raw,format=RGB ! '
            'appsink name=video sync=true max-buffers=1 drop=true', True)
        self.sink = video_bin.get_by_name('video')
        self.pipeline.set_property('video-sink', video_bin)
        self.pipeline.connect('deep-element-added', self.element_added)
        self.decoder = 'Preparing decoder'
        self.pixbuf = None
        self.pixel_aspect = 1.0
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus_id = self.bus.connect('message', self.on_message)

        self.get_style_context().add_class('var-player')
        provider = Gtk.CssProvider()
        provider.load_from_data(b'''
        .var-player { background: #10171f; color: #e7edf3; }
        .var-player button { background: rgba(40, 58, 70, 0.85);
          color: #e7edf3; border: 0; border-radius: 999px;
          min-width: 22px; min-height: 22px; padding: 9px; box-shadow: none; }
        .var-player button:hover { background: #377080; }
        .var-player .controls-bar { background: rgba(14, 22, 29, 0.76);
          border-radius: 14px; padding: 10px 14px; }
        .var-player .brand-badge { background: rgba(14, 22, 29, 0.55);
          border-radius: 9px; padding: 8px 12px; }
        .var-player scale trough { background: #344352; min-height: 5px; }
        .var-player scale highlight { background: #35bdd0; }
        .var-player scale slider { background: #d8f5f7; }
        .var-player .brand { color: #35bdd0; font-weight: bold; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        overlay = Gtk.Overlay()
        self.add(overlay)
        self.video = Gtk.DrawingArea()
        self.video.set_size_request(320, 180)
        self.video.set_hexpand(True)
        self.video.set_vexpand(True)
        self.video.connect('draw', self.draw_video)
        overlay.add(self.video)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        layout.set_border_width(12)
        overlay.add_overlay(layout)
        header = Gtk.Box(spacing=8)
        header.set_halign(Gtk.Align.START)
        header.get_style_context().add_class('brand-badge')
        layout.pack_start(header, False, False, 0)
        logo = Path(__file__).with_name('media') / 'variscite-logo-white.png'
        if logo.is_file():
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(logo), 150, 28, True)
            brand = Gtk.Image.new_from_pixbuf(pixbuf)
            brand.set_tooltip_text('Variscite')
            brand.get_accessible().set_name('Variscite logo')
        else:
            brand = Gtk.Label(label='VARISCITE')
        header.pack_start(brand, False, False, 0)
        header.pack_start(Gtk.Label(label=processor_name()), False, False, 0)
        layout.pack_start(Gtk.Box(), True, True, 0)
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        bottom.get_style_context().add_class('controls-bar')
        layout.pack_start(bottom, False, False, 0)
        timeline = Gtk.Box(spacing=8)
        bottom.pack_start(timeline, False, False, 0)
        self.progress = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 0.1
        )
        self.progress.set_draw_value(False)
        self.progress.connect('button-press-event', self.begin_seek)
        self.progress.connect('button-release-event', self.end_seek)
        self.progress.connect('change-value', self.change_seek)
        self.progress.set_sensitive(False)
        timeline.pack_start(self.progress, True, True, 0)
        self.time_label = Gtk.Label(label='00:00 / 00:00')
        timeline.pack_start(self.time_label, False, False, 0)
        controls = Gtk.Box(spacing=8)
        bottom.pack_start(controls, False, False, 0)
        self.play_button = self.button(controls, 'Play', self.toggle_play,
                                       'media-playback-start-symbolic')
        self.button(controls, 'Stop', self.stop, 'media-playback-stop-symbolic')
        self.full_button = self.button(
            controls, 'Window' if self.full else 'Fullscreen',
            self.toggle_fullscreen, 'view-fullscreen-symbolic')
        controls.pack_start(Gtk.Image.new_from_icon_name(
            'audio-volume-high-symbolic', Gtk.IconSize.BUTTON), False, False, 0)
        volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, .05)
        volume.set_size_request(110, -1)
        volume.set_value(.7)
        volume.set_draw_value(False)
        volume.connect('value-changed', lambda scale:
                       self.pipeline.set_property('volume', scale.get_value()))
        self.pipeline.set_property('volume', .7)
        controls.pack_start(volume, False, False, 0)
        self.status = Gtk.Label(label='Ready')
        controls.pack_start(self.status, True, True, 0)
        self.button(controls, 'Open movie', self.choose_file,
                    'folder-open-symbolic')
        self.button(controls, 'Exit', lambda _: self.destroy(),
                    'window-close-symbolic')
        if self.requested_full:
            self.set_decorated(False)
            self.fullscreen()
        self.show_all()
        self.tick_id = GLib.timeout_add(16, self.tick)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM,
                             self.signal_quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT,
                             self.signal_quit)
        if filename:
            GLib.idle_add(self.open_file, filename)

    def button(self, parent, label, callback, icon):
        button = Gtk.Button()
        self.button_icon(button, label, icon)
        button.connect('clicked', callback)
        parent.pack_start(button, False, False, 0)
        return button

    @staticmethod
    def button_icon(button, label, icon):
        button.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        button.set_always_show_image(True)
        button.set_tooltip_text(label)
        button.get_accessible().set_name(label)

    def draw_video(self, widget, context):
        context.set_source_rgb(.025, .035, .045)
        context.paint()
        if self.pixbuf is None:
            return False
        allocation = widget.get_allocation()
        width, height = self.pixbuf.get_width(), self.pixbuf.get_height()
        display_width = width * self.pixel_aspect
        scale = min(allocation.width / display_width,
                    allocation.height / height)
        context.translate((allocation.width - display_width * scale) / 2,
                          (allocation.height - height * scale) / 2)
        context.scale(scale * self.pixel_aspect, scale)
        Gdk.cairo_set_source_pixbuf(context, self.pixbuf, 0, 0)
        context.paint()
        return False

    def mapped(self, *_):
        if self.requested_full:
            self.fullscreen()
        return False

    def window_state(self, _window, event):
        self.full = bool(event.new_window_state & Gdk.WindowState.FULLSCREEN)
        self.button_icon(self.full_button,
                         'Window' if self.full else 'Fullscreen',
                         'view-restore-symbolic' if self.full
                         else 'view-fullscreen-symbolic')
        return False

    def element_added(self, _pipeline, _bin, element):
        factory = element.get_factory()
        if factory and 'Decoder' in factory.get_metadata('klass') and \
                'Video' in factory.get_metadata('klass'):
            self.decoder = factory.get_name()
            compatible = Path('/proc/device-tree/compatible')
            if (self.decoder == 'v4l2h264dec' and compatible.is_file()
                    and b'fsl,imx95' in compatible.read_bytes().split(b'\0')):
                # Avoid stale/future DMA_DRM textures observed on this BSP.
                element.set_property('capture-io-mode', 2)
            print(f'Video decoder: {self.decoder}', flush=True)

    def choose_file(self, _):
        dialog = Gtk.FileChooserDialog(
            title='Open a movie', parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons('Cancel', Gtk.ResponseType.CANCEL,
                           'Open', Gtk.ResponseType.OK)
        file_filter = Gtk.FileFilter()
        file_filter.set_name('Movies')
        file_filter.add_mime_type('video/*')
        dialog.add_filter(file_filter)
        if dialog.run() == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            dialog.destroy()
            self.open_file(filename)
        else:
            dialog.destroy()

    def open_file(self, filename):
        path = Path(filename).expanduser().resolve()
        if not path.is_file():
            self.status.set_text('File not found')
            return False
        self.pipeline.set_state(Gst.State.NULL)
        self.uri = path.as_uri()
        self.pipeline.set_property('uri', self.uri)
        self.frames = 0
        self.finished = False
        self.set_playing(True)
        return False

    def set_playing(self, playing):
        if not self.uri:
            self.status.set_text('Open a movie first')
            return
        if self.finished:
            self.pipeline.seek_simple(Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
            self.finished = False
        state = Gst.State.PLAYING if playing else Gst.State.PAUSED
        if self.pipeline.set_state(state) == Gst.StateChangeReturn.FAILURE:
            self.status.set_text('Cannot start playback; inspect diagnostic log')
            return
        self.playing = playing
        self.button_icon(self.play_button, 'Pause' if playing else 'Play',
                         'media-playback-pause-symbolic' if playing
                         else 'media-playback-start-symbolic')
        self.status.set_text('Playing' if playing else 'Paused')

    def toggle_play(self, _=None):
        self.set_playing(not self.playing)

    def stop(self, _=None):
        self.pipeline.set_state(Gst.State.READY)
        self.playing = False
        self.finished = False
        self.button_icon(self.play_button, 'Play', 'media-playback-start-symbolic')
        self.progress.set_value(0)
        self.progress.set_sensitive(False)
        self.time_label.set_text('00:00 / 00:00')
        self.status.set_text('Stopped')
        self.pixbuf = None
        self.video.queue_draw()

    def begin_seek(self, *_):
        self.seeking = True
        return False

    def end_seek(self, *_):
        self.seek(self.progress.get_value())
        self.seeking = False
        return False

    def change_seek(self, _scale, _scroll, value):
        if not self.seeking:
            self.seek(value)
        return False

    def seek(self, seconds):
        if not self.pipeline.seek_simple(Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(max(0, seconds) * Gst.SECOND)):
            self.status.set_text('This stream does not support seeking')

    def toggle_fullscreen(self, _=None):
        self.requested_full = not self.requested_full
        self.set_decorated(not self.requested_full)
        if self.requested_full:
            self.fullscreen()
        else:
            self.unfullscreen()

    def on_key(self, _window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
        elif event.keyval == Gdk.KEY_space:
            self.toggle_play()
        elif event.keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.toggle_fullscreen()
        elif event.keyval in (Gdk.KEY_s, Gdk.KEY_S):
            self.stop()
        else:
            return False
        return True

    def on_message(self, _bus, message):
        if message.type == Gst.MessageType.ERROR:
            error, debug = message.parse_error()
            print(f'Playback error: {error}\n{debug}', file=sys.stderr, flush=True)
            self.stop()
            self.status.set_text('Playback failed; open another movie')
        elif message.type == Gst.MessageType.EOS:
            self.pipeline.set_state(Gst.State.PAUSED)
            self.playing = False
            self.finished = True
            self.button_icon(self.play_button, 'Replay',
                             'media-playlist-repeat-symbolic')
            self.status.set_text('Finished')
            print(f'Playback finished; displayed {self.frames} frames.', flush=True)

    def tick(self):
        sample = self.sink.emit('try-pull-sample', 0)
        if sample:
            caps = sample.get_caps().get_structure(0)
            width, height = caps.get_value('width'), caps.get_value('height')
            got_aspect, numerator, denominator = caps.get_fraction(
                'pixel-aspect-ratio')
            self.pixel_aspect = (numerator / denominator
                                 if got_aspect and denominator else 1.0)
            buffer = sample.get_buffer()
            info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
            pixels = GLib.Bytes.new(buffer.extract_dup(0, buffer.get_size()))
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
                pixels, GdkPixbuf.Colorspace.RGB, False, 8,
                width, height, info.stride[0])
            self.frames += 1
            self.video.queue_draw()
        if self.playing:
            self.status.set_text('Playing')
        if not self.seeking:
            got_duration, duration = self.pipeline.query_duration(Gst.Format.TIME)
            got_position, position = self.pipeline.query_position(Gst.Format.TIME)
            if got_duration and duration > 0 and got_position:
                self.progress.set_sensitive(True)
                self.progress.set_range(0, duration / Gst.SECOND)
                self.progress.set_value(position / Gst.SECOND)
                self.time_label.set_text(
                    f'{clock_text(position / Gst.SECOND)} / '
                    f'{clock_text(duration / Gst.SECOND)}'
                )
        return not self.closed

    def signal_quit(self):
        self.destroy()
        return GLib.SOURCE_REMOVE

    def shutdown(self, *_):
        if self.closed:
            return
        self.closed = True
        if self.tick_id is not None:
            GLib.source_remove(self.tick_id)
        self.pipeline.set_state(Gst.State.NULL)
        self.bus.disconnect(self.bus_id)
        self.bus.remove_signal_watch()
        Gtk.main_quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('movie', nargs='?')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    check_runtime()
    if args.check:
        print('GTK 3 and GStreamer player dependencies available')
        return
    if not Gtk.init_check()[0]:
        raise SystemExit('Cannot connect to the board display')
    media = Path(__file__).with_name('media')
    sample = next((media / name for name in ('buildings.mp4', 'buildings.avi')
                   if (media / name).is_file()), media / 'chicago.mp4')
    filename = args.movie or (str(sample) if sample.is_file() else None)
    Player(filename, args.windowed)
    Gtk.main()


if __name__ == '__main__':
    main()
