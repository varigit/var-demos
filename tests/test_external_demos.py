import importlib.util
from pathlib import Path
import unittest
import tomllib
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('suite', ROOT / 'suite.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class ExternalDemoTests(unittest.TestCase):
    def test_curated_catalog_has_nine_unique_graphical_demos(self):
        with (ROOT / 'catalog.toml').open('rb') as source:
            entries = tomllib.load(source)['external_demos']
        expected = {'fractal', 'render-texture', 'opencl-filter',
                    'particles', 'bloom', 'skybox', 'model-viewer',
                    'verlet', 'spring-background'}
        self.assertEqual({entry['id'] for entry in entries}, expected)
        self.assertEqual(len(entries), len(expected))
        self.assertEqual(len({entry['executable'] for entry in entries}),
                         len(entries))
        for entry in entries:
            expected_platforms = ['imx8mplus'] if entry['id'] == 'render-texture' \
                else ['imx8mplus', 'imx95']
            self.assertEqual(entry['platforms'], expected_platforms)
            self.assertTrue(entry['executable'].startswith(
                '/opt/imx-gpu-sdk/GLES3/'))
            self.assertTrue(entry['executable'].endswith('___Wayland'))

    def catalog(self, executable='/opt/imx-gpu-sdk/demo/demo'):
        return {'groups': [], 'demos': [], 'launchers': [],
                'external_demos': [{
                    'id': 'test', 'title': 'GPU demo',
                    'description': 'Installed with the BSP',
                    'platforms': ['imx8mplus'], 'executable': executable,
                }]}

    @patch('suite.os.access', return_value=True)
    @patch.object(Path, 'is_file', return_value=True)
    def test_existing_demo_runs_in_original_directory(self, *_):
        catalog = self.catalog()
        suite.add_external_demos(catalog)
        self.assertEqual(catalog['groups'][0]['id'], 'bsp')
        launcher = catalog['launchers'][0]
        self.assertEqual(launcher['command'], ['/opt/imx-gpu-sdk/demo/demo'])
        self.assertTrue(launcher['native_wayland'])
        with patch.object(Path, 'is_dir', return_value=True):
            _, command, directory = suite.manager.prepare_launch(
                catalog, launcher)
        self.assertEqual(directory, Path('/opt/imx-gpu-sdk/demo'))
        self.assertEqual(command, launcher['command'])
        self.assertEqual(suite.manager.launchers_for(catalog, 'imx93'), [])

    @patch.object(Path, 'is_file', return_value=False)
    def test_missing_demo_does_not_create_empty_category(self, *_):
        catalog = self.catalog()
        suite.add_external_demos(catalog)
        self.assertEqual(catalog['groups'], [])
        self.assertEqual(catalog['launchers'], [])

    @patch('suite.os.access', return_value=False)
    @patch.object(Path, 'is_file', return_value=True)
    def test_nonexecutable_demo_is_hidden(self, *_):
        catalog = self.catalog()
        suite.add_external_demos(catalog)
        self.assertEqual(catalog['launchers'], [])

    @patch('suite.os.access', return_value=True)
    @patch.object(Path, 'is_file', return_value=True)
    def test_arbitrary_scripts_and_parent_traversal_are_rejected(self, *_):
        for executable in ('/opt/ltp/test', '/usr/bin/sh', 'relative',
                           '/opt/imx-gpu-sdk/../other/script'):
            catalog = self.catalog(executable)
            suite.add_external_demos(catalog)
            self.assertEqual(catalog['launchers'], [])


if __name__ == '__main__':
    unittest.main()
