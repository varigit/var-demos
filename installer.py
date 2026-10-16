#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import tomllib

# Do not leave an installer UI bytecode cache behind during uninstallation.
sys.dont_write_bytecode = True
from install_ui import event, run_dashboard

SAMPLE_URL = ('https://nyc3.digitaloceanspaces.com/variscite-marketing/demos/'
              'machine-learning/imx8mplus/v2/media/buildings_458687_1280x720.mp4')
SAMPLE_HASH = 'f6058ff68644e12d86e385a5e30c2d6815e74128d90ead713f42c5816b27c8e2'
MX93_SAMPLE_URL = ('https://nyc3.digitaloceanspaces.com/variscite-marketing/'
                  'demos/machine-learning/imx93/v1/media/'
                  'buildings_458687_1280x720.avi')
MX93_SAMPLE_HASH = '7faca1c02fe09337ff473bc8fe3151a80a7d7e976ba47fbc282adfd0e83609f1'
LOGO_URL = ('https://nyc3.digitaloceanspaces.com/variscite-marketing/'
            'demos/branding/v1/variscite-logo-white.png')
LOGO_HASH = 'ba878adab3671263d6907d91ec87be6c1abd049cdef30ee896fd11857b4c9a5c'
OWNED = '.var-demos-owned'


def installed_bin_dir(root):
    marker = root / '.var-demos-installed'
    text = marker.read_text().strip() if marker.is_file() else ''
    if not text:
        return Path('/usr/bin')  # Older installations used an empty marker.
    try:
        metadata = json.loads(text)
        directory = Path(metadata['bin_dir'])
    except (ValueError, TypeError, KeyError) as error:
        raise RuntimeError('Invalid installed command directory') from error
    if not directory.is_absolute():
        raise RuntimeError('Invalid installed command directory')
    return directory


def install_plan(source, board, groups):
    """Count actual manifest entries and copy/check steps, not guessed time."""
    include_ai = any(group['id'] == 'ai-ml' for group in groups)
    ai_root = source / 'ai-ml-demos'
    if not ai_root.exists():
        ai_root = source / 'ai-ml'
    ai = dict(demos=[], launchers=[])
    if include_ai:
        with (ai_root / 'catalog.toml').open('rb') as file:
            ai = tomllib.load(file)
    demos = [demo for demo in ai['demos'] if board in demo['platforms']]
    assets = 0
    if include_ai:
        for demo in demos:
            manifest = ai_root / demo['path'] / demo['manifest']
            assets += sum(bool(line.strip()) and not line.lstrip().startswith('#')
                          for line in manifest.read_text().splitlines())
    media = any(group['id'] == 'multimedia' for group in groups)
    # Dependency checks; prefetch and install each AI asset; demo copies;
    # logo/video verification; non-AI copies; final suite/launcher setup.
    total = (len(groups) + (2 * assets + len(demos) if include_ai else 0)
             + (2 if media else 0)
             + sum(group['id'] != 'ai-ml' for group in groups) + 1)
    ids = {demo['id'] for demo in demos} if include_ai else set()
    launchers = sum(item['demo'] in ids for item in ai['launchers'])
    launchers += sum(group['id'] != 'ai-ml' for group in groups)
    return dict(total=total, asset_total=assets + (2 if media else 0),
                demos=launchers)


def cancelled(_signum, _frame):
    raise InterruptedError('Operation cancelled')


def sample_asset(board):
    if board == 'imx93':
        return MX93_SAMPLE_URL, MX93_SAMPLE_HASH, 'buildings.avi'
    return SAMPLE_URL, SAMPLE_HASH, 'buildings.mp4'


def active_processes(root):
    for process in Path('/proc').glob('[0-9]*'):
        try:
            if process.name == str(os.getpid()):
                continue
            arguments = (process / 'cmdline').read_bytes().split(b'\0')
            if not Path(os.fsdecode(arguments[0])).name.startswith('python'):
                continue
            # The dashboard stays alive while its worker removes the suite.
            # Exempt only our exact parent installer, never another demo.
            if (process.name == str(os.getppid()) and len(arguments) > 1
                    and Path(os.fsdecode(arguments[1])).resolve()
                    == Path(__file__).resolve()):
                continue
            paths = [(process / 'cwd').resolve()]
            if len(arguments) > 1 and arguments[1].startswith(b'/'):
                paths.append(Path(os.fsdecode(arguments[1])).resolve())
            if any(path == root or root in path.parents for path in paths):
                raise RuntimeError(f'Installation in use by PID {process.name}; '
                                   'close var-demos and running demos first')
        except (OSError, ValueError):
            continue


def valid_root(value):
    path = Path(value)
    if (not path.is_absolute() or '..' in path.parts or path.is_symlink()
            or str(path) in ('/', '/opt', '/usr', '/usr/bin', '/home', '/root')
            or path == Path.home()):
        raise RuntimeError(f'Unsafe installation prefix: {value}')
    return path.resolve()


def verified(path, digest=SAMPLE_HASH):
    if not path.is_file():
        return False
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == digest


