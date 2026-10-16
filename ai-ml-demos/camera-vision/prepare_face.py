#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

"""Compile the verified source for the tested MX93 BSP, without replacing it."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE_SHA256 = '6d47a446337a9d9d10fa16d4133e976c1d56d84b4a46225ba60352e6fab0d3dd'
COMPILED_SHA256 = '22c836ec31a605b1ac8ae71007437f0a3d88857b3b4a179caf664084af7f4635'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(directory):
    directory = Path(directory)
    source = directory / 'ultraface.tflite'
    destination = directory / 'ultraface_vela.tflite'
    if digest(source) != SOURCE_SHA256:
        raise RuntimeError('UltraFace source checksum does not match the recorded model')
    if destination.is_file() and digest(destination) == COMPILED_SHA256:
        return
    try:
        version = subprocess.check_output(['vela', '--version'], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError('UltraFace on this MX93 BSP requires Vela 3.12.0') from error
    if version != '3.12.0':
        raise RuntimeError(f'Expected BSP Vela 3.12.0, found {version}; '
                           'do not substitute an unvalidated compiler')
    with tempfile.TemporaryDirectory(prefix='.ultraface-', dir=directory) as output:
        subprocess.run(['vela', str(source), '--accelerator-config',
                        'ethos-u65-256', '--output-dir', output], check=True)
        compiled = Path(output) / 'ultraface_vela.tflite'
        if digest(compiled) != COMPILED_SHA256:
            raise RuntimeError('UltraFace Vela output checksum differs from the tested artifact')
        compiled.replace(destination)


if __name__ == '__main__':
    prepare(sys.argv[1])
