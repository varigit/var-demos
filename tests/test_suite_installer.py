import importlib.util
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'installer.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def test_installed_bin_dir_keeps_legacy_default_and_custom_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / '.var-demos-installed'
            marker.touch()
            self.assertEqual(installer.installed_bin_dir(root), Path('/usr/bin'))
            marker.write_text('{"bin_dir":"/opt/fixture/bin"}')
            self.assertEqual(installer.installed_bin_dir(root), Path('/opt/fixture/bin'))
            marker.write_text('{"bin_dir":"relative"}')
            with self.assertRaises(RuntimeError):
                installer.installed_bin_dir(root)
    def test_brand_asset_requires_its_expected_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            asset = Path(temporary) / 'logo.png'
            asset.write_bytes(b'logo fixture')
            digest = hashlib.sha256(b'logo fixture').hexdigest()
            self.assertTrue(installer.verified(asset, digest))
            self.assertFalse(installer.verified(asset, '0' * 64))

    def run_installer(self, *arguments):
        return subprocess.run([sys.executable, str(ROOT / 'installer.py'),
                               *arguments], capture_output=True, text=True)

    def test_catalog_excludes_legacy_modules(self):
        with (ROOT / 'catalog.toml').open('rb') as source:
            catalog = tomllib.load(source)
        self.assertEqual({entry['source'] for entry in catalog['groups']},
                         {'ai-ml-demos', 'multimedia-demos', 'opencl/python'})

    def test_dry_run_does_not_create_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix = Path(temporary) / 'demos'
            result = self.run_installer('--board', 'imx8mplus', '--dry-run',
                                        '--prefix', str(prefix))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(prefix.exists())
            self.assertNotIn('TPM', result.stdout)

    def test_only_selects_one_group(self):
        result = self.run_installer('--board', 'imx8mplus', '--only', 'opencl',
                                    '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('OpenCL', result.stdout)
        self.assertNotIn('AI / ML', result.stdout)

    def test_unvalidated_board_is_rejected(self):
        result = self.run_installer('--board', 'unvalidated', '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not been validated', result.stderr)

    def test_mx95_selects_ai_opencl_and_validated_player(self):
        result = self.run_installer('--board', 'imx95', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('AI / ML', result.stdout)
        self.assertIn('OpenCL', result.stdout)
        self.assertIn('Multimedia', result.stdout)

    def test_mx93_selects_ai_and_pxp_player_but_no_opencl(self):
        result = self.run_installer('--board', 'imx93', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('AI / ML', result.stdout)
        self.assertIn('Multimedia', result.stdout)
        self.assertNotIn('OpenCL', result.stdout)

    def test_mx93_sample_uses_jpeg_not_missing_h264_decoder(self):
        url, digest, name = installer.sample_asset('imx93')
        self.assertTrue(url.endswith('.avi'))
        self.assertEqual(len(digest), 64)
        self.assertEqual(name, 'buildings.avi')

    def test_broad_paths_are_rejected(self):
        for value in ('/', '/opt', '/usr/bin', '/home', 'relative'):
            with self.assertRaises(RuntimeError):
                installer.valid_root(value)

    def test_symlink_prefix_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'link'
            link.symlink_to(ROOT, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                installer.valid_root(str(link))

    def test_launcher_collision_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            launcher = directory / 'var-demos'
            launcher.write_text('user file')
            with self.assertRaises(RuntimeError):
                installer.link_command(directory, 'var-demos', ROOT / 'suite.py')
            self.assertEqual(launcher.read_text(), 'user file')

    def test_update_removes_only_owned_legacy_shortcuts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'suite'
            bin_dir = Path(temporary) / 'bin'
            bin_dir.mkdir()
            for name, relative in [('var-ai', 'ai-ml/manager.py'),
                                   ('var-media', 'multimedia/video-player/player.py')]:
                (bin_dir / name).symlink_to(root / relative)
            installer.remove_legacy_commands(bin_dir, root)
            self.assertFalse((bin_dir / 'var-ai').is_symlink())
            self.assertFalse((bin_dir / 'var-media').is_symlink())

    def test_update_preserves_unrelated_legacy_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'var-ai').write_text('user command')
            (directory / 'var-media').symlink_to('/unrelated/player')
            installer.remove_legacy_commands(directory, directory / 'suite')
            self.assertEqual((directory / 'var-ai').read_text(), 'user command')
            self.assertEqual((directory / 'var-media').readlink(),
                             Path('/unrelated/player'))

    def test_uninstall_rejects_unrecognized_installation_before_removal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'suite'
            root.mkdir()
            (root / 'catalog.toml').write_bytes((ROOT / 'catalog.toml').read_bytes())
            module = root / 'multimedia'
            module.mkdir()
            (module / installer.OWNED).touch()
            result = self.run_installer('--uninstall', '--prefix', str(root))
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(module.is_dir())

    def test_uninstall_preserves_unrelated_root_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'suite'
            root.mkdir()
            (root / 'catalog.toml').write_bytes((ROOT / 'catalog.toml').read_bytes())
            (root / '.var-demos-installed').touch()
            (root / 'lib').mkdir()
            (root / 'keep.txt').write_text('user data')
            for name in ('multimedia', 'opencl'):
                module = root / name
                module.mkdir()
                (module / installer.OWNED).touch()
            result = self.run_installer('--uninstall', '--prefix', str(root),
                                       '--bin-dir', str(Path(temporary) / 'bin'))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'keep.txt').read_text(), 'user data')
            self.assertFalse((root / 'multimedia').exists())


if __name__ == '__main__':
    unittest.main()