def link_command(bin_dir, name, target):
    link = bin_dir / name
    if link.exists() or link.is_symlink():
        if not link.is_symlink() or link.readlink() != target:
            raise RuntimeError(f'Refusing to overwrite unrelated {link}')
        return
    link.symlink_to(target)


def remove_legacy_commands(bin_dir, root):
    for name, relative in [('var-ai', 'ai-ml/manager.py'),
                           ('var-media', 'multimedia/video-player/player.py')]:
        link = bin_dir / name
        if link.is_symlink() and link.readlink() == root / relative:
            link.unlink()
            if os.environ.get('VAR_DEMOS_PROGRESS') != '1':
                print(f'Removed obsolete shortcut: {link}')


def main():
    if '--worker' not in sys.argv and not any(
            option in sys.argv for option in ('--list', '--dry-run', '-h', '--help')):
        raise SystemExit(run_dashboard(sys.argv[1:]))
    if '--worker' in sys.argv:
        signal.signal(signal.SIGTERM, cancelled)
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--source', type=Path,
                        default=Path(__file__).resolve().parent)
    parser.add_argument('--prefix', default='/opt/var-demos')
    parser.add_argument('--bin-dir', type=Path)
    parser.add_argument('--only', action='append', choices=['ai-ml',
                         'multimedia', 'opencl'])
    parser.add_argument('--board')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--uninstall', action='store_true')
    args = parser.parse_args()
    source = args.source.resolve()
    root = valid_root(args.prefix)
    if args.bin_dir is None:
        args.bin_dir = installed_bin_dir(root) if args.uninstall else Path('/usr/bin')
    if args.uninstall:
        source = root
    with (source / 'catalog.toml').open('rb') as file:
        catalog = tomllib.load(file)
    compatible = Path('/proc/device-tree/compatible')
    values = compatible.read_bytes().split(b'\0') if compatible.exists() else []
    board = args.board or next((key for key, entry in catalog['platforms'].items()
        if any(value.encode() in values for value in entry['compatible'])), None)
    if not args.uninstall and (board not in catalog['platforms'] or
            catalog['platforms'][board]['status'] != 'validated'):
        raise RuntimeError('This board has not been validated yet')
    groups = [group for group in catalog['groups']
              if (args.uninstall or board in group['platforms'])
              and (not args.only or group['id'] in args.only)]
    if args.list or args.dry_run:
        for group in groups:
            action = 'Remove' if args.uninstall else 'Install'
            print(f"{action}: {group['title']} -> {root / group['id']}")
        return
    if args.uninstall:
        groups = [group for group in groups if (root / group['id']).exists()]
        try:
            plan = install_plan(root, board, groups)
        except (OSError, ValueError, KeyError):
            # Missing manifests must not prevent removal of recognized demos.
            plan = dict(demos='?', asset_total='?')
        event('Checking installed files', board=catalog['platforms'].get(
            board, {}).get('name', 'Installed Variscite suite'),
            total=len(groups) + 1, demos=plan['demos'],
            asset_total=plan['asset_total'])
    else:
        event('Checking system requirements',
              board=catalog['platforms'][board]['name'],
              **install_plan(source, board, groups))
    active_processes(root)
    args.bin_dir = args.bin_dir.resolve()
    if args.uninstall:
        if not (root / '.var-demos-installed').is_file():
            raise RuntimeError('Unrecognized suite installation')
        for group in groups:
            event('Removing ' + group['title'])
            target = root / group['id']
            if target.is_symlink():
                raise RuntimeError(f'Refusing symlink installation: {target}')
            if group['id'] == 'ai-ml' and target.exists():
                subprocess.run(['sh', str(target / 'install.sh'), '--uninstall',
                    '--prefix', str(target), '--bin-dir', str(args.bin_dir)],
                    check=True)
            elif target.exists():
                if not (target / OWNED).is_file():
                    raise RuntimeError(f'Unrecognized installation: {target}')
                shutil.rmtree(target)
            event(group['title'] + ' removed', done=True)
        for name, relative in [('var-demos', 'suite.py'),
                               ('var-media', 'multimedia/video-player/player.py')]:
            link = args.bin_dir / name
            if link.is_symlink() and link.readlink() == root / relative:
                if not args.only or (name == 'var-media' and
                                    'multimedia' in args.only):
                    link.unlink()
        if not args.only:
            if not (root / '.var-demos-installed').is_file():
                raise RuntimeError('Unrecognized suite installation')
            shutil.rmtree(root / 'lib')
            for name in ('suite.py', 'catalog.toml', 'installer.py', 'install.sh',
                         'install_ui.py',
                         '.var-demos-installed'):
                (root / name).unlink(missing_ok=True)
            if not any(root.iterdir()):
                root.rmdir()
        event('Removal complete', done=True)
        return
    # Validate before downloading or changing any installation.
    if (root / 'lib').is_symlink():
        raise RuntimeError('Refusing symlink support directory')
    if not (root / '.var-demos-installed').is_file():
        for name in ('suite.py', 'catalog.toml', 'installer.py', 'install.sh',
                     'install_ui.py'):
            if (root / name).exists() or (root / name).is_symlink():
                raise RuntimeError(f'Refusing unrelated {root / name}')
    for group in groups:
        event('Checking ' + group['title'])
        target = root / group['id']
        if target.is_symlink():
            raise RuntimeError(f'Refusing symlink installation: {target}')
        if (target.exists() and group['id'] != 'ai-ml'
                and not (target / OWNED).is_file()):
            raise RuntimeError(f'Refusing unrelated directory: {target}')
        if group['id'] == 'multimedia':
            subprocess.run([sys.executable,
                str(source / group['source'] / 'video-player/player.py'),
                '--check'], check=True)
        if group['id'] == 'opencl':
            subprocess.run([sys.executable,
                str(source / group['source'] / 'vector_add.py'),
                '--check'], check=True)
        event(group['title'] + ' compatibility checked', done=True)
    for name, relative in [('var-demos', 'suite.py')]:
        link = args.bin_dir / name
        if (link.exists() or link.is_symlink()) and (
                not link.is_symlink() or link.readlink() != root / relative):
            raise RuntimeError(f'Refusing to overwrite unrelated {link}')
    # Yocto often mounts /tmp AND /var/tmp on RAM-backed tmpfs. MJPEG media
    # can exceed it; stage on the destination filesystem without publishing
    # unverified assets. The context removes only its own generated directory.
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.var-demos-stage-',
                                     dir=root.parent) as temporary:
        cache = Path(temporary) / 'sample-video'
        logo_cache = Path(temporary) / 'variscite-logo-white.png'
        if any(group['id'] == 'multimedia' for group in groups):
            event('Preparing player logo', download=str(logo_cache))
            previous_logo = (root / 'multimedia/video-player/media'
                             / 'variscite-logo-white.png')
            if verified(previous_logo, LOGO_HASH):
                shutil.copy2(previous_logo, logo_cache)
            else:
                subprocess.run(['curl', '-fsSL', '--retry', '2', LOGO_URL,
                                '-o', str(logo_cache)], check=True)
            if not verified(logo_cache, LOGO_HASH):
                raise RuntimeError('Player logo SHA-256 mismatch')
            event('Player logo verified', done=True, asset=True)
            sample_url, sample_hash, sample_name = sample_asset(board)
            previous = [root / 'multimedia/video-player/media' / sample_name,
                root / 'ai-ml/high-resolution-video-detection/assets/videos/'
                       'buildings_458687_1280x720.mp4',
                root / 'ai-ml/camera-vision/assets/videos' /
                       sample_url.rsplit('/', 1)[1]]
            reusable = next((path for path in previous
                             if verified(path, sample_hash)), None)
            event('Preparing player video', download=str(cache))
            if reusable:
                shutil.copy2(reusable, cache)
            else:
                subprocess.run(['curl', '-fsSL', '--retry', '2', sample_url,
                                '-o', str(cache)], check=True)
            if not verified(cache, sample_hash):
                raise RuntimeError('Sample video SHA-256 mismatch')
            event('Player video verified', done=True, asset=True)
        root.mkdir(parents=True, exist_ok=True)
        for group in groups:
            event('Installing ' + group['title'])
            target = root / group['id']
            if group['id'] == 'ai-ml':
                subprocess.run(['sh', str(source / 'ai-ml-demos/install.sh'),
                    '--source', str(source / 'ai-ml-demos'), '--prefix',
                    str(target), '--bin-dir', str(args.bin_dir), '--board',
                    board, '--no-launcher'], check=True,
                    env={**os.environ, 'TMPDIR': temporary})
            else:
                shutil.copytree(source / group['source'], target,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                        '__pycache__', '*.pyc', 'tests'))
                (target / OWNED).touch()
            if group['id'] == 'multimedia':
                media = target / 'video-player/media'
                media.mkdir(exist_ok=True)
                shutil.copy2(cache, media / sample_name)
                shutil.copy2(logo_cache, media / 'variscite-logo-white.png')
                (target / 'video-player/player.py').chmod(0o755)
            if group['id'] != 'ai-ml':
                event(group['title'] + ' installed', done=True)
        event('Setting up the demo menu')
        lib = root / 'lib'
        lib.mkdir(exist_ok=True)
        for name in ('manager.py', 'terminal_ui.py', 'runtime.py', 'telemetry.py',
                     'vision_overlay.py', 'vision_window.py', 'demo_menu.py'):
            shutil.copy2(source / 'ai-ml-demos' / name, lib / name)
        for name in ('suite.py', 'catalog.toml', 'installer.py', 'install.sh',
                     'install_ui.py'):
            shutil.copy2(source / name, root / name)
        (root / 'suite.py').chmod(0o755)
        (root / 'install.sh').chmod(0o755)
        (root / '.var-demos-installed').write_text(json.dumps(
            {'bin_dir': str(args.bin_dir.resolve())}) + '\n')
        args.bin_dir.mkdir(parents=True, exist_ok=True)
        link_command(args.bin_dir, 'var-demos', root / 'suite.py')
        remove_legacy_commands(args.bin_dir, root)
    event('Installation complete', done=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'Error: {error}')
