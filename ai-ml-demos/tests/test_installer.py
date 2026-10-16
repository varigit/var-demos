import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'install.sh'


class InstallerTests(unittest.TestCase):
    def test_active_installation_is_protected(self):
        source = SCRIPT.read_text()
        function = re.search(
            r'^ensure_not_running\(\) \{\n.*?^\}', source,
            flags=re.MULTILINE | re.DOTALL,
        ).group()
        with tempfile.TemporaryDirectory() as directory:
            child = subprocess.Popen(
                ['python3', '-c', 'import time; time.sleep(60)'],
                cwd=directory,
            )
            try:
                result = subprocess.run(
                    ['sh', '-c', 'INSTALL_ROOT=$1\n'
                     'require_command() { command -v "$1"; }\n'
                     'fail() { echo "$*" >&2; exit 1; }\n' + function +
                     '\nensure_not_running', 'test', directory],
                    capture_output=True, text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('installation is in use', result.stderr)
                self.assertIsNone(child.poll())
            finally:
                child.terminate()
                child.wait()

    def test_download_replaces_the_demo_asset(self):
        self.check_asset_download(prefetch=False)

    def test_prefetch_keeps_the_installed_asset_untouched(self):
        self.check_asset_download(prefetch=True)

    def test_verified_upstream_https_asset_uses_its_own_url(self):
        self.check_asset_download(prefetch=False,
                                  remote='https://models.example.invalid/face.tflite')

    def check_asset_download(self, prefetch, remote='media/test.mp4'):
        source = SCRIPT.read_text()
        functions = '\n'.join(
            re.search(
                rf'^{name}\(\) \{{\n.*?^\}}', source,
                flags=re.MULTILINE | re.DOTALL,
            ).group()
            for name in ('progress', 'download', 'install_asset')
        )
        payload = b'new verified video content'
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / 'fixture'
            fixture.write_bytes(payload)
            destination = root / 'install/hd/assets/videos/test.mp4'
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b'old static sample')
            (root / 'work/assets').mkdir(parents=True)
            shell = '''
set -eu
INSTALL_ROOT=$1/install
WORK_DIR=$1/work
FIXTURE=$1/fixture
REQUEST=$1/request
ASSET_BASE_URL=https://example.invalid
PREFETCH_ONLY=$3
fail() { echo "$*" >&2; exit 1; }
curl() {
    for argument in "$@"; do
        case "$argument" in https://*) printf '%s' "$argument" > "$REQUEST" ;; esac
    done
    while [ "$#" -gt 0 ]; do
        if [ "$1" = --output ]; then
            cp "$FIXTURE" "$2"
            return
        fi
        shift
    done
    exit 1
}
'''
            subprocess.run(
                ['sh', '-c', shell + functions +
                 '\ninstall_asset hd "$2" "$4" '
                 'assets/videos/test.mp4', 'test', str(root), digest,
                 '1' if prefetch else '0', remote],
                check=True, capture_output=True, text=True,
            )
            expected = b'old static sample' if prefetch else payload
            self.assertEqual(destination.read_bytes(), expected)
            self.assertEqual((root / 'work/assets' / digest).read_bytes(), payload)
            self.assertEqual((root / 'request').read_text(), remote if remote.startswith(
                'https://') else 'https://example.invalid/' + remote)


if __name__ == '__main__':
    unittest.main()
