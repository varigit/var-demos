# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retired_assets import retire


class RetiredAssetTests(unittest.TestCase):
    def setup_files(self, directory, content=b'old sample'):
        root = Path(directory) / 'ai'
        root.mkdir()
        (root / '.var-ai-installed').touch()
        sample = root / 'demo/assets/old.mp4'
        sample.parent.mkdir(parents=True)
        sample.write_bytes(content)
        manifest = Path(directory) / 'retired.manifest'
        manifest.write_text(hashlib.sha256(b'old sample').hexdigest() +
                            ' demo/assets/old.mp4\n')
        return root, sample, manifest

    @patch('builtins.print')
    def test_only_matching_sample_is_removed_and_repeat_is_safe(self, _):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, manifest = self.setup_files(directory)
            other = sample.with_name('user.mp4')
            other.write_bytes(b'personal video')
            self.assertEqual(retire(root, manifest), [Path('demo/assets/old.mp4')])
            self.assertFalse(sample.exists())
            self.assertEqual(other.read_bytes(), b'personal video')
            self.assertEqual(retire(root, manifest), [])

    @patch('builtins.print')
    def test_changed_sample_is_preserved(self, _):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, manifest = self.setup_files(directory, b'user replacement')
            self.assertEqual(retire(root, manifest), [])
            self.assertEqual(sample.read_bytes(), b'user replacement')

    def test_symlink_target_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, manifest = self.setup_files(directory)
            outside = Path(directory) / 'outside.mp4'
            sample.rename(outside)
            sample.symlink_to(outside)
            self.assertEqual(retire(root, manifest), [])
            self.assertTrue(sample.is_symlink())
            self.assertEqual(outside.read_bytes(), b'old sample')

    def test_unrecognized_root_and_escaping_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, manifest = self.setup_files(directory)
            manifest.write_text('a' * 64 + ' ../outside.mp4\n')
            with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
                retire(root, manifest)
            (root / '.var-ai-installed').unlink()
            with self.assertRaisesRegex(RuntimeError, 'unrecognized'):
                retire(root, manifest)
            self.assertTrue(sample.exists())
