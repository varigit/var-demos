# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import manager


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'camera-vision' / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


face = module('face')
compiler = module('prepare_face')


class FaceTests(unittest.TestCase):
    def test_recorded_quantization_preserves_rgb_pixels(self):
        rgb = np.array([[[0, 127, 255], [1, 128, 254]]], np.uint8)
        actual = face.prepare_face_input(rgb,
            dict(dtype=np.uint8, quantization=(1 / 128, 127)))
        np.testing.assert_array_equal(actual, rgb[None])

    def test_quantization_rounds_and_clips_without_uint8_wrap(self):
        rgb = np.array([[[0, 127, 255]]], np.uint8)
        actual = face.prepare_face_input(rgb,
            dict(dtype=np.uint8, quantization=(1 / 256, 128)))
        np.testing.assert_array_equal(actual, [[[[0, 128, 255]]]])
        with self.assertRaises(ValueError):
            face.prepare_face_input(rgb, dict(dtype=np.uint8, quantization=(0, 0)))

    def test_boxes_are_converted_from_xy_to_yx(self):
        faces = face.decode_faces(np.array([[.1, .9, .2, .3, .7, .8],
                                            [.9, .1, .1, .1, .5, .5]]))
        self.assertEqual(len(faces), 1)
        np.testing.assert_allclose(faces[0][0], [.3, .2, .8, .7])
        self.assertEqual(faces[0][1:], (0, .9))

    def test_empty_and_invalid_outputs(self):
        self.assertEqual(face.decode_faces(np.zeros((100, 6))), [])
        for value in (np.zeros((1, 4)), np.full((100, 6), np.nan)):
            with self.assertRaises(ValueError):
                face.decode_faces(value)
        self.assertEqual(face.decode_faces(np.array([[0, .9, .8, .1, .2, .4]])), [])
        with self.assertRaises(ValueError):
            face.decode_faces(np.zeros((100, 6)), float('nan'))

    def test_three_sources_follow_shared_demos_on_all_soms(self):
        catalog = manager.load_catalog()
        for platform in catalog['platforms']:
            launchers = manager.launchers_for(catalog, platform)
            names = [x['id'].removeprefix('ethosu-').removeprefix('neutron-')
                     for x in launchers[6:9]]
            self.assertEqual(names, ['face-image', 'face-video', 'face-camera'])
            for item in launchers[6:9]:
                self.assertIn('face', item['command'])
                self.assertNotIn('--windowed', item['command'])
            video = launchers[7]
            demo = manager.launcher_video_demo(video, platform)
            self.assertEqual([x['id'] for x in manager.video_resolutions(catalog, demo, 'face')],
                             ['720p', '1080p'])
            for quality in ('720p', '1080p'):
                clips = manager.video_choices(catalog, demo, quality, 'face')
                self.assertEqual(len(clips), 1)
                self.assertIn('1117992', clips[0]['path'])
            self.assertTrue(launchers[8]['select_camera'])

    def test_compilation_is_reused_only_with_verified_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'ultraface.tflite').write_bytes(b'source')
            (root / 'ultraface_vela.tflite').write_bytes(b'compiled')
            with patch.object(compiler, 'digest', side_effect=[
                    compiler.SOURCE_SHA256, compiler.COMPILED_SHA256]), \
                    patch.object(compiler.subprocess, 'run') as run:
                compiler.prepare(root)
                run.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, 'source checksum'):
                compiler.prepare(root)

    def test_wrong_compiler_is_rejected_before_overwriting_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(compiler, 'digest', return_value=compiler.SOURCE_SHA256), \
                    patch.object(compiler.subprocess, 'check_output', return_value='4.0'), \
                    patch.object(compiler.subprocess, 'run') as run:
                with self.assertRaisesRegex(RuntimeError, 'Expected BSP Vela'):
                    compiler.prepare(directory)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
