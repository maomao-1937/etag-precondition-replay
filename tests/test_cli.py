import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "etag_precondition_replay.py"
CONTINUE = {"status": "continue", "http_status": None, "precondition": None}
INVALID = {"status": "invalid"}


def stop(http_status, field):
    return {"status": "short_circuit", "http_status": http_status, "precondition": field}


class ReplayTests(unittest.TestCase):
    def run_cli(self, *args, **kwargs):
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPT), *args], capture_output=True,
            text=True, encoding="utf-8", timeout=15, **kwargs,
        )

    def assert_raw(self, data, code, report):
        with tempfile.TemporaryDirectory(prefix="etag-fixture-") as directory:
            fixture = Path(directory) / "fixture.json"
            fixture.write_bytes(data)
            result = self.run_cli(str(fixture))
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), report)

    def assert_fixture(self, code, report, **fields):
        fixture = {
            "method": "GET", "exists": True, "etag": '"rev1"',
            "if_match": None, "if_none_match": None,
        }
        fixture.update(fields)
        self.assert_raw(json.dumps(fixture).encode("utf-8"), code, report)

    def test_strong_match_precedes_weak_none_match(self):
        self.assert_fixture(
            1, stop(412, "if_match"), if_match='W/"rev1"', if_none_match='"rev1"'
        )
        self.assert_fixture(
            1, stop(304, "if_none_match"), if_match='"rev1"', if_none_match='W/"rev1"'
        )

    def test_weak_current_tag_only_matches_weak_comparison(self):
        self.assert_fixture(1, stop(412, "if_match"), etag='W/"rev1"', if_match='"rev1"')
        self.assert_fixture(1, stop(304, "if_none_match"), etag='W/"rev1"', if_none_match='"rev1"')

    def test_method_is_case_sensitive(self):
        self.assert_fixture(1, stop(304, "if_none_match"), method="HEAD", if_none_match="*")
        for method in ("PATCH", "get", "X+TRACE"):
            with self.subTest(method=method):
                self.assert_fixture(1, stop(412, "if_none_match"), method=method, if_none_match="*")

    def test_wildcards_use_existence_without_current_tag(self):
        self.assert_fixture(0, CONTINUE, etag=None, if_match="*")
        self.assert_fixture(1, stop(304, "if_none_match"), etag=None, if_none_match="*")
        self.assert_fixture(1, stop(412, "if_match"), exists=False, etag=None, if_match="*")
        self.assert_fixture(0, CONTINUE, exists=False, etag=None, if_none_match="*")
        self.assert_fixture(1, stop(412, "if_match"), etag=None, if_match='""')

    def test_list_quotes_preserve_commas_backslashes_and_obs_text(self):
        tag = '"a,b' + chr(92) + 'é"'
        self.assert_fixture(0, CONTINUE, etag="\t" + tag + " ", if_match=' , W/"other", ' + tag)
        self.assert_fixture(1, stop(304, "if_none_match"), etag=tag, if_none_match="W/" + tag)
        self.assert_fixture(1, stop(304, "if_none_match"), etag='""', if_none_match='""')

    def test_empty_list_members_and_cap(self):
        self.assert_fixture(1, stop(412, "if_match"), if_match="\t , ,")
        self.assert_fixture(0, CONTINUE, if_none_match="")
        self.assert_fixture(0, CONTINUE, if_match="," * 127 + '"rev1"')
        self.assert_fixture(2, INVALID, if_match="," * 128 + '"rev1"')

    def test_invalid_etag_and_list_syntax(self):
        for value in ('"a" "b"', '"a"\r\n', '"a b"', 'w/"a"', '"☃"', '*, "a"', 'W/ "a"', '"a' + chr(92) + '"b"'):
            with self.subTest(value=value):
                self.assert_fixture(2, INVALID, if_match=value)
        self.assert_fixture(2, INVALID, etag="*")
        self.assert_fixture(2, INVALID, etag='"a","b"')
        self.assert_fixture(2, INVALID, if_match='"other"', if_none_match="invalid")

    def test_strict_fixture_validation(self):
        for fields in ({"exists": 1}, {"exists": False}, {"method": "G É T"}, {"method": "X" * 65},
                       {"if_match": 7}, {"etag": '"x"' + " " * 8192}, {"extra": True}):
            with self.subTest(fields=tuple(fields)):
                self.assert_fixture(2, INVALID, **fields)
        for data in (b'{"method":"GET","method":"HEAD"}', b'{"exists":NaN}', b'\xef\xbb\xbf{}',
                     b'\xff', b'[1]', b'{} trailing', b' ' * (256 * 1024 + 1)):
            self.assert_raw(data, 2, INVALID)

    def test_non_file_and_unsupported_spellings(self):
        with tempfile.TemporaryDirectory() as directory:
            for value in (directory, str(Path(directory) / "missing"), "https://example.invalid/test",
                          "C:drive-relative", "CON.json", r"\\?\C:\device", r"\temp\..\Device\name"):
                with self.subTest(value=value):
                    result = self.run_cli(value)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(json.loads(result.stdout), INVALID)

    def test_help_and_missing_argument(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout), INVALID)

    def test_closed_output(self):
        read, write = os.pipe()
        os.close(read)
        try:
            result = subprocess.run(
                [sys.executable, "-I", str(SCRIPT), "--help"], stdout=write,
                stderr=subprocess.PIPE, timeout=15,
            )
        finally:
            os.close(write)
        self.assertEqual((result.returncode, result.stderr), (2, b""))
