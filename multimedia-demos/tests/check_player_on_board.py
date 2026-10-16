# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
# Hardware integration test: opens a temporary window on the board display.

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'video-player'))
from player import GLib, Gst, Gtk, Player, processor_name

if not Gtk.init_check()[0]:
    raise SystemExit('Board display unavailable')
player = Player(sys.argv[1])
def widgets(root):
    yield root
    if isinstance(root, Gtk.Container):
        for child in root.get_children():
            yield from widgets(child)


assert any(isinstance(widget, Gtk.Image)
           and widget.get_accessible().get_name() == 'Variscite logo'
           for widget in widgets(player)), \
    'Installed player header is missing the Variscite logo'
assert isinstance(player.get_child(), Gtk.Overlay)
assert any(isinstance(widget, Gtk.Label) and widget.get_text() == processor_name()
           for widget in widgets(player)), 'Player header is missing the SoM name'
assert not hasattr(player, 'filename'), 'Movie filename is visible in header'
errors = []


def verify(function):
    def callback():
        try:
            function()
        except Exception as error:
            errors.append(str(error))
            player.destroy()
        return False
    return callback


def pause():
    assert player.frames > 5, 'No decoded video frames reached the display'
    assert not player.pixbuf.get_has_alpha(), 'Video must be opaque'
    rgb = player.pixbuf.get_pixels()
    assert max(rgb) - min(rgb) > 24, 'Decoded reference frame is blank'
    assert sum(rgb) / len(rgb) > 10, 'Decoded reference frame is black'
    assert player.full, 'Player did not enter fullscreen'
    player.set_playing(False)


def resume():
    assert player.pipeline.get_state(Gst.SECOND)[1] == Gst.State.PAUSED
    player.seek(5)
    player.set_playing(True)
    player.toggle_fullscreen()


def stop():
    assert player.playing
    assert not player.full, 'Player did not leave fullscreen'
    player.toggle_fullscreen()
    player.stop()
    assert player.pipeline.get_state(Gst.SECOND)[1] == Gst.State.READY
    assert not player.progress.get_sensitive()
    player.set_playing(True)


GLib.timeout_add_seconds(2, verify(pause))
GLib.timeout_add_seconds(4, verify(resume))
GLib.timeout_add_seconds(7, verify(stop))
def close():
    assert player.full, 'Player did not re-enter fullscreen'
    player.destroy()


GLib.timeout_add_seconds(10, verify(close))
Gtk.main()
assert player.pipeline.get_state(Gst.SECOND)[1] == Gst.State.NULL
if errors:
    raise SystemExit('; '.join(errors))
print(f'PASS: play, pause, seek, stop, restart, close; {player.frames} frames')
