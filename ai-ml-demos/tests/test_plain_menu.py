from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manager


class PlainMenuTests(unittest.TestCase):
    def catalog(self):
        return {'groups': [{'id': 'opencl', 'title': 'OpenCL'}]}

    def launchers(self):
        return [{'id': 'vector', 'title': 'Vector addition', 'group': 'opencl'}]

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['1', 'q', 'q'])
    def test_category_then_back_then_quit(self, *_):
        self.assertEqual(manager.interactive(
            self.catalog(), 'imx8mplus', self.launchers()), 0)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['invalid', '0', '2', 'q'])
    def test_invalid_category_does_not_crash(self, *_):
        self.assertEqual(manager.interactive(
            self.catalog(), 'imx8mplus', self.launchers()), 0)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['1', '1', '', 'q', 'q'])
    @patch('manager.run_launcher', side_effect=OSError('Executable missing'))
    def test_failed_launch_keeps_menu_available(self, run, *_):
        self.assertEqual(manager.interactive(
            self.catalog(), 'imx8mplus', self.launchers()), 0)
        run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
