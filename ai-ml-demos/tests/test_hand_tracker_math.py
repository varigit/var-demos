import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'hand-gesture/hand_tracker.py'
SPEC = importlib.util.spec_from_file_location('hand_tracker_math', SOURCE)
tracker = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {
        'tflite_runtime': ModuleType('tflite_runtime'),
        'tflite_runtime.interpreter': ModuleType('tflite_runtime.interpreter')}):
    SPEC.loader.exec_module(tracker)


class TrackerMathTests(unittest.TestCase):
    def test_sigmoid_does_not_overflow(self):
        with np.errstate(over='raise', invalid='raise'):
            values = tracker.HandTracker._sigm(np.array([-1e6, 0., 1e6]))
        np.testing.assert_allclose(values, [0., .5, 1.], atol=1e-20)

    def test_normalization_matches_model(self):
        image = np.array([0, 128, 255], dtype=np.uint8)
        result = tracker.HandTracker._im_normalize(image)
        self.assertEqual(result.dtype, np.float32)
        np.testing.assert_equal(result, [-1, 0, 127 / 128])

    def test_degenerate_alignment_rejected(self):
        hand = object.__new__(tracker.HandTracker)
        with self.assertRaises(ValueError):
            hand._get_triangle(np.array([1., 1.]), np.array([1., 1.]))

    def test_odd_aspect_padding_is_square(self):
        hand = object.__new__(tracker.HandTracker)
        padded, normalized, pad = hand.preprocess_img(
            np.zeros((241, 320, 3), dtype=np.uint8))
        self.assertEqual(padded.shape, (320, 320, 3))
        self.assertEqual(normalized.shape, (256, 256, 3))
        np.testing.assert_equal(pad, [39, 0])


if __name__ == '__main__':
    unittest.main()
