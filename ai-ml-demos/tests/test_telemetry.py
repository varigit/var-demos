import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('telemetry', ROOT / 'telemetry.py')
telemetry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(telemetry)


class TemperatureTests(unittest.TestCase):
    def test_board_selects_named_cpu_zone_instead_of_analog(self):
        for compatible, expected in (
                (b'fsl,imx95\0', 'a55-thermal'),
                (b'fsl,imx93\0', 'cpu-thermal'),
                (b'fsl,imx8mp\0', 'soc-thermal')):
            with patch.object(telemetry.Path, 'read_bytes', return_value=compatible):
                self.assertEqual(telemetry.board_sensor_name(), expected)

    def test_soc_sensor_and_refresh_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cpu = root / 'thermal_zone0'
            soc = root / 'thermal_zone1'
            cpu.mkdir()
            soc.mkdir()
            (cpu / 'type').write_text('cpu-thermal')
            (cpu / 'temp').write_text('81000')
            (soc / 'type').write_text('soc-thermal')
            (soc / 'temp').write_text('76000')
            sensor = telemetry.SoCTemperature(root)
            with patch.object(telemetry, 'monotonic', return_value=10):
                self.assertEqual(sensor.read(), 76)
            (soc / 'temp').write_text('78000')
            with patch.object(telemetry, 'monotonic', return_value=10.5):
                self.assertEqual(sensor.read(), 76)
            with patch.object(telemetry, 'monotonic', return_value=11):
                self.assertEqual(sensor.read(), 78)

    def test_missing_or_invalid_sensor_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            sensor = telemetry.SoCTemperature(directory)
            self.assertIsNone(sensor.read())
            zone = Path(directory) / 'thermal_zone0'
            zone.mkdir()
            (zone / 'type').write_text('soc-thermal')
            (zone / 'temp').write_text('invalid')
            with patch.object(telemetry, 'monotonic', return_value=1e20):
                self.assertIsNone(sensor.read())


if __name__ == '__main__':
    unittest.main()
