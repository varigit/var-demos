import importlib.util
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location('manager', ROOT / 'manager.py')
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class VideoMenuTests(unittest.TestCase):
    def setUp(self):
        self.catalog = manager.load_catalog()
        self.launcher = next(
            item for item in self.catalog['launchers']
            if item['id'] == 'detection-video'
        )

    def test_invalid_choices_do_not_select_a_video(self):
        with patch('builtins.input', side_effect=['0', '-1', 'oops', '1', '1']):
            with patch('builtins.print'):
                video = manager.select_video(
                    self.catalog, self.launcher['video_demo']
                )
        self.assertIn('Buildings A', video['title'])

    def test_back_does_not_launch_a_video(self):
        with patch('builtins.input', return_value='b'):
            with patch('builtins.print'):
                self.assertIsNone(manager.select_video(
                    self.catalog, self.launcher['video_demo']
                ))

    def test_clip_back_returns_to_quality_and_full_hd_choice_is_correct(self):
        with patch('builtins.input', side_effect=['1', 'b', '2', '2']), \
                patch('builtins.print'):
            video = manager.select_video(self.catalog, self.launcher['video_demo'])
        self.assertEqual(video['resolution'], '1080p')
        self.assertIn('458688_1920x1080', video['path'])
        self.assertEqual(video['title'], 'Buildings B - 32 seconds (Freepik)')
        self.assertIn('Full HD', video['run_title'])

    def test_only_two_clips_per_quality_on_all_three_boards(self):
        for demo in ('high-resolution-video-detection', 'vision-imx93', 'vision-imx95'):
            qualities = manager.video_resolutions(self.catalog, demo)
            self.assertEqual([item['id'] for item in qualities], ['720p', '1080p'])
            for quality in qualities:
                videos = manager.video_choices(self.catalog, demo, quality['id'])
                self.assertEqual(len(videos), 2)
                self.assertTrue(all('Freepik' in item['title'] for item in videos))
                self.assertIn('458687', videos[0]['path'])
                self.assertIn('458688', videos[1]['path'])

    def test_player_uses_positional_movie_argument(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'multimedia').mkdir()
            movie = root / 'camera/assets/buildings.mp4'
            movie.parent.mkdir(parents=True)
            movie.touch()
            catalog = {'demos': [dict(id='multimedia', path='multimedia'),
                                 dict(id='vision', path='camera')]}
            launcher = dict(demo='multimedia', title='Player',
                            command=['python3', 'player.py'], video_argument='positional')
            video = dict(demo='vision', path='assets/buildings.mp4',
                         title='Buildings A')
            with patch.object(manager, 'ROOT', root):
                _, command, _ = manager.prepare_launch(catalog, launcher, video)
            self.assertEqual(command, ['python3', 'player.py', str(movie)])

    def test_player_selects_the_right_video_catalog_for_each_som(self):
        import tomllib
        with (ROOT.parent / 'catalog.toml').open('rb') as file:
            suite = tomllib.load(file)
        player = next(item for item in suite['launchers'] if item['id'] == 'video-player')
        self.assertTrue(player['select_video'])
        for board, demo in [('imx8mplus', 'high-resolution-video-detection'),
                            ('imx93', 'vision-imx93'), ('imx95', 'vision-imx95')]:
            self.assertEqual(manager.launcher_video_demo(player, board), 'ai-ml/' + demo)

    def test_both_buildings_clips_have_hd_and_full_hd_on_each_board(self):
        manifests = {
            'high-resolution-video-detection':
                'high-resolution-video-detection/assets.manifest',
            'vision-imx93': 'camera-vision/assets-imx93.manifest',
            'vision-imx95': 'camera-vision/assets-imx95.manifest',
        }
        for demo, manifest in manifests.items():
            assets = {line.split()[2] for line in
                      (ROOT / manifest).read_text().splitlines()
                      if line and not line.startswith('#')}
            videos = [item for item in self.catalog['videos']
                      if item['demo'] == demo and not item.get('task')]
            self.assertIn('1280x720', videos[0]['path'])
            for clip in ('458687', '458688'):
                for resolution in ('1280x720', '1920x1080'):
                    matches = [item for item in videos
                               if clip in item['path']
                               and resolution in item['path']]
                    self.assertEqual(len(matches), 1)
                    self.assertIn(matches[0]['path'], assets)

    def test_selected_video_controls_input_and_resolution(self):
        video = [item for item in self.catalog['videos']
                 if item['demo'] == self.launcher['video_demo']][-1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / self.launcher['demo']).mkdir()
            path = root / self.launcher['video_demo'] / video['path']
            path.parent.mkdir(parents=True)
            path.touch()
            with patch.object(manager, 'ROOT', root):
                with patch.object(manager.subprocess, 'run') as run:
                    manager.run_launcher(
                        self.catalog, self.launcher,
                        dashboard=False, video=video,
                    )
            command = run.call_args.args[0]
            self.assertEqual(command[-2:], ['--video', str(path)])
            self.assertEqual(video['resolution'], '1080p')


if __name__ == '__main__':
    unittest.main()
