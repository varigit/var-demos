import importlib.util
from pathlib import Path
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'camera-vision/postprocess.py'
SPEC = importlib.util.spec_from_file_location('detector_postprocess', SOURCE)
decoder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decoder)


class DetectorTests(unittest.TestCase):
    def test_zero_offsets_match_anchor_and_skip_background(self):
        boxes = np.zeros((1, 1, 1, 4), np.float32)
        logits = np.array([[[50., -10., 10.]]])
        priors = np.array([[.5], [.5], [.4], [.2]])
        result = decoder.decode_ssdlite(boxes, logits, priors)
        self.assertEqual(len(result), 1)
        np.testing.assert_allclose(result[0][0], [.3, .4, .7, .6])
        self.assertEqual(result[0][1], 2)
        self.assertGreater(result[0][2], .99)

    def test_duplicate_same_class_boxes_are_suppressed(self):
        priors = np.array([[.5, .5], [.5, .5], [.4, .4], [.4, .4]])
        boxes = np.zeros((2, 4))
        logits = np.array([[0, 10, -10], [0, 9, -10]])
        self.assertEqual(len(decoder.decode_ssdlite(boxes, logits, priors)), 1)

    def test_overlap_of_different_classes_is_kept(self):
        priors = np.array([[.5, .5], [.5, .5], [.4, .4], [.4, .4]])
        boxes = np.zeros((2, 4))
        logits = np.array([[0, 10, -10], [0, -10, 10]])
        self.assertEqual(len(decoder.decode_ssdlite(boxes, logits, priors)), 2)

    def test_invalid_model_output_is_not_drawn(self):
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            decoder.decode_ssdlite(np.full((1, 4), np.nan),
                                   np.ones((1, 3)), np.ones((4, 1)))
        with self.assertRaisesRegex(ValueError, 'anchors'):
            decoder.decode_ssdlite(np.zeros((1, 4)),
                                   np.ones((1, 3)), np.ones((4, 2)))

    def test_postprocessed_indices_are_not_shifted(self):
        result = decoder.decode_postprocessed([
            np.array([[[.1, .2, .8, .9], [.1, .2, .8, .9]]]),
            np.array([[2, 3]]), np.array([[.9, .1]]), np.array([2])])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], 2)


if __name__ == '__main__':
    unittest.main()
