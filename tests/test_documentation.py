from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDES = [ROOT / 'README.md', *sorted((ROOT / 'docs').rglob('*.md'))]


class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'README.md').read_text()

    def test_no_obsolete_launchers_or_paths(self):
        for path in GUIDES:
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text(),
                                    r'\bvar-ai\b|\bvar-media\b|tflite/classification|tflite/detection')

    def test_relative_links_resolve(self):
        for path in GUIDES:
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in target:
                    continue
                filename, _, anchor = target.partition('#')
                destination = path.parent / filename if filename else path
                with self.subTest(path=path, target=target):
                    self.assertTrue(destination.exists())
                    if anchor:
                        headings = re.findall(r'^#{1,6}\s+(.+)$',
                                              destination.read_text(), re.M)
                        anchors = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-')
                                   for h in headings}
                        self.assertIn(anchor, anchors)

    def test_official_references(self):
        self.assertIn('https://www.nxp.com/docs/en/user-guide/UG10166.pdf', self.text)
        self.assertIn('matching your BSP', (ROOT / 'docs/README.md').read_text())
        for platform in ('dart-mx8m-plus', 'var-som-mx93', 'dart-mx95'):
            self.assertIn('https://dev.variscite.com/' + platform + '/',
                          (ROOT / 'docs/README.md').read_text())

    def test_install_run_and_uninstall_are_concise(self):
        self.assertLess(len(self.text.splitlines()), 80)
        self.assertIn('curl -fsSL https://raw.githubusercontent.com/'
                      'varigit/var-demos/edge-ai/install.sh | sh', self.text)
        self.assertIn('```sh\nvar-demos\n```', self.text)
        self.assertNotIn('## Uninstalling', self.text)
        self.assertIn('```sh\nvar-demos --uninstall\n```',
                      (ROOT / 'docs/README.md').read_text())
        self.assertIn('run as root', self.text)

    def test_setup_documentation_is_centralized(self):
        self.assertIn('(docs/README.md)', self.text)
        self.assertNotIn('| SoM |', self.text)
        self.assertTrue((ROOT / 'docs/npus/README.md').exists())
        for directory in ('ai-ml-demos', 'multimedia-demos', 'opencl'):
            self.assertEqual(list((ROOT / directory).rglob('README*')), [])
            self.assertEqual(list((ROOT / directory).rglob('*.md')), [])

    def test_public_instructions_do_not_target_personal_fork(self):
        for path in GUIDES:
            self.assertNotRegex(path.read_text(),
                                r'https://(?:github\.com|raw\.githubusercontent\.com)/dorta/')

    def test_model_hashes_match_installer_manifests(self):
        manifests = list((ROOT / 'ai-ml-demos').rglob('*.manifest'))
        assets = '\n'.join(path.read_text() for path in manifests)
        for filename in ('model-conversion.md', 'face-detection.md',
                         'people-segmentation.md', 'hand-gestures.md'):
            text = (ROOT / 'docs' / filename).read_text()
            hashes = re.findall(r'`([a-f0-9]{64})`', text)
            self.assertTrue(hashes, filename)
            for digest in hashes:
                with self.subTest(filename=filename, digest=digest):
                    self.assertIn(digest, assets)
        text = (ROOT / 'docs/segmentation.md').read_text()
        for digest in re.findall(r'^([a-f0-9]{64})  ', text, re.M):
            self.assertIn(digest, assets)

    def test_npu_guides_keep_processing_flows(self):
        for name in ('vip8000', 'ethos-u65', 'neutron'):
            text = (ROOT / 'docs/npus' / (name + '.md')).read_text()
            for heading in ('NPU and Libraries', 'Starting a Demo',
                            'Classification Flow', 'Detection Flow',
                            'Hardware Versus Software'):
                self.assertRegex(text, r'#{2,3} ' + heading)
            self.assertEqual(text.count('```mermaid'), 2)

    def test_inventory_includes_specialized_models(self):
        text = (ROOT / 'docs/models.md').read_text()
        for guide in ('face-detection', 'segmentation', 'people-segmentation',
                      'hand-gestures', 'model-conversion'):
            self.assertIn('(' + guide + '.md)', text)
        self.assertEqual(text.count('```mermaid'), 3)

    def test_benchmarks_keep_comparable_table_structure(self):
        text = (ROOT / 'docs/performance.md').read_text()
        expected = None
        for section in text.split('### ')[1:]:
            rows = [line for line in section.splitlines() if line.startswith('|')]
            scenarios = [row.split('|')[1].strip() for row in rows[2:]]
            if expected is None:
                expected = scenarios
            self.assertEqual(scenarios, expected)
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                self.assertEqual(len(cells), 6)
                self.assertIn(cells[2], ('Measured', 'Functional',
                                        'Experimental', 'Not enabled'))
                if cells[2] != 'Measured':
                    self.assertEqual(cells[3:], ['N/A', 'N/A', 'N/A'])
        self.assertIn('not one standardized benchmark', text)

    def test_license_notices_are_preserved(self):
        for filename in ('LICENSE', 'ai-ml-demos/LICENSE.adoc',
                         'ai-ml-demos/classification/model/LICENSE',
                         'ai-ml-demos/detection/model/LICENSE',
                         'ai-ml-demos/hand-gesture/LICENSE',
                         'docs/third-party.md',
                         'opencl/LICENSE'):
            with self.subTest(filename=filename):
                self.assertTrue((ROOT / filename).is_file())
        self.assertIn('No independent license verification',
                      (ROOT / 'docs/video-sources.md').read_text())
        self.assertIn('[BSD 3-Clause License](LICENSE)', self.text)
        self.assertIn('except where otherwise noted', self.text)
        self.assertIn('BSD 3-Clause License', (ROOT / 'LICENSE').read_text())
        notices = (ROOT / 'docs/third-party.md').read_text().split('## MIT notices\n', 1)[1].strip()
        self.assertIn(notices, (ROOT / 'ai-ml-demos/hand-gesture/LICENSE').read_text())


if __name__ == '__main__':
    unittest.main()
