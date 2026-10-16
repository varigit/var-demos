# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

"""Small dependency-free installer dashboard; stdout may be a serial TTY."""

import json
import os
import re
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
from time import monotonic

PREFIX = 'VAR_INSTALL_EVENT '


def asset_name(path):
    """Display the same content name regardless of its board-specific container."""
    name = Path(path).name
    face_video = re.fullmatch(r'face_1117992_(1280x720|1920x1080)\.(mp4|avi)', name)
    if face_video:
        quality = '720p' if face_video[1] == '1280x720' else '1080p'
        return f'City Selfie - {quality}'
    video = re.fullmatch(r'(buildings_458687|buildings_458688|chicago|video)_(1280x720|1280x800|1920x1080)\.(mp4|avi)', name)
    if video:
        clip, size, _ = video.groups()
        title = {'buildings_458687': 'Buildings A',
                 'buildings_458688': 'Buildings B',
                 'chicago': 'Chicago traffic', 'video': 'Jijiga street'}[clip]
        resolution = {'1280x720': '720p', '1280x800': '1280 x 800',
                      '1920x1080': '1080p'}[size]
        return f'{title} - {resolution}'
    if name.endswith('.tflite'):
        if name.startswith('people'):
            return 'Selfie Segmenter people model'
        if name.startswith('deeplab'):
            return 'DeepLabV3 segmentation model'
        if name.startswith('ultraface'):
            return 'UltraFace face detection model'
        if name.startswith('mobilenet'):
            return 'MobileNet V1 classification model'
        if name.startswith('ssd'):
            return ('SSD-Lite V2 detection model' if 'neutron' in name
                    else 'SSD MobileNet V1 detection model')
        return {'palm.tflite': 'Hand palm detection model',
                'landmark.tflite': 'Hand landmark model'}.get(name, name)
    if 'labels' in name:
        return ('Classification labels' if 'mobilenet' in name or
                name in ('classification-labels.txt', 'labels.txt')
                else 'Object detection labels')
    return {'classification-image.jpg': 'Classification sample image',
            'face-image.jpg': 'Face detection sample image',
            'segmentation-image.jpg': 'People segmentation sample image',
            'variscite-logo-white.png': 'Variscite logo',
            'example_input.jpg': 'Face detection sample image',
            'detection-image.png': 'Object detection sample image',
            'hand.bmp': 'Hand gesture sample image',
            'LICENSE': 'Model license', 'anchors.csv': 'Hand model anchors',
            'box-priors.txt': 'Object detection anchors'}.get(
                name, Path(name).stem.replace('_', ' ').replace('-', ' '))


def event(message, *, done=False, **fields):
    if os.environ.get('VAR_DEMOS_PROGRESS') == '1':
        print(PREFIX + json.dumps(dict(message=message, done=done, **fields)),
              flush=True)


