# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'camera-vision'))
import people_segmentation as people
import manager


class PeopleSegmentationTests(unittest.TestCase):
    def test_input_is_rgb_float_zero_to_one(self):
        rgb = np.array([[[0, 127, 255]]], np.uint8)
        original = rgb.copy()
        value = people.prepare_people_input(rgb, dict(dtype=np.float32))
        np.testing.assert_allclose(value, [[[[0, 127 / 255, 1]]]])
        np.testing.assert_array_equal(rgb, original)
        self.assertEqual(value.dtype, np.float32)
        with self.assertRaises(ValueError):
            people.prepare_people_input(rgb, dict(dtype=np.uint8))

    def test_threshold_returns_only_background_and_person(self):
        scores = np.full((1, 144, 256, 1), .5, np.float32)
        scores[0, 0, 0, 0] = .8
        mask = people.decode_people(scores)
        self.assertEqual(mask[0, 0], 15)
        self.assertEqual(mask[0, 1], 0)
        self.assertEqual(set(np.unique(mask)), {0, 15})
        self.assertFalse(np.shares_memory(scores, mask))

    def test_invalid_shape_probabilities_and_threshold_are_rejected(self):
        for invalid in (np.zeros((1, 256, 256, 1)),
                        np.full((1, 144, 256, 1), np.nan),
                        np.full((1, 144, 256, 1), 1.1),
                        np.full((1, 144, 256, 1), -.1)):
            with self.assertRaises(ValueError):
                people.decode_people(invalid)
        for threshold in (-1, 2):
            with self.assertRaises(ValueError):
                people.decode_people(np.zeros((1, 144, 256, 1)), threshold)

    def test_tensor_view_does_not_escape_into_mask(self):
        scores = np.ones((1, 144, 256, 1), np.float32)
        engine = Mock()
        engine.tensor.return_value = lambda: scores
        mask = people.read_people(engine, dict(index=9))
        engine.get_tensor.assert_not_called()
        scores[:] = 0
        self.assertTrue((mask == 15).all())

    def test_all_three_soms_offer_same_order_modes_and_qualities(self):
        catalog = manager.load_catalog()
        for platform in ('imx8mplus', 'imx93', 'imx95'):
            items = manager.launchers_for(catalog, platform)[12:15]
            names = [item['id'].removeprefix('ethosu-').removeprefix('neutron-')
                     for item in items]
            self.assertEqual(names, ['people-segmentation-image',
                                     'people-segmentation-video', 'people-segmentation-camera'])
            self.assertTrue(items[2]['select_camera'])
            self.assertEqual(items[1]['video_prompt'], 'Choose a People Video')
            demo = manager.launcher_video_demo(items[1], platform)
            resolutions = manager.video_resolutions(catalog, demo, items[1]['video_task'])
            self.assertEqual([item['id'] for item in resolutions], ['720p', '1080p'])
            for resolution in resolutions:
                clips = manager.video_choices(catalog, demo, resolution['id'], 'face')
                self.assertTrue(clips)
                self.assertTrue(all('1117992' in clip['path'] for clip in clips))
