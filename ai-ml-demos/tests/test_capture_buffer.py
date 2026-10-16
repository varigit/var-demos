import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import numpy as np


class CaptureBufferTests(unittest.TestCase):
    def capture(self, pixels, stride=8, offset=4):
        source = Path(__file__).resolve().parents[1] / 'camera-vision/capture.py'
        tree = ast.parse(source.read_text())
        info = SimpleNamespace(width=2, height=2, stride=[6], offset=[0],
                               finfo=SimpleNamespace(name='BGR'))
        video = SimpleNamespace(
            VideoInfo=SimpleNamespace(new_from_caps=lambda _: info),
            buffer_get_video_meta=lambda _: SimpleNamespace(stride=[stride], offset=[offset]))
        namespace = dict(np=np, GstVideo=video, Gst=SimpleNamespace(SECOND=1))
        nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        capture = namespace['VideoCapture'].__new__(namespace['VideoCapture'])
        buffer = SimpleNamespace(pts=10, get_size=lambda: len(pixels),
                                 extract_dup=lambda *_: pixels)
        sample = SimpleNamespace(get_caps=lambda: None, get_buffer=lambda: buffer)
        capture.sink = SimpleNamespace(emit=lambda *_: sample)
        return capture

    def test_stride_offset_and_bottom_padding_are_respected(self):
        pixels = bytes(range(32))
        ok, frame = self.capture(pixels).read()
        self.assertTrue(ok)
        np.testing.assert_array_equal(frame.reshape(2, 6),
                                      [list(range(4, 10)), list(range(12, 18))])
        self.assertTrue(frame.flags['C_CONTIGUOUS'])
        frame[:] = 0
        self.assertEqual(pixels, bytes(range(32)))

    def test_invalid_layout_is_rejected(self):
        for pixels, stride in ((bytes(10), 8), (bytes(32), 4)):
            with self.assertRaisesRegex(RuntimeError, 'image layout'):
                self.capture(pixels, stride=stride).read()


if __name__ == '__main__':
    unittest.main()
