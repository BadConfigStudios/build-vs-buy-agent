import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class PluginValidate(unittest.TestCase):
    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_plugin_validates_strictly(self):
        proc = subprocess.run(["claude", "plugin", "validate", "--strict", str(ROOT)],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
