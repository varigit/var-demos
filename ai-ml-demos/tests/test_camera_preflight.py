# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime
import manager
from terminal_ui import TerminalUI


class CameraPreflightTests(unittest.TestCase):
    @patch('manager.run_launcher', side_effect=runtime.CameraUnavailable('No camera'))
    @patch('builtins.print')
    def test_direct_manager_command_warns_without_traceback(self, output, _):
        with patch.object(sys, 'argv', ['var-ai', '--platform', 'imx95',
                                       '--run', 'neutron-face-camera']):
            self.assertEqual(manager.main(), 0)
        self.assertIn('Camera unavailable', output.call_args.args[0])

    @patch('runtime.Path.is_char_device', return_value=False)
    @patch('subprocess.run')
    def test_absent_device_does_not_start_capture_or_model(self, run, _):
        with self.assertRaises(runtime.CameraUnavailable):
            runtime.check_camera('imx8mplus')
        run.assert_not_called()

    @patch('runtime.Path.is_char_device', return_value=True)
    @patch('runtime.Path.exists', return_value=False)
    @patch('subprocess.run')
    def test_isi_nodes_without_media_graph_are_not_a_connected_camera(self, run, *_):
        with self.assertRaises(runtime.CameraUnavailable):
            runtime.check_camera('imx95')
        run.assert_not_called()

    @patch('runtime.Path.is_char_device', return_value=True)
    @patch('runtime.Path.exists', return_value=True)
    @patch('subprocess.run', return_value=Mock(returncode=0, stdout='mxc_isi.0'))
    def test_media_graph_without_sensor_is_unavailable(self, *_):
        with self.assertRaises(runtime.CameraUnavailable):
            runtime.check_camera('imx95')

    @patch('runtime.Path.is_char_device', return_value=True)
    @patch('runtime.Path.exists', return_value=True)
    @patch('subprocess.run', return_value=Mock(returncode=0, stdout='ov5640 4-003c'))
    def test_present_mx93_sensor_is_accepted(self, *_):
        self.assertEqual(runtime.check_camera('imx93'), '/dev/video0')

    @patch('manager.detect_platform', return_value='imx95')
    @patch('manager.check_camera', side_effect=runtime.CameraUnavailable('No camera'))
    @patch('manager.subprocess.run')
    def test_cli_launch_checks_before_starting_child(self, run, *_):
        with self.assertRaises(runtime.CameraUnavailable):
            manager.run_launcher({}, dict(select_camera=True), dashboard=False)
        run.assert_not_called()

    @patch('terminal_ui.check_camera', side_effect=runtime.CameraUnavailable('No camera'))
    def test_menu_warns_and_returns_without_resolution_or_launch(self, _):
        ui = object.__new__(TerminalUI)
        ui.catalog = {}
        ui.platform = 'imx95'
        ui.launchers = [dict(id='camera', select_camera=True)]
        ui.choose = Mock(side_effect=[ui.launchers[0], None])
        ui.run = Mock()
        ui.message = Mock()
        self.assertEqual(ui.main(), 0)
        ui.run.assert_not_called()
        ui.message.assert_called_once()
        self.assertEqual(ui.message.call_args.args[0], 'Camera unavailable')
