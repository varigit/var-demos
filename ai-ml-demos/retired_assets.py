# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause
"""Remove only unmodified, explicitly retired suite samples during updates."""

import hashlib
from pathlib import Path
import re
import sys


def retire(root, manifest):
    root = Path(root)
    if root.is_symlink() or not (root / '.var-ai-installed').is_file():
        raise RuntimeError('Refusing to prune an unrecognized AI installation')
    root = root.resolve()
    removed = []
    for line in Path(manifest).read_text().splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        checksum, relative = line.split()
        relative = Path(relative)
        if (not re.fullmatch('[0-9a-f]{64}', checksum) or relative.is_absolute()
                or '..' in relative.parts or len(relative.parts) < 2):
            raise RuntimeError('Unsafe retired asset entry')
        path = root / relative
        if any(part.is_symlink() for part in [path, *path.parents] if part != root):
            continue
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != checksum:
            print(f'Keeping changed sample: {relative}', flush=True)
            continue
        path.unlink()
        removed.append(relative)
        print(f'Removed retired sample: {relative}', flush=True)
    return removed


if __name__ == '__main__':
    retire(*sys.argv[1:])
