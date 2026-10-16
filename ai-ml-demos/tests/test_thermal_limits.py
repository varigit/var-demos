# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime


class ThermalLimitTests(unittest.TestCase):
    def tearDown(self):
        runtime.thermal_limits.cache_clear()

    def zone(self, root, name, passive, critical, index=0):
        zone = Path(root) / f'thermal_zone{index}'
        zone.mkdir()
        (zone / 'type').write_text(name)
        for number, kind, value in ((0, 'passive', passive), (1, 'critical', critical)):
            (zone / f'trip_point_{number}_type').write_text(kind)
            (zone / f'trip_point_{number}_temp').write_text(str(value * 1000))
        return zone

    def test_actual_bsp_policies_keep_conservative_headroom(self):
        for name, passive, critical, expected in (
                ('soc-thermal', 85, 95, (80, 82, 78)),
                ('cpu-thermal', 95, 100, (88, 90, 86)),
                ('a55-thermal', 105, 125, (93, 95, 91))):
            with tempfile.TemporaryDirectory() as directory:
                self.zone(directory, name, passive, critical)
                runtime.thermal_limits.cache_clear()
                with patch.object(runtime, 'THERMAL_ROOT', Path(directory)):
                    self.assertEqual(runtime.thermal_limits(), expected)

    def test_missing_or_incomplete_policy_keeps_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(runtime, 'THERMAL_ROOT', Path(directory)):
                self.assertEqual(runtime.thermal_limits(), (80, 82, 78))
                zone = self.zone(directory, 'cpu-thermal', 95, 100)
                (zone / 'trip_point_0_temp').write_text('invalid')
                runtime.thermal_limits.cache_clear()
                self.assertEqual(runtime.thermal_limits(), (80, 82, 78))

    def test_strictest_soc_zone_wins_and_unrelated_sensor_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            self.zone(directory, 'cpu-thermal', 95, 100)
            self.zone(directory, 'soc-thermal', 85, 95, 1)
            self.zone(directory, 'battery', 45, 55, 2)
            with patch.object(runtime, 'THERMAL_ROOT', Path(directory)):
                self.assertEqual(runtime.thermal_limits(), (80, 82, 78))

    def test_mx95_does_not_pause_at_old_universal_limit(self):
        with patch.object(runtime, 'temperature', return_value=85), \
                patch.object(runtime, 'clock_is_limited', return_value=False), \
                patch.object(runtime, 'sleep') as sleep:
            pacer = runtime.ThermalPacer(clock_paced=True,
                                        limits=runtime.ThermalLimits(93, 95, 91))
            self.assertTrue(pacer.wait())
            self.assertFalse(pacer.cooling)
            self.assertFalse(pacer.warm)
            sleep.assert_not_called()

    def test_real_driver_throttling_still_pauses_below_app_limit(self):
        with patch.object(runtime, 'temperature', return_value=70), \
                patch.object(runtime, 'clock_is_limited', return_value=True), \
                patch('builtins.print'):
            pacer = runtime.ThermalPacer(limits=runtime.ThermalLimits(93, 95, 91))
            self.assertFalse(pacer.wait(lambda: True))
            self.assertTrue(pacer.cooling)
