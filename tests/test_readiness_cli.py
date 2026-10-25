"""The accepted source must not implicitly reapply historical exclusions."""
from pathlib import Path
import subprocess
import sys
import unittest


class ReadinessCliTests(unittest.TestCase):
    def invoke(self, *arguments):
        script = Path(__file__).resolve().parents[1] / 'scripts/00_audit_dataset.py'
        return subprocess.run([sys.executable, '-S', str(script), *arguments],
                              capture_output=True, text=True, timeout=20)

    def test_write_requires_explicit_decisions_and_destination_before_dependencies(self):
        result = self.invoke('--write')
        self.assertEqual(result.returncode, 2)
        self.assertIn('requires explicit --exclusions and --output', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_write_cannot_replace_the_accepted_source(self):
        result = self.invoke('--write', '--input', 'same', '--output', 'same', '--exclusions', 'review.json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Output must be separate', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)


if __name__ == '__main__':
    unittest.main()
