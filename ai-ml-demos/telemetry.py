# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
from time import monotonic


class SoCTemperature:
    """Read the SoC sensor at most once per second, not on every frame."""

    def __init__(self, thermal_root='/sys/class/thermal',
                 sensor_name='soc-thermal'):
        self.root = Path(thermal_root)
        self.sensor_name = sensor_name
        self.sensor = None
        self.next_read = 0
        self.value = None

    def read(self):
        now = monotonic()
        if now < self.next_read:
            return self.value
        self.next_read = now + 1
        try:
            if self.sensor is None:
                for zone in sorted(self.root.glob('thermal_zone*')):
                    try:
                        name = (zone / 'type').read_text().strip()
                    except OSError:
                        continue
                    if name == self.sensor_name:
                        self.sensor = zone / 'temp'
                        break
            self.value = (
                int(self.sensor.read_text()) / 1000
                if self.sensor is not None else None
            )
        except (OSError, ValueError):
            self.value = None
            self.sensor = None
        return self.value


def board_sensor_name():
    try:
        compatible = Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
    except OSError:
        return 'soc-thermal'
    if b'fsl,imx95' in compatible:
        return 'a55-thermal'
    if b'fsl,imx93' in compatible:
        return 'cpu-thermal'
    return 'soc-thermal'


SOC_TEMPERATURE = SoCTemperature(sensor_name=board_sensor_name())


def draw_soc_temperature(frame, panel_color, text_color, rgb=False):
    from vision_overlay import temperature
    temperature(frame, SOC_TEMPERATURE.read(), rgb)
