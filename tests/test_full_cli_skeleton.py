import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL_CLI = ROOT / "src" / "full-cli"


class FullCliSkeletonTests(unittest.TestCase):
    def test_full_cli_files_exist(self):
        for rel in ("GNUmakefile", "main.m", "GSCommandContext.h", "GSCommandContext.m", "GSCommandRunner.h", "GSCommandRunner.m"):
            with self.subTest(rel=rel):
                self.assertTrue((FULL_CLI / rel).exists())

    def test_gnumakefile_declares_tool(self):
        content = (FULL_CLI / "GNUmakefile").read_text()
        self.assertIn("TOOL_NAME = gnustep", content)
        self.assertIn("ADDITIONAL_OBJCFLAGS", content)
        self.assertIn("GNUSTEP_MAKEFILES", content)

    def test_runner_lists_expected_commands(self):
        content = (FULL_CLI / "GSCommandRunner.m").read_text()
        for command in ("setup", "doctor", "build", "run", "new", "install", "remove"):
            with self.subTest(command=command):
                self.assertIn(command, content)

    def test_runner_supports_json_and_version(self):
        content = (FULL_CLI / "GSCommandRunner.m").read_text()
        self.assertIn("NSJSONSerialization", content)
        self.assertIn("--version", content)
        self.assertIn("schema_version", content)
        self.assertIn("runNativeCommandForContext", content)
        self.assertIn("repositoryRoot", content)
        self.assertIn("defaultManagedRoot", content)
        self.assertIn("runCommand:", content)
        self.assertIn("executeDoctorForContext", content)
        self.assertIn("executeSetupForContext", content)
        self.assertIn("executeBuildForContext", content)
        self.assertIn("executeRunForContext", content)
        self.assertIn("executeNewForContext", content)
        self.assertIn("executeInstallForContext", content)
        self.assertIn("executeRemoveForContext", content)
        self.assertIn('[command isEqualToString: @"setup"]', content)
        self.assertIn('libexec/gnustep-cli', content)
        self.assertIn('ADDITIONAL_TOOL_LIBS += -ldispatch -lBlocksRuntime', content)
        self.assertNotIn('@"python3"', content)

    def test_context_tracks_global_options(self):
        content = (FULL_CLI / "GSCommandContext.m").read_text()
        for token in ("--json", "--verbose", "--quiet", "--yes", "--help", "--version"):
            with self.subTest(token=token):
                self.assertIn(token, content)
        self.assertIn('if (commandSeen == NO && [argument hasPrefix: @"--"])', content)
        self.assertIn('context->_jsonOutput = YES;', content)


if __name__ == "__main__":
    unittest.main()
