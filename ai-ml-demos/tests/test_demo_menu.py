# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manager
from demo_menu import demo_entries, clean_title, NPU_NAMES
from terminal_ui import TerminalUI


class DemoMenuTests(unittest.TestCase):
    def test_same_tasks_and_modes_on_all_platforms(self):
        catalog = manager.load_catalog()
        for platform in NPU_NAMES:
            with self.subTest(platform=platform):
                launchers = manager.launchers_for(catalog, platform)
                entries = demo_entries(launchers)
                self.assertEqual([item['title'] for item in entries[:5]],
                    ['Classification', 'Object Detection', 'Face Detection',
                     'People and Vehicle Segmentation', 'People Segmentation'])
                for task in entries[:5]:
                    self.assertEqual([mode['menu_title'] for mode in task['children']],
                                     ['Image', 'Video', 'Camera'])
                    for mode in task['children']:
                        original = next(item for item in launchers if item['id'] == mode['id'])
                        self.assertEqual(mode['command'], original['command'])
                        self.assertEqual(mode.get('select_camera'), original.get('select_camera'))
                        self.assertEqual(mode.get('select_video'), original.get('select_video'))
                self.assertFalse(any('menu_title' in item and item['menu_title'] in ('Image', 'Video', 'Camera')
                                     for item in launchers if 'segmentation' in item['id']))

    def test_strip_only_npu_suffix_without_changing_catalog(self):
        for npu in NPU_NAMES.values():
            self.assertEqual(clean_title(f'Detect faces with {npu}'), 'Detect faces')
        self.assertEqual(clean_title('Video player'), 'Video player')

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['1', '1', '', 'q', 'q'])
    @patch('manager.run_launcher', return_value=0)
    def test_plain_mode_returns_to_task_then_demo_menu(self, run, *_):
        launcher = dict(id='classification-image', title='Classify an image with VIP8000')
        self.assertEqual(manager.interactive({}, 'imx8mplus', [launcher]), 0)
        self.assertEqual(run.call_args.args[1]['id'], launcher['id'])

    def test_curses_back_unwinds_input_task_and_suite(self):
        group = dict(id='ai-ml', title='AI / ML')
        launchers = [dict(id='classification-image', title='Image', group='ai-ml')]
        task = demo_entries(launchers)[0]
        ui = object.__new__(TerminalUI)
        ui.catalog, ui.platform, ui.launchers = {'groups': [group]}, 'imx93', launchers
        ui.choose = Mock(side_effect=[group, task, None, None, None])
        self.assertEqual(ui.main(), 0)
        self.assertEqual([call.args[0] for call in ui.choose.call_args_list],
            ['Choose a category', 'Choose a demo', 'Classification: Choose Input',
             'Choose a demo', 'Choose a category'])

    @patch('terminal_ui.SOC_TEMPERATURE.read', return_value=65)
    def test_header_names_npu_without_overlap_in_narrow_terminal(self, _):
        for width in (45, 80):
            for platform, npu in NPU_NAMES.items():
                ui = object.__new__(TerminalUI)
                ui.platform, ui.catalog, ui.view = platform, {}, None
                ui.screen = Mock()
                ui.screen.getmaxyx.return_value = (24, width)
                ui.accent = 0
                ui.text = Mock()
                ui.header('Choose a demo')
                labels = [call.args[2] for call in ui.text.call_args_list]
                self.assertTrue(any(npu in label for label in labels))
                right = next(call for call in ui.text.call_args_list if 'SoC' in call.args[2])
                self.assertGreater(right.args[1], 2 + len('VARISCITE  /  AI + ML'))
