from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PlatformCatalogTests(unittest.TestCase):
    def test_ai_models_and_delegates_are_platform_specific(self):
        with (ROOT / 'ai-ml-demos/catalog.toml').open('rb') as source:
            catalog = tomllib.load(source)
        platforms = catalog['platforms']
        self.assertEqual(platforms['imx95']['delegate_path'],
                         '/usr/lib/libneutron_delegate.so')
        self.assertEqual(platforms['imx8mplus']['delegate_path'],
                         '/usr/lib/libvx_delegate.so')
        mx95 = {demo['id'] for demo in catalog['demos']
                if 'imx95' in demo['platforms']}
        self.assertEqual(mx95, {'vision-imx95'})
        for demo in catalog['demos']:
            if demo['id'] == 'vision-imx95':
                self.assertEqual(demo['platforms'], ['imx95'])
            elif demo['id'] == 'vision-imx93':
                self.assertEqual(demo['platforms'], ['imx93'])
            else:
                self.assertEqual(demo['platforms'], ['imx8mplus'])
        self.assertEqual(platforms['imx93']['status'], 'validated')
        self.assertEqual(platforms['imx93']['delegate_path'],
                         '/usr/lib/libethosu_delegate.so')

    def test_neutron_assets_use_hashes_and_external_storage(self):
        directory = ROOT / 'ai-ml-demos/neutron-classification'
        entries = (directory / 'assets.manifest').read_text().splitlines()
        self.assertEqual(len(entries), 3)
        for line in entries:
            digest, remote, local = line.split()
            self.assertEqual(len(digest), 64)
            int(digest, 16)
            self.assertEqual(remote, local)
            self.assertFalse((directory / local).exists())


if __name__ == '__main__':
    unittest.main()
