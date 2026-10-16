# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import ast
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'multimedia-demos/video-player/player.py'
node = next(node for node in ast.parse(SOURCE.read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == 'processor_name')
namespace = dict(Path=Path)
exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)


class PlayerBrandingTests(unittest.TestCase):
    def test_each_supported_processor_is_named(self):
        for identifier, expected in ((b'fsl,imx8mp', 'i.MX 8M Plus'),
                                     (b'fsl,imx93', 'i.MX 93'), (b'fsl,imx95', 'i.MX 95')):
            with patch.object(Path, 'read_bytes', return_value=identifier + b'\0'):
                self.assertEqual(namespace['processor_name'](), expected)

    def test_no_device_tree_has_a_readable_fallback(self):
        with patch.object(Path, 'read_bytes', side_effect=OSError):
            self.assertEqual(namespace['processor_name'](), 'i.MX SoM')
