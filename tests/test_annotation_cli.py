"""Planning must work without model packages and must not write outputs."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class AnnotationPlanningTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = self.root/'inputs'
        for split in ('train','valid','test'):
            folder = self.inputs/split
            folder.mkdir(parents=True)
            # Discovery is filename-only; inference would decode real images later.
            (folder/'sample.jpg').write_bytes(b'plan-only fixture')
        self.script = Path(__file__).resolve().parents[1]/'scripts/02_auto_annotate.py'

    def invoke(self,*arguments):
        # -S removes third-party site-packages entirely.
        return subprocess.run([sys.executable,'-S',str(self.script),'--input',str(self.inputs),*arguments],
                              capture_output=True,text=True,timeout=20)

    def test_default_plan_needs_no_model_dependencies_and_writes_nothing(self):
        result = self.invoke('--output',str(self.root/'draft'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("'val': 1",result.stdout)
        self.assertIn('Plan only',result.stdout)
        self.assertFalse((self.root/'draft').exists())

    def test_invalid_output_is_rejected_before_loading_model_packages(self):
        result = self.invoke('--run','--output',str(self.root/'outside'))
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Output must be a new subdirectory',result.stderr)
        self.assertNotIn('ModuleNotFoundError',result.stderr)
        self.assertFalse((self.root/'outside').exists())


if __name__ == '__main__':
    unittest.main()
