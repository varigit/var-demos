import io
import os
from pathlib import Path
import sys
import signal
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install_ui import Dashboard
import install_ui
from installer import install_plan
import tomllib


class Terminal(io.StringIO):
    def isatty(self):
        return True


class InstallUITests(unittest.TestCase):
    def test_recent_assets_roll_without_duplicates_and_keep_fixed_height(self):
        ui = Dashboard(Terminal())
        self.assertEqual(len(ui.content()), 14)
        for clip in ('buildings_458687_1280x720', 'buildings_458688_1280x720',
                     'chicago_1280x720', 'video_1920x1080'):
            for stage in ('Verifying', 'Downloading', 'Verified'):
                ui.accept(dict(message=f'{stage} assets/videos/{clip}.mp4'))
                self.assertLessEqual(len(ui.recent_assets), 3)
                self.assertEqual(len(ui.content()), 14)
        rows = ui.content()[-3:]
        self.assertNotIn('Buildings A', '\n'.join(rows))
        self.assertIn('Buildings B', rows[0])
        self.assertIn('Chicago traffic', rows[1])
        self.assertIn('Jijiga street - 1080p', rows[2])
        self.assertTrue(all(row.startswith('OK ') for row in rows))
        ui.accept(dict(message='Installing assets/videos/video_1920x1080.mp4'))
        self.assertEqual(ui.content()[-3:], rows)

    def test_recent_assets_distinguish_downloads_from_cached_verification(self):
        ui = Dashboard(io.StringIO())
        ui.accept(dict(message='Verifying model/mobilenet_vela.tflite'))
        self.assertIn('Verifying', ui.content()[-3])
        ui.accept(dict(message='Downloading model/mobilenet_vela.tflite'))
        self.assertIn('Downloading', ui.content()[-3])
        ui.accept(dict(message='Verified model/mobilenet_vela.tflite',
                       done=True, asset=True))
        self.assertEqual(len(ui.recent_assets), 1)
        self.assertIn('OK MobileNet V1 classification model', ui.content()[-3])
        self.assertEqual(len(Dashboard(io.StringIO(), remove=True).content()), 9)

    def test_video_names_match_across_containers_and_stages(self):
        ui = Dashboard(io.StringIO())
        for stage in ('Verifying', 'Verified', 'Installing', 'Installed'):
            for extension in ('mp4', 'avi'):
                ui.accept(dict(message=f'{stage} assets/videos/buildings_458687_1280x720.{extension}'))
                self.assertEqual(ui.message, f'{stage} Buildings A - 720p')
        self.assertEqual(install_ui.asset_name('media/video_1280x800.mp4'),
                         'Jijiga street - 1280 x 800')
        self.assertEqual(install_ui.asset_name('media/buildings_458688_1920x1080.avi'),
                         'Buildings B - 1080p')

    def test_remote_identity_is_used_for_generic_local_alias(self):
        ui = Dashboard(io.StringIO())
        ui.accept(dict(message='Installing media/video.mp4',
                       asset_path='media/buildings_458687_1280x720.mp4'))
        self.assertEqual(ui.message, 'Installing Buildings A - 720p')
        ui.accept(dict(message='Verifying model/ssd_neutron.tflite'))
        self.assertEqual(ui.message, 'Verifying SSD-Lite V2 detection model')
        ui.accept(dict(message='Installing media/image.jpg',
                       asset_path='media/classification-image.jpg'))
        self.assertEqual(ui.message, 'Installing Classification sample image')

    def test_progress_is_counted_not_invented_and_success_requires_exit(self):
        ui = Dashboard(io.StringIO())
        ui.accept(dict(message='Plan', total=4, asset_total=2, demos=3))
        self.assertIn('  0%', ui.content()[5])
        ui.accept(dict(message='Verified', done=True, asset=True))
        self.assertIn(' 25%', ui.content()[5])
        self.assertEqual(ui.assets, 1)
        for _ in range(3):
            ui.accept(dict(message='Done', done=True))
        self.assertIn(' 99%', ui.content()[5])
        self.assertIn('100%', ui.content('Complete')[5])
        self.assertNotIn('100%', ui.content('Failed')[5])

    def test_pipe_output_has_no_terminal_sequences_or_repeated_ticks(self):
        stream = io.StringIO()
        with Dashboard(stream) as ui:
            ui.render()
            ui.render()
            ui.accept(dict(message='Checking assets'))
            ui.render()
        self.assertNotIn('\033', stream.getvalue())
        self.assertEqual(stream.getvalue().count('Preparing installation'), 1)

    def test_tty_redraw_and_cursor_restoration_on_exception(self):
        stream = Terminal()
        with patch.dict(os.environ, {'TERM': 'vt102'}):
            with self.assertRaises(RuntimeError):
                with Dashboard(stream) as ui:
                    ui.accept(dict(message='Bad\033[2Jmessage'))
                    ui.render()
                    raise RuntimeError('test failure')
        text = stream.getvalue()
        self.assertIn('\033[14A', text)
        self.assertIn('\033[?25l', text)
        self.assertTrue(text.endswith('\033[0m\033[?25h'))
        self.assertNotIn('Bad\033[2J', text)

    def test_dumb_terminal_and_no_color(self):
        with patch.dict(os.environ, {'TERM': 'dumb'}):
            ui = Dashboard(Terminal())
            self.assertFalse(ui.tty)
        with patch.dict(os.environ, {'TERM': 'vt102', 'NO_COLOR': '1'}):
            ui = Dashboard(Terminal())
            self.assertTrue(ui.tty)
            self.assertFalse(ui.color)

    def test_uninstall_has_no_launch_hint_or_sha_download_status(self):
        ui = Dashboard(io.StringIO(), remove=True)
        text = '\n'.join(ui.content('Complete'))
        self.assertIn('UNINSTALL', text)
        self.assertNotIn('SHA-256', text)
        self.assertNotIn('Run:', text)

    def test_every_board_has_exact_manifest_work_plan(self):
        with (ROOT / 'catalog.toml').open('rb') as file:
            catalog = tomllib.load(file)
        with (ROOT / 'ai-ml-demos/catalog.toml').open('rb') as file:
            ai = tomllib.load(file)
        for board in ('imx8mplus', 'imx93', 'imx95'):
            groups = [g for g in catalog['groups'] if board in g['platforms']]
            demos = [d for d in ai['demos'] if board in d['platforms']]
            entries = sum(sum(bool(line.strip()) and not line.startswith('#')
                              for line in (ROOT / 'ai-ml-demos' / d['path'] /
                                           d['manifest']).read_text().splitlines())
                          for d in demos)
            plan = install_plan(ROOT, board, groups)
            self.assertEqual(plan['asset_total'], entries + 2)
            self.assertEqual(plan['total'], len(groups) + entries * 2 +
                             len(demos) + 2 + len(groups) - 1 + 1)
            self.assertEqual(plan['demos'], 18 if board == 'imx8mplus' else
                             16 if board == 'imx93' else 17)

    def test_cancel_stops_owned_worker_and_restores_cursor(self):
        with tempfile.TemporaryDirectory() as directory:
            descriptor, logfile = tempfile.mkstemp(dir=directory)
            process = MagicMock()
            process.pid = 12345
            process.poll.return_value = None
            stream = Terminal()
            previous = signal.getsignal(signal.SIGTERM)
            with patch.dict(os.environ, {'TERM': 'vt102'}), \
                    patch.object(install_ui.tempfile, 'mkstemp',
                                 return_value=(descriptor, logfile)), \
                    patch.object(install_ui.subprocess, 'Popen',
                                 return_value=process), \
                    patch.object(install_ui.selectors, 'DefaultSelector') as sel, \
                    patch.object(install_ui.os, 'killpg') as kill, \
                    redirect_stdout(stream):
                sel.return_value.__enter__.return_value.select.side_effect = (
                    KeyboardInterrupt)
                self.assertEqual(install_ui.run_dashboard([]), 130)
                kill.assert_called_once_with(12345, signal.SIGTERM)
                self.assertTrue(Path(logfile).exists())
            self.assertEqual(signal.getsignal(signal.SIGTERM), previous)
            self.assertIn('Cancelled', stream.getvalue())
            self.assertNotIn('100%', stream.getvalue())
            self.assertTrue(stream.getvalue().endswith('\033[0m\033[?25h'))

    def test_failed_preflight_keeps_log_and_never_reports_success(self):
        with tempfile.TemporaryDirectory() as directory:
            descriptor, logfile = tempfile.mkstemp(dir=directory)
            stream = io.StringIO()
            with patch.object(install_ui.tempfile, 'mkstemp',
                              return_value=(descriptor, logfile)), \
                    redirect_stdout(stream):
                result = install_ui.run_dashboard([
                    '--board', 'unsupported', '--prefix', directory + '/suite'])
            self.assertNotEqual(result, 0)
            self.assertIn('Failed', stream.getvalue())
            self.assertNotIn('100%', stream.getvalue())
            self.assertIn('not been validated', Path(logfile).read_text())
            self.assertFalse((Path(directory) / 'suite').exists())


if __name__ == '__main__':
    unittest.main()
