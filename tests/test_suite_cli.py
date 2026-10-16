import importlib.util
from pathlib import Path
import sys
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('suite_cli', ROOT / 'suite.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class SuiteCommandTests(unittest.TestCase):
    def test_suite_preserves_cross_demo_videos_and_camera_choices(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy2(ROOT / 'catalog.toml', root / 'catalog.toml')
            ai = root / 'ai-ml'
            ai.mkdir()
            shutil.copy2(ROOT / 'ai-ml-demos/catalog.toml', ai / 'catalog.toml')
            (ai / 'classification').mkdir()
            with patch.object(suite, 'ROOT', root), \
                    patch.object(suite.manager, 'ROOT', root), \
                    patch.object(suite, 'add_external_demos'):
                catalog = suite.load_suite()
                launcher = next(x for x in catalog['launchers']
                                if x['id'] == 'classification-video')
                self.assertEqual(launcher['video_demo'],
                                 'ai-ml/high-resolution-video-detection')
                video = next(x for x in catalog['videos']
                             if x['demo'] == launcher['video_demo'])
                path = ai / 'high-resolution-video-detection' / video['path']
                path.parent.mkdir(parents=True)
                path.touch()
                _, command, _ = suite.manager.prepare_launch(catalog, launcher, video)
                self.assertEqual(command[-2:], ['--video', str(path)])
                for platform in ('imx8mplus', 'imx93', 'imx95'):
                    self.assertTrue(suite.manager.camera_choices(catalog, platform))

    def catalog(self, groups=None):
        return {'platforms': {'imx8mplus': {'name': 'i.MX 8M Plus'}},
                'groups': groups or [], 'demos': [], 'launchers': []}

    def test_uninstall_replaces_caller_and_forwards_installed_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.var-demos-installed').touch()
            with patch.object(suite, 'ROOT', root), \
                    patch.object(sys, 'argv', ['var-demos', '--uninstall',
                                             '--dry-run']), \
                    patch.object(suite.os, 'execv') as execute:
                self.assertEqual(suite.main(), 0)
                execute.assert_called_once_with(sys.executable, [
                    sys.executable, str(root / 'installer.py'),
                    '--prefix', str(root), '--uninstall', '--dry-run'])

    def test_uninstall_refuses_unrecognized_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(suite, 'ROOT', Path(temporary)), \
                    patch.object(sys, 'argv', ['var-demos', '--uninstall']), \
                    patch.object(suite.os, 'execv') as execute:
                with self.assertRaisesRegex(SystemExit, 'Unrecognized'):
                    suite.main()
                execute.assert_not_called()

    @patch('builtins.print')
    def test_status_aliases_do_not_launch_a_demo(self, *_):
        for option in ('status', '--status'):
            with patch.object(sys, 'argv', ['var-demos', option]), \
                    patch.object(suite, 'show_status', return_value=0) as status, \
                    patch.object(suite.manager, 'main') as manager:
                self.assertEqual(suite.main(), 0)
                status.assert_called_once()
                manager.assert_not_called()

    @patch('builtins.print')
    def test_status_reports_missing_player_assets(self, output):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.var-demos-installed').touch()
            catalog = self.catalog([{'id': 'multimedia', 'title': 'Media'}])
            with patch.object(suite, 'ROOT', root), \
                    patch.object(suite, 'load_suite', return_value=catalog), \
                    patch.object(suite.manager, 'detect_platform',
                                 return_value='imx8mplus'):
                self.assertEqual(suite.show_status(), 1)
                self.assertTrue(any('2 missing' in str(call)
                                    for call in output.call_args_list))

    @patch('builtins.print')
    def test_status_rejects_source_checkout(self, *_):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(suite, 'ROOT', Path(temporary)):
                self.assertEqual(suite.show_status(), 1)

    @patch('builtins.print')
    def test_mx95_status_names_sensors_and_does_not_infer_clock(self, output):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.var-demos-installed').touch()
            catalog = self.catalog()
            catalog['platforms'] = {'imx95': {'name': 'i.MX 95'}}
            with patch.object(suite, 'ROOT', root), \
                    patch.object(suite, 'load_suite', return_value=catalog), \
                    patch.object(suite.manager, 'detect_platform',
                                 return_value='imx95'), \
                    patch.object(suite, 'SoCTemperature') as sensor, \
                    patch.object(suite.manager, 'clock_is_limited') as clock:
                sensor.return_value.read.return_value = 45.0
                self.assertEqual(suite.show_status(), 0)
                clock.assert_not_called()
                text = '\n'.join(str(call) for call in output.call_args_list)
                self.assertIn('a55-thermal', text)
                self.assertIn('ana-thermal', text)
                self.assertIn('limitation indicator: unavailable', text)

    def test_list_still_uses_manager_without_opening_ui(self):
        with patch.object(sys, 'argv', ['var-demos', '--list']), \
                patch.object(suite.manager, 'main', return_value=0) as manager:
            self.assertEqual(suite.main(), 0)
            manager.assert_called_once()

    def test_uninstall_preview_and_removal_on_disposable_installation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'suite'
            root.mkdir()
            (root / '.var-demos-installed').touch()
            (root / 'keep.txt').write_text('unrelated data')
            for name in ('suite.py', 'installer.py', 'install.sh', 'install_ui.py'):
                shutil.copy2(ROOT / name, root / name)
            shutil.copy2(ROOT / 'catalog.toml', root / 'catalog.toml')
            lib = root / 'lib'
            lib.mkdir()
            for name in ('manager.py', 'runtime.py', 'telemetry.py',
                         'terminal_ui.py', 'demo_menu.py'):
                shutil.copy2(ROOT / 'ai-ml-demos' / name, lib / name)
            preview = subprocess.run([
                sys.executable, str(root / 'suite.py'), '--uninstall',
                '--dry-run'], capture_output=True, text=True)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            self.assertTrue((root / 'suite.py').exists())
            result = subprocess.run([
                sys.executable, str(root / 'suite.py'), '--uninstall'],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'suite.py').exists())
            self.assertFalse(lib.exists())
            self.assertFalse((root / 'install_ui.py').exists())
            self.assertNotIn('Removed /', result.stdout)
            self.assertIn('Complete', result.stdout)
            self.assertEqual((root / 'keep.txt').read_text(), 'unrelated data')


if __name__ == '__main__':
    unittest.main()
