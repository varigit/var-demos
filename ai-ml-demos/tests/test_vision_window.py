from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import vision_window as display


class WindowTests(unittest.TestCase):
    def tearDown(self):
        display.destroyAllWindows()

    def test_fullscreen_is_prepared_and_populated_before_mapping(self):
        gtk, gdk, pixbuf, glib = Mock(), Mock(), Mock(), Mock()
        with patch.object(display, '_bindings', return_value=(gtk, gdk, pixbuf, glib)):
            display.namedWindow('Demo')
            display.setWindowProperty('Demo', 0, 1)
            window = gtk.Window.return_value
            window.show_all.assert_not_called()
            window.set_decorated.assert_called_with(False)
            window.fullscreen.assert_called_once()
            window.show_all.side_effect = lambda: self.assertIsNotNone(display._windows['Demo'].pixbuf)
            display.imshow('Demo', np.zeros((480, 800, 3), np.uint8))
            window.show_all.assert_called_once()
            display.imshow('Demo', np.zeros((480, 800, 3), np.uint8))
            window.show_all.assert_called_once()

    def test_pixel_bytes_are_rgb_and_owned(self):
        gtk, gdk, pixbuf, glib = Mock(), Mock(), Mock(), Mock()
        with patch.object(display, '_bindings', return_value=(gtk, gdk, pixbuf, glib)):
            frame = np.array([[[10, 20, 30]]], dtype=np.uint8)
            display.imshow('Demo', frame)
            pixels = glib.Bytes.new.call_args.args[0]
            frame[:] = 0
            self.assertEqual(pixels, bytes([30, 20, 10]))

    def test_close_is_visible_to_loop_and_cleanup_is_repeatable(self):
        gtk, gdk, pixbuf, glib = Mock(), Mock(), Mock(), Mock()
        gtk.events_pending.return_value = False
        with patch.object(display, '_bindings', return_value=(gtk, gdk, pixbuf, glib)):
            display.imshow('Demo', np.zeros((1, 1, 3), np.uint8))
            display._windows['Demo'].close()
            self.assertEqual(display.getWindowProperty('Demo', 4), 0)
            self.assertEqual(display.waitKey(1), 27)
            display.destroyAllWindows()
            display.destroyAllWindows()
            self.assertEqual(display._windows, {})
