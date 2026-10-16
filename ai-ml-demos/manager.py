#!/usr/bin/env python3

# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
from collections import deque
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib

from telemetry import SOC_TEMPERATURE
from demo_menu import demo_entries, clean_title, NPU_NAMES
from runtime import (clock_is_limited, temperature, thermal_limits, StartupProgress,
                     CameraUnavailable, check_camera)


ROOT = Path(__file__).resolve().parent


def load_catalog():
    with (ROOT / "catalog.toml").open("rb") as catalog_file:
        return tomllib.load(catalog_file)


def detect_platform(catalog):
    compatible_path = Path("/proc/device-tree/compatible")
    if not compatible_path.is_file():
        raise RuntimeError("Device Tree compatible string is unavailable")

    compatible = compatible_path.read_bytes().split(b"\0")
    values = {value.decode(errors="replace") for value in compatible if value}
    for platform_id, platform in catalog["platforms"].items():
        if values.intersection(platform.get("compatible", [])):
            if platform.get("status") != "validated":
                status = platform.get("status", "unknown")
                raise RuntimeError(
                    f"{platform_id} support is {status}"
                )
            return platform_id
    raise RuntimeError("unsupported platform")


def find_demo(catalog, demo_id):
    return next(demo for demo in catalog["demos"] if demo["id"] == demo_id)


def launchers_for(catalog, platform):
    supported = {
        demo["id"]
        for demo in catalog["demos"]
        if platform in demo.get("platforms", [])
    }
    launchers = [
        launcher
        for launcher in catalog.get("launchers", [])
        if launcher["demo"] in supported
    ]
    order = {'classification-image': 0, 'classification-video': 1,
             'classification-camera': 2, 'detection-image': 3,
             'detection-video': 4, 'detection-camera': 5,
             'face-image': 6, 'face-video': 7, 'face-camera': 8,
             'segmentation-image': 9, 'segmentation-video': 10,
             'segmentation-camera': 11, 'people-segmentation-image': 12,
             'people-segmentation-video': 13, 'people-segmentation-camera': 14}
    def rank(item):
        name = item['id']
        for prefix in ('ethosu-', 'neutron-'):
            name = name.removeprefix(prefix)
        return order.get(name, 15)
    return sorted(launchers, key=rank)


def camera_choices(catalog, platform):
    return catalog['platforms'][platform].get('camera_resolutions', [])


def with_camera_resolution(launcher, resolution):
    return dict(launcher, command=list(launcher['command']) +
                ['--resolution', resolution['value']])


def detect_camera():
    nodes = sorted(Path("/sys/class/video4linux").glob("video*"))
    for node in nodes:
        name_file = node / "name"
        name = name_file.read_text(errors="replace").strip().lower()
        if "capture" in name:
            return f"/dev/{node.name}"

    if shutil.which("v4l2-ctl"):
        for node in nodes:
            device = f"/dev/{node.name}"
            result = subprocess.run(
                ["v4l2-ctl", "--device", device, "--all"],
                capture_output=True,
                text=True,
                check=False,
            )
            output = f"{result.stdout}\n{result.stderr}"
            if "Video Capture" in output and "Memory-to-Memory" not in output:
                return device
    raise RuntimeError("no V4L2 capture device was found")


def command_for(launcher):
    camera = None
    command = []
    for argument in launcher["command"]:
        if argument == "{camera}":
            if camera is None:
                camera = detect_camera()
            command.append(camera)
        else:
            command.append(argument)
    return command


def display_environment():
    environment = os.environ.copy()
    environment.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    environment.setdefault("DISPLAY", ":0")
    environment.pop("WAYLAND_DISPLAY", None)
    environment.pop("QT_QPA_PLATFORM", None)
    return environment


