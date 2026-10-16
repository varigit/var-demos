import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manager
import vision_overlay as ui


class SharedPresentationTests(unittest.TestCase):
    def test_metric_labels_share_the_right_edge(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui.cv2, 'putText') as draw:
            ui.statistics(frame, 123.4, 100.0)
            ui.video_resolution(frame, (1920, 1080))
        for call in draw.call_args_list:
            text, (x, _) = call.args[1:3]
            if text in ('INFERENCE', 'FPS', 'VIDEO'):
                width = ui.cv2.getTextSize(text, ui.FONT, .55, 1)[0][0]
                self.assertEqual(x + width, 800 - ui.MARGIN - 12)

    def test_temperature_draws_degree_glyph(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        for temperature in (None, 57.9, 85.0):
            with patch.object(ui, 'panel'), patch.object(ui.cv2, 'circle') as circle, \
                    patch.object(ui.cv2, 'putText') as draw:
                ui.temperature(frame, temperature)
            self.assertEqual(circle.call_count, 1)
            self.assertEqual(draw.call_args.args[1], 'C')

    def test_legend_marker_and_text_share_vertical_center(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui, 'panel'), patch.object(ui.cv2, 'rectangle') as marker, \
                patch.object(ui.cv2, 'putText') as draw:
            ui.legend(frame, [('People', 'person')])
        top, bottom = marker.call_args.args[1:3]
        center = (top[1] + bottom[1]) / 2
        (_, height), baseline = ui.cv2.getTextSize('People', ui.FONT, .6, 1)
        text_center = draw.call_args.args[2][1] + (baseline - height) / 2
        self.assertLessEqual(abs(center - text_center), 1)

    def test_panel_background_is_cached_without_mutating_the_color(self):
        bg = ui.panel_background((10, 20, 3), False)
        self.assertIs(bg, ui.panel_background((10, 20, 3), False))
        self.assertFalse(bg.flags.writeable)
        frame = np.full((30, 40, 3), 180, np.uint8)
        ui.panel(frame, 0, 0, 20, 10)
        np.testing.assert_array_equal(bg[0, 0], ui.PANEL)
        np.testing.assert_array_equal(ui.panel_background((10, 20, 3), True)[0, 0],
                                      ui.PANEL[::-1])

    def test_shared_demos_first_in_identical_order(self):
        catalog = manager.load_catalog()
        expected = ['classification-image', 'classification-video',
                    'classification-camera', 'detection-image',
                    'detection-video', 'detection-camera']
        for board in catalog['platforms']:
            launchers = manager.launchers_for(catalog, board)
            ids = [x['id'].removeprefix('ethosu-').removeprefix('neutron-')
                   for x in launchers[:6]]
            self.assertEqual(ids, expected, board)
            self.assertTrue(all('--windowed' not in x['command']
                                for x in launchers))

    def test_video_menus_identical_and_assets_present_in_manifests(self):
        catalog = manager.load_catalog()
        titles = []
        root = Path(__file__).resolve().parents[1]
        for demo_id in ['high-resolution-video-detection', 'vision-imx93', 'vision-imx95']:
            videos = [x for x in catalog['videos']
                      if x['demo'] == demo_id and not x.get('task')]
            self.assertEqual(len(videos), 4)
            titles.append([x['title'] for x in videos])
            demo = manager.find_demo(catalog, demo_id)
            assets = (root / demo['path'] / demo['manifest']).read_text()
            self.assertTrue(all(x['path'] in assets for x in videos))
        self.assertEqual(titles[0], titles[1])
        self.assertEqual(titles[1], titles[2])

    def test_camera_resolution_does_not_mutate_catalog_command(self):
        catalog = manager.load_catalog()
        for board in catalog['platforms']:
            for item in manager.launchers_for(catalog, board):
                if not item.get('select_camera'):
                    continue
                selected = manager.with_camera_resolution(item,
                    manager.camera_choices(catalog, board)[0])
                self.assertEqual(selected['command'][-2], '--resolution')
                self.assertNotIn('--resolution', item['command'])

    def test_every_camera_launcher_offers_the_som_capture_modes(self):
        catalog = manager.load_catalog()
        for board in catalog['platforms']:
            choices = manager.camera_choices(catalog, board)
            self.assertTrue(choices, board)
            for launcher in manager.launchers_for(catalog, board):
                if '--camera' in launcher['command']:
                    self.assertTrue(launcher.get('select_camera'), launcher['id'])
                    for choice in choices:
                        selected = manager.with_camera_resolution(launcher, choice)
                        self.assertEqual(selected['command'][-1], choice['value'])

    def test_camera_badge_matches_video_geometry_and_uses_capture_size(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        for size in ((640, 480), (720, 480), (1280, 720), (1920, 1080)):
            with patch.object(ui, 'panel') as panel, \
                    patch.object(ui.cv2, 'putText') as draw:
                ui.camera_resolution(frame, size)
            self.assertEqual(panel.call_args.args[1:5], (496, 174, 280, 36))
            self.assertEqual(draw.call_args.args[1], f'{size[0]} x {size[1]}')
            self.assertEqual(draw.call_args.args[2][0], 508)

    def test_badge_origin_does_not_change_with_values(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui, 'panel') as panel:
            ui.statistics(frame, 1.2, 9.9)
            first = panel.call_args_list
            panel.reset_mock()
            ui.statistics(frame, 123.4, 100.0)
            self.assertEqual(first, panel.call_args_list)

    def test_fps_inference_and_resolution_values_share_a_fixed_column(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        for ms, rate in ((9.1, 24.1), (123.4, 100.0)):
            with patch.object(ui.cv2, 'putText') as draw:
                ui.statistics(frame, ms, rate)
                ui.camera_resolution(frame, (1920, 1080))
            values = {call.args[1]: call.args[2] for call in draw.call_args_list}
            for text in (f'{ms:.1f} ms', f'{rate:.1f}', '1920 x 1080'):
                self.assertEqual(values[text][0], 508)
            self.assertNotIn('ms', values)
            self.assertEqual(values[f'{rate:.1f}'][1] - values[f'{ms:.1f} ms'][1], 42)

    def test_video_resolution_panel_is_below_fps_and_has_fixed_geometry(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        origins = []
        for size in ((1280, 720), (1920, 1080)):
            with patch.object(ui, 'panel') as panel, \
                    patch.object(ui.cv2, 'putText') as draw:
                ui.video_resolution(frame, size)
            origins.append(panel.call_args.args[1:5])
            self.assertIn(f'{size[0]} x {size[1]}', draw.call_args.args[1])
        self.assertEqual(origins, [(496, 174, 280, 36)] * 2)

    def test_header_metrics_and_temperature_share_right_edge(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui, 'panel') as panel, patch.object(ui, 'logo_image', return_value=None):
            ui.branding(frame)
            ui.statistics(frame, 9, 25)
            ui.video_resolution(frame, (1280, 720))
            ui.temperature(frame, 60)
        for call in panel.call_args_list:
            self.assertEqual(call.args[1] + call.args[3], 800 - ui.MARGIN)

    def test_branding_is_above_results_and_identifies_the_processor(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui, 'logo_image', return_value=None), \
                patch.object(ui, 'som_name', return_value='i.MX 93'), \
                patch.object(ui.cv2, 'putText') as draw:
            ui.branding(frame)
        texts = {call.args[1]: call.args[2] for call in draw.call_args_list}
        name = 'DART-MX93 / VAR-SOM-MX93'
        width = ui.cv2.getTextSize(name, ui.FONT, .55, 1)[0][0]
        self.assertEqual(texts[name], (800 - ui.MARGIN - 12 - width, 60))
        self.assertLess(texts['VARISCITE'][1], ui.FIELD_TOP)

    def test_soc_is_in_model_footer_for_each_platform(self):
        for name in ('i.MX 8M Plus', 'i.MX 93', 'i.MX 95'):
            frame = np.zeros((480, 800, 3), np.uint8)
            with patch.object(ui, 'som_name', return_value=name), \
                    patch.object(ui, 'branding'), \
                    patch.object(ui.cv2, 'putText') as draw:
                ui.model(frame, 'Model | NPU')
            self.assertEqual(draw.call_args.args[1], f'{name} | Model | NPU')

    def test_face_count_is_centered_in_panel(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        text = 'Faces detected: 1'
        (width, height), _ = ui.cv2.getTextSize(text, ui.FONT, .6, 1)
        with patch.object(ui.cv2, 'putText') as draw:
            ui.results(frame, [(text, None)])
        self.assertEqual(draw.call_args.args[2],
                         (ui.MARGIN + (320 - width) // 2,
                          ui.FIELD_TOP + 23 + height // 2))

    def test_real_logo_alpha_blends_without_mutating_the_asset(self):
        logo = np.full((28, 140, 4), 255, np.uint8)
        logo[:, :, 3] = 128
        original = logo.copy()
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui, 'logo_image', return_value=logo):
            ui.branding(frame)
        np.testing.assert_array_equal(logo, original)
        self.assertTrue(frame[39:67, 36:176].any())

    def test_rounded_panel_preserves_corner_pixels(self):
        frame = np.full((50, 100, 3), 180, np.uint8)
        ui.panel(frame, 10, 10, 80, 30)
        np.testing.assert_array_equal(frame[10, 10], [180] * 3)
        self.assertFalse(np.all(frame[25, 50] == 180))
        self.assertIs(ui.panel_mask(30, 80), ui.panel_mask(30, 80))

    def test_branding_and_footer_leave_hd_letterbox_untouched(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        frame[15:465] = 180
        with patch.object(ui, 'logo_image', return_value=None):
            ui.model(frame, 'Model | NPU')
        ui.temperature(frame, 60)
        self.assertFalse(frame[:15].any())
        self.assertFalse(frame[465:].any())

    def test_semantic_colors_independent_of_class_index(self):
        self.assertEqual(ui.color_for(' person '), ui.PALETTE[0])
        self.assertEqual(ui.color_for('CAR'), ui.PALETTE[2])
        self.assertEqual(ui.color_for('car', True), ui.color_for('car')[::-1])

    def test_faces_can_use_boxes_without_overlapping_label_panels(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        with patch.object(ui.cv2, 'putText') as draw:
            ui.box(frame, (100, 100, 150, 160), 'face', .9, show_label=False)
        draw.assert_not_called()
        self.assertTrue(frame.any())

    def test_box_labels_avoid_header_metrics_and_footer(self):
        frame = np.zeros((480, 800, 3), np.uint8)
        for bounds in ((180, 32, 780, 465), (700, 100, 799, 300),
                       (20, 445, 150, 479)):
            with patch.object(ui.cv2, 'rectangle') as rect:
                ui.box(frame, bounds, 'person', .8)
            left, top = rect.call_args.args[1]
            right, bottom = rect.call_args.args[2]
            self.assertGreaterEqual(top, ui.HEADER_TOP + 42 + 8)
            self.assertLessEqual(bottom, 480 - ui.HEADER_TOP - 34 - 8)
            self.assertLess(right, 800)
            self.assertTrue(right < 496 or top >= ui.FIELD_TOP + 2 * ui.FIELD_STEP + 36)

    def test_rgb_and_bgr_paths_have_same_colors(self):
        bgr = np.zeros((480, 800, 3), np.uint8)
        rgb = bgr.copy()
        for frame, is_rgb in [(bgr, False), (rgb, True)]:
            ui.statistics(frame, 12.3, 25, is_rgb)
            ui.video_resolution(frame, (1920, 1080), is_rgb)
            ui.model(frame, 'SSD | NPU', is_rgb)
            ui.temperature(frame, 81.2, is_rgb)
            ui.results(frame, [('person', .95)], is_rgb)
            ui.box(frame, (200, 150, 400, 300), 'car', .8, is_rgb)
        np.testing.assert_array_equal(bgr, rgb[:, :, ::-1])