class Dashboard:
    def __init__(self, stream=None, remove=False):
        self.stream = stream or sys.stdout
        self.tty = self.stream.isatty() and os.environ.get('TERM') != 'dumb'
        self.color = self.tty and 'NO_COLOR' not in os.environ
        self.remove = remove
        self.board = 'Detecting board'
        self.message = 'Preparing installation' if not remove else 'Preparing removal'
        self.completed = self.total = self.assets = self.asset_total = 0
        self.demos = 0
        self.download = None
        self.recent_assets = []
        self.started = monotonic()
        self.lines = 0
        self.last_plain = None

    def accept(self, data):
        self.message = data.get('message', self.message)
        match = re.fullmatch(r'(Downloading|Verifying|Verified|Installing|Installed) (\S+/\S+)', self.message)
        if match:
            identity = data.get('asset_path') or match[2]
            name = asset_name(identity)
            self.message = f'{match[1]} {name}'
            if match[1] in ('Downloading', 'Verifying', 'Verified'):
                entry = next((item for item in self.recent_assets
                              if item['path'] == identity), None)
                if entry is None:
                    entry = dict(path=identity, name=name)
                    self.recent_assets.append(entry)
                    self.recent_assets = self.recent_assets[-3:]
                entry['status'] = match[1]
        for key in ('board', 'total', 'asset_total', 'demos', 'download'):
            if key in data:
                setattr(self, key, data[key])
        if data.get('done'):
            self.completed += 1
            self.download = None
        if data.get('asset'):
            self.assets += 1

    def content(self, outcome=None):
        width = max(24, min(76, shutil.get_terminal_size((80, 24)).columns - 2))
        percent = min(99, self.completed * 100 // max(1, self.total))
        if outcome == 'Complete':
            percent = 100
        bar_width = max(8, width - 10)
        fill = bar_width * percent // 100
        bar = '[' + '=' * fill + ' ' * (bar_width - fill) + f'] {percent:3d}%'
        minutes, seconds = divmod(int(monotonic() - self.started), 60)
        detail = ''
        if self.download:
            path = Path(self.download)
            try:
                detail = f'Downloaded: {path.stat().st_size / 1048576:.1f} MiB'
            except OSError:
                detail = 'Connecting to asset storage'
        action = 'UNINSTALL' if self.remove else 'INSTALL'
        lines = [
            f'VARISCITE  /  DEMOS   {action}', '', self.board,
            f'{self.demos} demos  |  {self.asset_total} assets', '', bar,
            f'Steps {self.completed}/{self.total}  |  {minutes:02}:{seconds:02}',
            (outcome or self.message),
            (detail or (f'SHA-256 verified: {self.assets}/{self.asset_total}'
                        if not self.remove else 'Unrelated files are preserved')),
        ]
        if not self.remove:
            recent = [f'{"OK" if item["status"] == "Verified" else ">"} '
                      f'{item["name"]} | {item["status"]}'
                      for item in self.recent_assets]
            lines.extend(['', 'Recent assets (latest three)',
                          *recent, *([''] * (3 - len(recent)))])
        return lines

    def render(self, outcome=None):
        lines = self.content(outcome)
        if not self.tty:
            text = outcome or self.message
            if text != self.last_plain:
                self.stream.write(f'var-demos: {text}\n')
                self.last_plain = text
            self.stream.flush()
            return
        width = max(24, min(76, shutil.get_terminal_size((80, 24)).columns - 2))
        if self.lines:
            self.stream.write(f'\033[{self.lines}A')
        for index, line in enumerate(lines):
            clean = ''.join(c for c in str(line) if c.isprintable())[:width]
            color = '\033[36m' if self.color and index in (0, 5) else ''
            self.stream.write('\r\033[2K' + color + clean +
                              ('\033[0m' if color else '') + '\n')
        self.lines = len(lines)
        self.stream.flush()

    def __enter__(self):
        self.previous_term = signal.signal(signal.SIGTERM, self.interrupt)
        if self.tty:
            self.stream.write('\r\033[2K\033[?25l')
        self.render()
        return self

    @staticmethod
    def interrupt(_signum, _frame):
        raise KeyboardInterrupt

    def __exit__(self, *_args):
        signal.signal(signal.SIGTERM, self.previous_term)
        if self.tty:
            self.stream.write('\033[0m\033[?25h')
            self.stream.flush()


def run_dashboard(arguments):
    descriptor, logfile = tempfile.mkstemp(prefix='var-demos-', suffix='.log')
    process = None
    last_error = ''
    with os.fdopen(descriptor, 'wb') as log, \
            Dashboard(remove='--uninstall' in arguments) as ui:
        try:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name('installer.py')),
                 '--worker', *arguments], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, start_new_session=True,
                env={**os.environ, 'VAR_DEMOS_PROGRESS': '1',
                     'PYTHONUNBUFFERED': '1'})
            pending = b''
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                reading = True
                while reading:
                    for key, _ in selector.select(.2):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            reading = False
                            break
                        log.write(chunk)
                        log.flush()
                        pending += chunk
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            text = line.decode(errors='replace')
                            if text.startswith(PREFIX):
                                ui.accept(json.loads(text[len(PREFIX):]))
                            elif text.startswith('Error:'):
                                last_error = text
                        pending = pending[-65536:]
                    ui.render()
            result = process.wait()
            if result == 0:
                ui.render('Complete')
                # Successful operation needs no leftover diagnostic log.
                Path(logfile).unlink(missing_ok=True)
                if not ui.remove:
                    print('\nvar-demos')
            else:
                ui.render('Failed - installation was not completed')
                print(f'\n{last_error or "Installer failed"}\nLog: {logfile}')
            return result
        except KeyboardInterrupt:
            if process and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            ui.render('Cancelled - operation was not completed')
            print(f'\nLog: {logfile}')
            return 130
        finally:
            if process is not None and process.stdout is not None:
                process.stdout.close()
