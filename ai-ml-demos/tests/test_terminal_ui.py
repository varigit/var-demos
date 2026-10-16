# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import curses
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from terminal_ui import TerminalUI, log_tail, navigate, safe_text, summary_lines


class TerminalTests(unittest.TestCase):
    def make_ui(self, keys, size=(24, 80)):
        screen = Mock()
        screen.getmaxyx.return_value = size
        screen.getch.side_effect = keys
        with patch('terminal_ui.curses.has_colors', return_value=False), \
                patch('terminal_ui.curses.curs_set'):
            ui = TerminalUI(screen, {}, 'imx8mplus', [], Mock())
        return ui

    def test_navigation_wraps(self):
        self.assertEqual(navigate(curses.KEY_UP, 0, 3), 2)
        self.assertEqual(navigate(curses.KEY_DOWN, 2, 3), 0)
        self.assertEqual(navigate(curses.KEY_DOWN, 0, 0), 0)

    @patch('terminal_ui.curses.doupdate')
    @patch('terminal_ui.SOC_TEMPERATURE.read', return_value=70)
    def test_select_and_cancel(self, *_):
        items = [{'title': 'One'}, {'title': 'Two'}]
        ui = self.make_ui([curses.KEY_DOWN, 10])
        self.assertEqual(ui.choose('Demos', items), items[1])
        ui = self.make_ui([27])
        self.assertIsNone(ui.choose('Demos', items))

    @patch('terminal_ui.curses.doupdate')
    def test_small_terminal_can_exit(self, *_):
        ui = self.make_ui([27], (8, 20))
        self.assertIsNone(ui.choose('Demos', [{'title': 'One'}]))

    @patch('terminal_ui.curses.doupdate')
    @patch('terminal_ui.SOC_TEMPERATURE.read', return_value=70)
    @patch('terminal_ui.clock_is_limited', return_value=False)
    @patch('terminal_ui.temperature', return_value=70)
    @patch('terminal_ui.subprocess.Popen')
    def test_escape_releases_process(self, popen, *_):
        ui = self.make_ui([27])
        launcher = {'title': 'Camera'}
        ui.api.prepare_launch.return_value = (launcher, ['demo'], '/tmp')
        process = popen.return_value
        process.poll.return_value = None
        ui.message = Mock()
        ui.run(launcher)
        ui.api.stop_process.assert_called_once_with(process)
        self.assertIn('stopped', ui.notice)
        ui.message.assert_called_once()

    def test_control_characters_are_removed(self):
        self.assertEqual(safe_text('hello\n\x00world'), 'helloworld')

    def test_category_back_returns_to_category_menu(self):
        ui = self.make_ui([])
        group = {'id': 'opencl', 'title': 'OpenCL'}
        ui.catalog = {'groups': [group]}
        ui.launchers = [{'id': 'vector', 'group': 'opencl'}]
        ui.choose = Mock(side_effect=[group, None, None])
        self.assertEqual(ui.main(), 0)
        self.assertEqual(ui.choose.call_count, 3)
        self.assertEqual(ui.choose.call_args_list[1].args[2], 'Back')

    def test_launch_failure_keeps_menu_available(self):
        ui = self.make_ui([])
        launcher = {'id': 'camera', 'title': 'Camera'}
        ui.choose = Mock(side_effect=[launcher, None])
        ui.run = Mock(side_effect=RuntimeError('Camera unavailable'))
        ui.message = Mock()
        self.assertEqual(ui.main(), 0)
        ui.message.assert_called_once_with(
            'Cannot start demo', ['Camera unavailable'])
        self.assertEqual(ui.choose.call_count, 2)

    def test_video_back_returns_to_quality_in_curses(self):
        import manager
        ui = self.make_ui([])
        ui.api = manager
        ui.catalog = manager.load_catalog()
        launcher = next(item for item in ui.catalog['launchers']
                        if item['id'] == 'detection-video')
        ui.launchers = [launcher]
        from demo_menu import demo_entries
        task = demo_entries(ui.launchers)[0]
        mode = task['children'][0]
        qualities = manager.video_resolutions(ui.catalog, launcher['video_demo'])
        video = manager.video_choices(ui.catalog, launcher['video_demo'], '1080p')[1]
        ui.choose = Mock(side_effect=[task, mode, qualities[0], None,
                                      qualities[1], video, None, None])
        ui.run = Mock()
        self.assertEqual(ui.main(), 0)
        ui.run.assert_called_once_with(mode, video)
        self.assertEqual(ui.choose.call_args_list[4].args[0], 'Choose Video Quality')

    @patch('terminal_ui.subprocess.Popen')
    def test_crashed_child_is_reported_without_raising(self, popen):
        ui = self.make_ui([])
        launcher = {'title': 'Camera'}
        ui.api.prepare_launch.return_value = (launcher, ['demo'], '/tmp')
        process = popen.return_value
        process.poll.return_value = -11
        process.returncode = -11
        ui.message = Mock()
        ui.run(launcher)
        self.assertIn('exit -11', ui.notice)
        ui.message.assert_called_once()

    def test_log_tail_is_bounded_and_keeps_latest_lines(self):
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log') as log:
            log.write('old diagnostic\n' * 10000 + 'latest output\n')
            log.flush()
            lines = log_tail(log.name)
        self.assertEqual(len(lines), 8)
        self.assertEqual(lines[-1], 'latest output')

    def test_summary_reads_structured_metrics(self):
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log') as log:
            log.write('driver warning\nVAR_AI_STATS {"frames": 15, '
                      '"inference_ms": 8.5, "processing_fps": 29.5, '
                      '"soc_peak_c": 75}\n')
            log.flush()
            lines = summary_lines(log.name, 1.2)
        self.assertIn('Frames with inference: 15', lines)
        self.assertIn('Average inference: 8.5 ms', lines)

    def test_incomplete_run_does_not_invent_statistics(self):
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log') as log:
            log.write('VAR_AI_STATS truncated\n')
            log.flush()
            lines = summary_lines(log.name, 2)
        self.assertIn('Processing statistics unavailable for this run.', lines)

    @patch('terminal_ui.curses.doupdate')
    @patch('terminal_ui.SOC_TEMPERATURE.read', return_value=70)
    def test_screen_change_forces_refresh_only_once(self, *_):
        ui = self.make_ui([])
        ui.header('Menu')
        ui.footer('Help')
        ui.screen.refresh.assert_called_once()
        ui.header('Menu')
        ui.footer('Help')
        self.assertEqual(ui.screen.refresh.call_count, 1)
        ui.header('Videos')
        ui.footer('Help')
        self.assertEqual(ui.screen.refresh.call_count, 2)

    @patch('terminal_ui.curses.resizeterm')
    @patch('terminal_ui.serial_console', return_value=True)
    def test_serial_uses_small_ascii_screen(self, _, resize):
        ui = self.make_ui([], (61, 201))
        resize.assert_called_once_with(24, 80)
        ui.text(1, 2, 'Chicago \u2014 HD')
        self.assertEqual(ui.screen.addnstr.call_args.args[2], 'Chicago - HD')
        ui.screen.idcok.assert_called_once_with(False)
        ui.screen.idlok.assert_called_once_with(False)


if __name__ == '__main__':
    unittest.main()
