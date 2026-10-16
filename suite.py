#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path
import argparse
import os
import sys
import tomllib

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'lib'))
sys.path.insert(0, str(ROOT / 'ai-ml'))
sys.path.insert(0, str(ROOT / 'ai-ml-demos'))
import manager
from runtime import CLOCK_SCALE
from telemetry import SoCTemperature


def add_external_demos(catalog):
    """Expose curated BSP executables without installing or owning them."""
    available = []
    for entry in catalog.get('external_demos', []):
        executable = Path(entry['executable'])
        if (not executable.is_absolute()
                or '..' in executable.parts
                or not executable.is_relative_to('/opt/imx-gpu-sdk')
                or not executable.is_file()
                or not os.access(executable, os.X_OK)):
            continue
        demo_id = 'bsp/' + entry['id']
        catalog['demos'].append({
            'id': demo_id, 'path': str(executable.parent),
            'platforms': entry['platforms'],
        })
        available.append({
            'id': demo_id, 'demo': demo_id, 'group': 'bsp',
            'title': entry['title'], 'description': entry['description'],
            'command': [str(executable)], 'native_wayland': True,
        })
    if available:
        catalog['groups'].append({
            'id': 'bsp', 'title': 'Installed BSP demos /opt',
            'description': 'Existing GPU examples supplied with the image',
            'platforms': sorted({platform
                                 for entry in catalog['external_demos']
                                 for platform in entry['platforms']}),
        })
        catalog['launchers'].extend(available)


def load_suite():
    with (ROOT / 'catalog.toml').open('rb') as source:
        catalog = tomllib.load(source)
    catalog['demos'] = []
    catalog['groups'] = [group for group in catalog['groups']
                         if (ROOT / group['id']).is_dir()]
    for group in catalog['groups']:
        catalog['demos'].append({
            'id': group['id'], 'path': group['id'],
            'platforms': group['platforms'],
        })
        if group['id'] != 'ai-ml':
            continue
        with (ROOT / 'ai-ml/catalog.toml').open('rb') as source:
            ai = tomllib.load(source)
        for name, platform in ai.get('platforms', {}).items():
            if name in catalog['platforms']:
                catalog['platforms'][name]['camera_resolutions'] = platform.get('camera_resolutions', [])
        for demo in ai['demos']:
            demo['id'] = 'ai-ml/' + demo['id']
            demo['path'] = 'ai-ml/' + demo['path']
            catalog['demos'].append(demo)
        for launcher in ai['launchers']:
            launcher['demo'] = 'ai-ml/' + launcher['demo']
            if launcher.get('video_demo'):
                launcher['video_demo'] = 'ai-ml/' + launcher['video_demo']
            launcher['group'] = 'ai-ml'
            catalog['launchers'].append(launcher)
        for video in ai.get('videos', []):
            video['demo'] = 'ai-ml/' + video['demo']
        catalog['videos'] = ai.get('videos', [])
    if not catalog.get('videos'):
        for launcher in catalog['launchers']:
            if launcher.get('video_demo_by_platform'):
                launcher.pop('select_video', None)
    add_external_demos(catalog)
    return catalog


def show_status():
    installed = (ROOT / '.var-demos-installed').is_file()
    print('VARISCITE DEMOS')
    print(f'Installation: {ROOT}')
    if not installed:
        print('State: not a recognized installed suite')
        return 1
    catalog = load_suite()
    try:
        platform = manager.detect_platform(catalog)
    except RuntimeError as error:
        print(f'Board: {error}')
        return 1
    print(f'Board: {catalog["platforms"][platform]["name"]}')
    launchers = manager.launchers_for(catalog, platform)
    for group in catalog['groups']:
        count = sum(item.get('group') == group['id'] for item in launchers)
        if count:
            print(f'{group["title"]}: {count} demos')
    missing = []
    for demo in catalog['demos']:
        if (platform not in demo.get('platforms', [])
                or demo['id'].startswith('bsp/')):
            continue
        directory = ROOT / demo['path']
        manifest = directory / 'assets.manifest'
        if manifest.is_file():
            for line in manifest.read_text().splitlines():
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                fields = line.split()
                if len(fields) != 3:
                    missing.append(f'Invalid manifest: {manifest}')
                elif not (directory / fields[2]).is_file():
                    missing.append(str(directory / fields[2]))
    if any(group['id'] == 'multimedia' for group in catalog['groups']):
        media = ROOT / 'multimedia/video-player/media'
        sample = 'buildings.avi' if platform == 'imx93' else 'buildings.mp4'
        for filename in (sample, 'variscite-logo-white.png'):
            if not (media / filename).is_file():
                missing.append(str(media / filename))
    print('Assets: present (checksums verified at install)' if not missing
          else f'Assets: {len(missing)} missing or invalid entries')
    for filename in missing:
        print(f'  {filename}')
    if platform == 'imx8mplus':
        sensors = [('SoC temperature', manager.SOC_TEMPERATURE)]
    elif platform == 'imx93':
        sensors = [('CPU temperature (cpu-thermal)',
                    SoCTemperature(sensor_name='cpu-thermal'))]
    else:
        sensors = [('CPU temperature (a55-thermal)',
                    SoCTemperature(sensor_name='a55-thermal')),
                   ('Analog temperature (ana-thermal)',
                    SoCTemperature(sensor_name='ana-thermal'))]
    for label, sensor in sensors:
        value = sensor.read()
        print(f'{label}: unavailable' if value is None
              else f'{label}: {value:.1f} C')
    if platform != 'imx8mplus' or not CLOCK_SCALE.is_file():
        print('GPU/NPU clock limitation indicator: unavailable')
    else:
        print('GPU/NPU clock: thermally limited' if manager.clock_is_limited()
              else 'GPU/NPU clock: not reporting thermal limitation')
    return 1 if missing else 0


def main():
    arguments = sys.argv[1:]
    if arguments == ['status']:
        return show_status()
    parser = argparse.ArgumentParser(description='Variscite demo manager')
    parser.add_argument('--status', action='store_true',
                        help='show installed demos, assets and board status')
    parser.add_argument('--uninstall', action='store_true',
                        help='remove this installed suite, preserving BSP demos')
    parser.add_argument('--dry-run', action='store_true',
                        help='preview --uninstall without removing files')
    parser.add_argument('--list', action='store_true', help='list available demos')
    parser.add_argument('--run', metavar='LAUNCHER', help='run a demo by id')
    parser.add_argument('--platform', help='select a catalog platform')
    parser.add_argument('--plain', action='store_true', help='use the text menu')
    args = parser.parse_args(arguments)
    if args.uninstall:
        if args.status or args.list or args.run or args.platform or args.plain:
            parser.error('--uninstall only accepts --dry-run')
        if not (ROOT / '.var-demos-installed').is_file():
            raise SystemExit('Unrecognized suite installation')
        command = [sys.executable, str(ROOT / 'installer.py'),
                   '--prefix', str(ROOT), '--uninstall']
        if args.dry_run:
            command.append('--dry-run')
        # Replace the caller so the active-process guard does not count it.
        os.execv(sys.executable, command)
        return 0
    if args.dry_run:
        parser.error('--dry-run requires --uninstall')
    if args.status:
        if args.list or args.run or args.platform or args.plain:
            parser.error('--status cannot be combined with demo options')
        return show_status()
    manager.ROOT = ROOT
    manager.load_catalog = load_suite
    return manager.main()


if __name__ == '__main__':
    raise SystemExit(main())