def clear_screen():
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_with_dashboard(launcher, command, directory):
    print(f"\n  {launcher['title']}")
    if launcher.get('terminal_output'):
        print('  Results will appear in the terminal when finished.')
    else:
        print("  The demo opens on the board's display.")
    print("  Ctrl+C: stop and return\n")
    stopped = False
    with tempfile.NamedTemporaryFile(
        prefix='var-ai-', suffix='.log', delete=False
    ) as log:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=environment_for(launcher),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        started = time.monotonic()
        last_elapsed = -1
        cooling = False
        progress = StartupProgress(launcher.get('startup_progress', False))
        try:
            while process.poll() is None:
                elapsed = int(time.monotonic() - started)
                if elapsed != last_elapsed:
                    soc = SOC_TEMPERATURE.read()
                    soc_text = '--' if soc is None else f'{soc:.1f}'
                    peak = temperature()
                    limited = clock_is_limited()
                    inference_demo = launcher.get('group', 'ai-ml') == 'ai-ml'
                    if inference_demo and (limited or (
                            peak is not None and peak >= thermal_limits().pause)):
                        cooling = True
                    elif peak is not None and peak < thermal_limits().resume:
                        cooling = False
                    progress.read(log.name)
                    state = ('Cooling' if cooling else 'Running'
                             if progress.ready else 'Preparing')
                    print(
                        f"\r  {state:<7}  {elapsed // 60:02d}:"
                        f"{elapsed % 60:02d}  |  SoC {soc_text} C    ",
                        end='', flush=True,
                    )
                    last_elapsed = elapsed
                    if not progress.ready:
                        print(f'\n  {progress.message}', flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            stopped = True
        finally:
            stop_process(process)

    if stopped:
        print('\r  Stopped.                                       ')
    elif process.returncode == 0:
        print('\r  Finished.                                      ')
    else:
        print(f'\n  Demo failed (exit {process.returncode}).')
        print(f'  Diagnostic log: {log.name}')
        with open(log.name, encoding='utf-8', errors='replace') as output:
            # Keep failure details visible without dumping startup chatter.
            tail = deque(output, maxlen=8)
        for line in tail:
            line = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', line)
            line = ''.join(
                character for character in line.rstrip()
                if character.isprintable() or character == '\t'
            )
            print(f'  {line}')
    if stopped or process.returncode == 0:
        try:
            from terminal_ui import log_tail, summary_lines
            lines = (log_tail(log.name) if launcher.get('terminal_output') else
                     summary_lines(log.name, time.monotonic() - started))
        except ImportError:
            # The plain interface remains usable on images without curses.
            with open(log.name, 'rb') as output:
                output.seek(0, 2)
                output.seek(max(0, output.tell() - 65536))
                lines = output.read().decode('utf-8', errors='replace').splitlines()[-8:]
        for line in lines:
            line = ''.join(character for character in line
                           if character.isprintable())
            print(f'  {line}')
    return 0 if stopped else process.returncode


def prepare_launch(catalog, launcher, video=None):
    if launcher.get('select_camera') and video is None:
        check_camera(detect_platform(catalog))
    demo = find_demo(catalog, launcher["demo"])
    directory = ROOT / demo["path"]
    if not directory.is_dir():
        raise RuntimeError(f"demo is not installed: {demo['id']}")
    command = command_for(launcher)
    if video is not None:
        video_demo = find_demo(catalog, video.get('demo',
            launcher.get('video_demo', launcher['demo'])))
        video_path = ROOT / video_demo['path'] / video['path']
        if not video_path.is_file():
            raise RuntimeError(f"video is not installed: {video['title']}")
        if launcher.get('video_argument') == 'positional':
            command.append(str(video_path))
        else:
            command.extend(['--video', str(video_path)])
        if '--combination' in command:
            index = command.index('--combination') + 1
            command[index] = str(video['combination'])

    if video is not None:
        launcher = dict(launcher, title=video.get('run_title', video['title']))
    return launcher, command, directory


def environment_for(launcher):
    environment = display_environment()
    if launcher.get('native_wayland'):
        environment['GDK_BACKEND'] = 'wayland'
        runtime = Path(environment['XDG_RUNTIME_DIR'])
        sockets = sorted(path for path in runtime.glob('wayland-*')
                         if path.is_socket())
        if not sockets:
            raise RuntimeError(f'No Wayland display socket in {runtime}')
        environment['WAYLAND_DISPLAY'] = sockets[0].name
    return environment


def run_launcher(catalog, launcher, dashboard=True, video=None):
    launcher, command, directory = prepare_launch(catalog, launcher, video)
    if dashboard and sys.stdout.isatty():
        return run_with_dashboard(launcher, command, directory)
    return subprocess.run(
        command,
        cwd=directory,
        env=environment_for(launcher),
        check=False,
    ).returncode


def show_menu(platform, launchers, back=False, suite=False):
    clear_screen()
    print('VARISCITE DEMOS' if suite else 'VARISCITE AI/ML DEMOS')
    print(f"Platform: {platform}")
    print(f"NPU: {NPU_NAMES.get(platform, 'N/A')}")
    category = None
    for index, launcher in enumerate(launchers, start=1):
        if launcher.get("category") != category:
            category = launcher.get("category")
            if category:
                print(category)
        title = clean_title(launcher.get("menu_title", launcher["title"]))
        description = launcher.get("description", "")
        print(f"  {index}. {title:<9} {description}")
    print('\n  q. Back' if back else '\n  q. Quit')
    print("Demos open fullscreen. Press Esc to close the display.")


def interactive(catalog, platform, launchers):
    all_launchers = launchers
    groups = [group for group in catalog.get('groups', []) if any(
        item.get('group') == group['id'] for item in launchers)]
    selected_group = None
    selected_task = None
    while True:
        if groups and selected_group is None:
            clear_screen()
            print(f'VARISCITE DEMOS | {platform}\n')
            for index, group in enumerate(groups, 1):
                print(f"  {index}. {group['title']}")
            print('\n  q. Quit')
            try:
                choice = input('Choose a category: ').strip().lower()
            except (EOFError, KeyboardInterrupt):
                return 0
            if choice in {'q', 'quit', 'exit'}:
                return 0
            try:
                index = int(choice) - 1
                if not 0 <= index < len(groups):
                    continue
                selected_group = groups[index]
            except ValueError:
                continue
            launchers = [item for item in all_launchers
                         if item.get('group') == selected_group['id']]
        entries = (selected_task['children'] if selected_task else demo_entries(launchers))
        show_menu(platform, entries, back=bool(groups or selected_task), suite=bool(groups))
        if selected_task:
            print(f"\n{selected_task['title']}: choose Image, Video or Camera.")
        try:
            choice = input(
                f"\nSelect {'input' if selected_task else 'demo'} [1-{len(entries)}]: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if choice in {"q", "quit", "exit"}:
            if selected_task:
                selected_task = None
                continue
            if groups:
                selected_group = None
                continue
            return 0
        try:
            if int(choice) < 1:
                continue
            launcher = entries[int(choice) - 1]
        except (ValueError, IndexError):
            continue

        if 'children' in launcher:
            selected_task = launcher
            continue

        try:
            video = None
            if launcher.get('select_camera'):
                check_camera(platform)
                choices = camera_choices(catalog, platform)
                print('\nChoose a camera resolution:')
                for index, item in enumerate(choices, 1):
                    print(f"  {index}. {item['title']}")
                choice = input('Resolution (b: back): ').strip()
                if not choice.isdigit() or not 1 <= int(choice) <= len(choices):
                    continue
                launcher = with_camera_resolution(launcher, choices[int(choice)-1])
            if launcher.get('select_video'):
                video = select_video(catalog, launcher_video_demo(launcher, platform),
                                     launcher.get('video_task'), launcher.get('video_prompt'))
                if video is None:
                    continue
            result = run_launcher(catalog, launcher, video=video)
            if result != 0:
                print(f"\nThe demo could not finish (exit {result}).")
        except CameraUnavailable as error:
            print(f'\nCamera unavailable. {error}')
        except (OSError, RuntimeError) as error:
            print(f"\nError: {error}")
        try:
            input("Press Enter to return to the menu...")
        except (EOFError, KeyboardInterrupt):
            print()


def launcher_video_demo(launcher, platform):
    return launcher.get('video_demo_by_platform', {}).get(platform,
        launcher.get('video_demo', launcher['demo']))


def video_resolutions(catalog, demo_id, task=None):
    available = {item.get('resolution') for item in catalog.get('videos', [])
                 if item['demo'] == demo_id and item.get('task') == task}
    return [dict(id=key, title=title) for key, title in (
        ('720p', 'HD - 720p (1280 x 720)'),
        ('1080p', 'Full HD - 1080p (1920 x 1080)')) if key in available]


def video_choices(catalog, demo_id, resolution, task=None):
    return [dict(item, title=item.get('clip_title', item['title']),
                 menu_title=item.get('clip_title', item['title']),
                 run_title=item['title'])
            for item in catalog.get('videos', [])
            if item['demo'] == demo_id and item.get('resolution') == resolution
            and item.get('task') == task]


def select_plain(title, items):
    while True:
        print('\n' + title + ':')
        for index, item in enumerate(items, start=1):
            print(f"  {index}. {item.get('menu_title', item['title'])}")
        print('  b. Back')
        try:
            choice = input('Choice: ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if choice in {'b', 'q'}:
            return None
        try:
            index = int(choice) - 1
            if 0 <= index < len(items):
                return items[index]
        except ValueError:
            pass


def select_video(catalog, demo_id, task=None, prompt=None):
    resolutions = video_resolutions(catalog, demo_id, task)
    if not resolutions:
        raise RuntimeError('no videos are configured for this demo')
    while True:
        resolution = select_plain('Choose Video Quality', resolutions)
        if resolution is None:
            return None
        video = select_plain(prompt or ('Choose a Face Video' if task == 'face' else 'Choose a Freepik Video'),
                             video_choices(catalog, demo_id, resolution['id'], task))
        if video is not None:
            return video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--run", metavar="LAUNCHER")
    parser.add_argument("--platform")
    parser.add_argument("--plain", action="store_true",
                        help="use the simple text interface")
    args = parser.parse_args()

    catalog = load_catalog()
    platform = args.platform or detect_platform(catalog)
    launchers = launchers_for(catalog, platform)

    if args.list:
        for launcher in launchers:
            print(f"{launcher['id']}\t{launcher['title']}")
        return 0

    if args.run:
        try:
            launcher = next(
                item for item in launchers if item["id"] == args.run
            )
        except StopIteration as error:
            raise SystemExit(f"unknown launcher: {args.run}") from error
        try:
            return run_launcher(catalog, launcher)
        except CameraUnavailable as error:
            print(f'Camera unavailable. {error}')
            return 0

    if (not args.plain and sys.stdin.isatty() and sys.stdout.isatty()
            and os.environ.get('TERM', 'dumb') != 'dumb'):
        try:
            import curses
            from terminal_ui import TerminalUI, serial_console
        except ImportError:
            return interactive(catalog, platform, launchers)
        try:
            if serial_console():
                # The serial login defaults to Linux-console capabilities,
                # but minicom emulates VT100, not the Linux console.
                os.environ['TERM'] = 'vt100'
            return curses.wrapper(
                lambda screen: TerminalUI(
                    screen, catalog, platform, launchers,
                    sys.modules[__name__],
                ).main()
            )
        except curses.error as error:
            print(f'Terminal UI unavailable: {error}; using text mode.')
        except KeyboardInterrupt:
            return 0
    return interactive(catalog, platform, launchers)


if __name__ == "__main__":
    sys.exit(main())
