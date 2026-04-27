import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class NativeUpdateSmokeTests(unittest.TestCase):
    def test_built_full_cli_exposes_update_help_and_json_usage_errors(self):
        script = r'''
set -e
. ./scripts/dev/activate-tools-xctest.sh >/dev/null
make -C src/full-cli clean >/dev/null
make -C src/full-cli >/dev/null
src/full-cli/obj/gnustep update --help
src/full-cli/obj/gnustep --json update bogus
'''
        proc = subprocess.run(['bash','-lc',script], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(proc.stdout.find('gnustep update [all|cli|packages]'), -1, proc.stderr)
        self.assertNotEqual(proc.stdout.find('"command": "update"'), -1, proc.stdout + proc.stderr)
        self.assertNotEqual(proc.stdout.find('Unknown update scope'), -1, proc.stdout + proc.stderr)

if __name__ == '__main__':
    unittest.main()
