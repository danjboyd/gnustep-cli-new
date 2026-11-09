import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gnustep_cli_shared.doctor_engine import (
    _bundled_authorities_check,
    _bundled_authorities_date,
    build_doctor_payload,
)


TODAY = date(2026, 11, 9)


def _msys2_toolchain(root: Path, source: str | None) -> dict:
    gstls = root / "clang64/lib/GNUstep/Libraries/gnustep-base/Versions/1.31/Resources/GSTLS"
    gstls.mkdir(parents=True)
    (gstls / "ca-certificates.crt").write_text("-----BEGIN CERTIFICATE-----\n")
    if source is not None:
        (gstls / "ca-certificates.source").write_text(source)
    makefiles = root / "clang64/share/GNUstep/Makefiles"
    makefiles.mkdir(parents=True)
    return {"os": "windows", "toolchain": {"gnustep_makefiles": str(makefiles)}}


class BundledAuthoritiesTests(unittest.TestCase):
    def check(self, environment, *, windows=True):
        return _bundled_authorities_check(environment, interface="full", today=TODAY, windows=windows)

    def test_reads_the_date_from_the_recorded_package_version(self):
        self.assertEqual(_bundled_authorities_date("mingw-w64-clang-x86_64-ca-certificates 20260816-1\n"), date(2026, 8, 16))
        self.assertIsNone(_bundled_authorities_date("mingw-w64-clang-x86_64-ca-certificates unknown"))
        self.assertIsNone(_bundled_authorities_date("mingw-w64-clang-x86_64-ca-certificates 20261399-1"))

    def test_a_current_bundle_is_ok(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self.check(_msys2_toolchain(Path(tempdir), "mingw-w64-clang-x86_64-ca-certificates 20260816-1\n"))
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.details["age_days"], 85)
        self.assertEqual(result.execution_tier, "full_only")

    def test_a_bundle_over_a_year_old_warns(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self.check(_msys2_toolchain(Path(tempdir), "mingw-w64-clang-x86_64-ca-certificates 20251108-1\n"))
        self.assertEqual(result.status, "warning")
        self.assertEqual(result.details["age_days"], 366)
        self.assertIn("Update the toolchain", result.message)

    def test_exactly_a_year_old_is_still_ok(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self.check(_msys2_toolchain(Path(tempdir), "mingw-w64-clang-x86_64-ca-certificates 20251109-1\n"))
        self.assertEqual(result.status, "ok")

    def test_windows_bundle_without_a_source_record_warns(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self.check(_msys2_toolchain(Path(tempdir), None))
        self.assertEqual(result.status, "warning")
        self.assertIn("v0.1.5", result.message)

    def test_unrecorded_bundle_elsewhere_is_only_a_fallback(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            gstls = root / "Local/Library/Libraries/gnustep-base/Versions/1.31/Resources/GSTLS"
            gstls.mkdir(parents=True)
            (gstls / "ca-certificates.crt").write_text("x")
            makefiles = root / "System/Library/Makefiles"
            makefiles.mkdir(parents=True)
            result = self.check({"os": "linux", "toolchain": {"gnustep_makefiles": str(makefiles)}}, windows=False)
        self.assertEqual(result.status, "not_run")
        self.assertTrue(result.details["found"])

    def test_unparseable_record_warns(self):
        with tempfile.TemporaryDirectory() as tempdir:
            result = self.check(_msys2_toolchain(Path(tempdir), "something else\n"))
        self.assertEqual(result.status, "warning")

    def test_no_toolchain_is_not_run(self):
        result = self.check({"os": "windows", "toolchain": {"gnustep_makefiles": None}})
        self.assertEqual(result.status, "not_run")
        self.assertFalse(result.details["found"])

    def test_bootstrap_reports_it_as_full_only(self):
        result = _bundled_authorities_check({"toolchain": {}}, interface="bootstrap")
        self.assertEqual(result.status, "not_run")
        self.assertEqual(result.execution_tier, "full_only")

    def test_both_interfaces_list_the_check(self):
        for interface in ("bootstrap", "full"):
            ids = {check["id"] for check in build_doctor_payload(interface=interface)["checks"]}
            self.assertIn("tls.bundled-authorities", ids)


if __name__ == "__main__":
    unittest.main()
