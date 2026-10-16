import importlib.util
from pathlib import Path
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / 'hand-gesture/gestures.py'
SPEC = importlib.util.spec_from_file_location('gestures', SOURCE)
gestures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gestures)


class GestureTests(unittest.TestCase):
    def hand(self, fingers):
        points = np.zeros((21, 2), dtype=float)
        for base, middle, tip, x, extended in zip(
                (5, 9, 13, 17), (6, 10, 14, 18), (8, 12, 16, 20),
                (-2, -1, 1, 2), fingers):
            points[base] = (x, 2)
            points[middle] = (x, 3)
            points[tip] = (x, 6 if extended else 2)
        points[4] = points[9]
        return points

    def test_gestures(self):
        for fingers, label in (
                ([True] * 4, 'Open hand'), ([False] * 4, 'Closed fist'),
                ([True, False, False, False], 'Pointing'),
                ([True, True, False, False], 'Victory'),
                ([False, True, False, False], 'Unknown')):
            self.assertEqual(gestures.classify(self.hand(fingers)), label)

    def test_rotated_gestures(self):
        hand = self.hand([True, True, False, False])
        rotation = np.array([[0, -1], [1, 0]])
        self.assertEqual(gestures.classify(hand @ rotation), 'Victory')

    def test_no_hand_and_invalid_points(self):
        self.assertEqual(gestures.classify(None), 'No hand')
        self.assertEqual(gestures.classify(np.zeros((2, 2))), 'Unknown')
        self.assertEqual(gestures.classify(np.full((21, 2), np.nan)), 'Unknown')

    def test_stabilization_and_clear(self):
        now = [0.0]
        stable = gestures.StableGesture(clock=lambda: now[0])
        self.assertEqual(stable.update('Victory'), 'Recognizing...')
        now[0] = .4
        self.assertEqual(stable.update('Victory'), 'Victory')
        self.assertEqual(stable.update('Open hand'), 'Recognizing...')
        self.assertEqual(stable.update('No hand'), 'No hand')

    def test_alternation_never_commits(self):
        now = [0.0]
        stable = gestures.StableGesture(clock=lambda: now[0])
        for index in range(20):
            now[0] += .1
            self.assertEqual(stable.update(
                'Victory' if index % 2 else 'Open hand'), 'Recognizing...')

    def test_landmark_smoothing_and_loss(self):
        smooth = gestures.SmoothLandmarks()
        hand = self.hand([True] * 4)
        np.testing.assert_equal(smooth.update(hand), hand)
        np.testing.assert_allclose(smooth.update(hand + .5), hand + .3)
        self.assertIsNone(smooth.update(None))
        np.testing.assert_equal(smooth.update(hand + 10), hand + 10)

    def test_large_hand_change_resets_smoothing(self):
        smooth = gestures.SmoothLandmarks()
        hand = self.hand([True] * 4)
        smooth.update(hand)
        np.testing.assert_equal(smooth.update(hand + 100), hand + 100)


if __name__ == '__main__':
    unittest.main()
