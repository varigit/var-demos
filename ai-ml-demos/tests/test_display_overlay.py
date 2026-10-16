# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import runtime

SPEC = importlib.util.spec_from_file_location(
    'hd_overlay_utils', ROOT / 'high-resolution-video-detection/utils.py')
utils = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(utils)


class DisplayOverlayTests(unittest.TestCase):
    def tearDown(self):
        runtime.display_size.cache_clear()

    def test_hd_and_full_hd_use_identical_display_geometry(self):
        for width, height in ((1280, 720), (1920, 1080)):
            area = runtime.viewport_geometry((height, width, 3), (800, 480))
            self.assertEqual(area, (0, 15, 800, 450))
            self.assertEqual(runtime.display_box((0, 0, 1, 1), area),
                             (0, 15, 799, 464))
            self.assertEqual(runtime.display_box((.25, .25, .75, .75), area),
                             (200, 127, 599, 352))

    def test_portrait_and_camera_keep_their_aspect_ratio(self):
        self.assertEqual(runtime.viewport_geometry((480, 640), (800, 480)),
                         (80, 0, 640, 480))
        self.assertEqual(runtime.viewport_geometry((1920, 1080), (800, 480)),
                         (265, 0, 270, 480))
        with self.assertRaises(ValueError):
            runtime.viewport_geometry((0, 1920), (800, 480))

    def test_annotations_do_not_modify_the_inference_source(self):
        source = np.full((1080, 1920, 3), 100, np.uint8)
        canvas, area = runtime.display_view(source, (800, 480))
        self.assertEqual(canvas.shape, (480, 800, 3))
        self.assertTrue(np.all(canvas[:15] == 0))
        self.assertTrue(np.all(canvas[15:465] == 100))
        canvas[:] = 255
        self.assertTrue(np.all(source == 100))
        self.assertEqual(area, (0, 15, 800, 450))

    def test_hd_and_full_hd_render_same_text_and_boxes(self):
        results = [{'box': (.25, .25, .75, .75), 'class': 1, 'score': .9}]
        rendered = []
        with patch.object(utils, 'draw_soc_temperature'):
            for width, height in ((1280, 720), (1920, 1080)):
                source = np.full((height, width, 3), 100, np.uint8)
                rendered.append(utils.put_info_on_frame(
                    source, results, '0:00:00.009', {1: 'person'},
                    'ssd_mobilenet_v1.tflite', 'video', 30., (800, 480)))
                self.assertTrue(np.all(source == 100))
        np.testing.assert_array_equal(rendered[0], rendered[1])

    def test_display_override_and_invalid_fallback(self):
        for value, expected in [('1280x800', (1280, 800)),
                                ('800,480', (800, 480)),
                                ('0x480', (800, 480)),
                                ('nonsense', (800, 480))]:
            runtime.display_size.cache_clear()
            with patch.dict(runtime.os.environ, {'VAR_AI_DISPLAY_SIZE': value}):
                self.assertEqual(runtime.display_size(), expected)

    def test_framebuffer_detection_and_missing_display(self):
        with patch.dict(runtime.os.environ, {}, clear=True), \
                patch.object(runtime.Path, 'read_text', return_value='800,480'):
            self.assertEqual(runtime.display_size(), (800, 480))
        runtime.display_size.cache_clear()
        with patch.dict(runtime.os.environ, {}, clear=True), \
                patch.object(runtime.Path, 'read_text', side_effect=OSError):
            self.assertEqual(runtime.display_size(), (800, 480))


if __name__ == '__main__':
    unittest.main()
