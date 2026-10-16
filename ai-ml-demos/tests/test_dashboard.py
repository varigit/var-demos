import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location('manager', ROOT / 'manager.py')
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class DashboardTests(unittest.TestCase):
    def run_demo(self, code):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(manager.tempfile, 'tempdir', directory):
                with patch('sys.stdout', output):
                    result = manager.run_with_dashboard(
                        {'title': 'Camera detection'},
                        [sys.executable, '-c', code], directory,
                    )
            logs = list(Path(directory).glob('var-ai-*.log'))
            self.assertEqual(len(logs), 1)
            log = logs[0].read_text()
        return result, output.getvalue(), log

    def test_success_keeps_logs_out_of_the_panel(self):
        result, output, log = self.run_demo("print('driver warning')")
        self.assertEqual(result, 0)
        self.assertIn('driver warning', log)
        self.assertNotIn('driver warning', output)
        self.assertNotIn('\x1b[2J', output)
        self.assertNotIn('Command', output)
        self.assertIn('Finished', output)

    def test_failure_remains_visible(self):
        result, output, log = self.run_demo(
            "import sys; print('camera unavailable'); sys.exit(2)"
        )
        self.assertEqual(result, 2)
        self.assertIn('camera unavailable', output)
        self.assertIn('Diagnostic log:', output)
        self.assertIn('camera unavailable', log)

    def test_interrupt_stops_the_child_and_returns_to_the_menu(self):
        with patch.object(manager, 'time') as clock:
            clock.monotonic.side_effect = time.monotonic
            clock.sleep.side_effect = KeyboardInterrupt
            result, output, _ = self.run_demo(
                'import time; time.sleep(60)'
            )
        self.assertEqual(result, 0)
        self.assertIn('Stopped', output)


if __name__ == '__main__':
    unittest.main()
