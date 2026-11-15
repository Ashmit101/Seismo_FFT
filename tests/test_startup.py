import subprocess
import sys
import unittest
from pathlib import Path


class StartupTests(unittest.TestCase):
    def test_ui_imports_do_not_load_scientific_stack(self):
        script = (
            "import sys\n"
            "import ground_motion_analyzer.app\n"
            "import ground_motion_analyzer.views\n"
            "import ground_motion_analyzer.widgets\n"
            "heavy = {'numpy', 'pandas', 'scipy', 'matplotlib', 'obspy'}\n"
            "assert not (heavy & set(sys.modules)), heavy & set(sys.modules)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
