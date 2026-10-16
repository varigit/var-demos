# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import ast
from pathlib import Path
import unittest


# The pipeline builder is pure; load it without importing target-only TFLite.
SOURCE = Path(__file__).resolve().parents[1] / 'camera-vision/demo.py'
tree = ast.parse(SOURCE.read_text())
builders = [node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ('capture_tail', 'gpu_video_conversion', 'video_decoder',
                             'face_camera_conversion')]
namespace = {}
exec(compile(ast.Module(body=builders, type_ignores=[]), str(SOURCE), 'exec'),
     namespace)


class CapturePipelineTests(unittest.TestCase):
    def test_gesture_capture_keeps_bgr_at_every_resolution(self):
        gesture = SOURCE.parents[1] / 'hand-gesture' / 'demo.py'
        source = gesture.read_text()
        self.assertIn("'videoconvert ! video/x-raw,format=BGR ! '", source)
        self.assertIn('width={capture_width},height={capture_height}', source)
        self.assertIn('ui.camera_resolution(frame, camera_size)', source)

    def test_face_camera_conversion_uses_tested_image_engines(self):
        self.assertIn('imxvideoconvert_g2d ! video/x-raw,format=RGBx,width=800,height=450',
                      namespace['face_camera_conversion']('imx8mplus', (800, 450)))
        self.assertIn('imxvideoconvert_pxp ! video/x-raw,format=BGR,width=800,height=450',
                      namespace['face_camera_conversion']('imx93', (800, 450)))
        self.assertEqual(namespace['face_camera_conversion']('imx95', (800, 450)), '')
    def test_mx95_decoder_uses_owned_linear_buffers(self):
        description = namespace['video_decoder']('imx95')
        self.assertIn('v4l2h264dec capture-io-mode=2', description)
        self.assertIn('video/x-raw,format=NV12', description)
        self.assertNotIn('decodebin', description)

    def test_mx93_keeps_cpu_mjpeg_decoder(self):
        self.assertEqual(namespace['video_decoder']('imx93'), 'avidemux ! jpegdec')

    def test_gpu_download_renders_without_resizing_model_source(self):
        description = namespace['gpu_video_conversion']()
        self.assertIn('glcolorscale ! ', description)
        self.assertIn('video/x-raw(memory:GLMemory),format=RGBA', description)
        self.assertLess(description.index('glcolorscale'),
                        description.index('gldownload'))
        self.assertNotIn('width=', description)
        self.assertNotIn('height=', description)

    def test_live_sink_is_discoverable_by_opencv(self):
        description = namespace['capture_tail'](False)
        self.assertIn('appsink name=opencvsink ', description)
        self.assertIn('format=BGR', description)
        self.assertIn('max-buffers=1', description)

    def test_gpu_scaling_happens_before_download(self):
        description = namespace['gpu_video_conversion']((800, 450))
        self.assertIn('format=RGBA,width=800,height=450', description)
        self.assertLess(description.index('width=800'), description.index('gldownload'))

    def test_file_sink_matches_gi_reader(self):
        description = namespace['capture_tail'](True)
        self.assertIn('appsink name=frames ', description)
        self.assertNotIn('opencvsink', description)
