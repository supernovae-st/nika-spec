"""Publication-state proof is not an HTTP-success or artifact-integrity claim."""
import copy
from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("timeline_verify", Path(__file__).with_name("verify.py"))
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ReleaseEvidenceTests(unittest.TestCase):
    entry = {"evidence": {"class": "github-release", "repo": "supernovae-st/nika", "tag": "v0.116.2"}}
    published = {"tag_name": "v0.116.2", "draft": False, "published_at": "2026-08-31T12:00:00Z"}

    def check_payload(self, payload):
        with patch.object(VERIFY, "http_ok", return_value=True), patch.object(VERIFY, "fetch_json", return_value=payload):
            return VERIFY.check(self.entry, False)

    def test_published_release_at_exact_tag_is_proved(self):
        verdict, detail = self.check_payload(self.published)
        self.assertEqual(verdict, "PROVED")
        self.assertIn("2026-08-31", detail)

    def test_successful_http_response_is_not_publication_evidence(self):
        for payload in [None, [], {}, {"message": "unknown"}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.check_payload(payload)[0], "FAILED")

    def test_wrong_tag_draft_and_missing_publication_refuse(self):
        mutations = [{"tag_name": "v0.118.3"}, {"draft": True}, {"draft": "false"},
                     {"published_at": None}, {"published_at": ""},
                     {"published_at": "2026-02-30T00:00:00Z"}, {"published_at": "not-a-date"}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                payload = {**self.published, **mutation}
                self.assertEqual(self.check_payload(payload)[0], "FAILED")
        for missing in self.published:
            with self.subTest(missing=missing):
                payload = copy.deepcopy(self.published)
                del payload[missing]
                self.assertEqual(self.check_payload(payload)[0], "FAILED")

    def test_unreachable_release_is_failed_not_proved(self):
        with patch.object(VERIFY, "http_ok", return_value=True), patch.object(VERIFY, "fetch_json", side_effect=OSError("unreachable")):
            self.assertEqual(VERIFY.check(self.entry, False)[0], "FAILED")

    def test_offline_is_never_publication_proof(self):
        with patch.object(VERIFY, "fetch_json", side_effect=AssertionError("network forbidden")):
            self.assertEqual(VERIFY.check(self.entry, True), ("SKIPPED-OFFLINE", "github-release"))

    def test_final_summary_does_not_promote_skipped_offline_claims(self):
        doc = {"evidence_classes": {"github-release": "published state"},
               "entries": [{"id": "released-engine", **self.entry}]}
        for offline in [False, True]:
            output = io.StringIO()
            with self.subTest(offline=offline), redirect_stdout(output), \
                 patch.object(VERIFY.yaml, "safe_load", return_value=doc), \
                 patch.object(VERIFY, "fetch_json", return_value=self.published):
                self.assertEqual(VERIFY.main(["--offline"] if offline else []), 0)
            self.assertEqual("every provable claim holds" in output.getvalue(), not offline)
            self.assertEqual("external claims remain unproved" in output.getvalue(), offline)


class ApiAuthorityTests(unittest.TestCase):
    def test_token_is_only_sent_to_the_exact_https_github_api_origin(self):
        for url, authorized in [("https://api.github.com/repos/x/y", True),
                                ("https://crates.io/api/v1/crates/nika", False),
                                ("https://api.github.com.evil.invalid/x", False),
                                ("http://api.github.com/x", False)]:
            with self.subTest(url=url), patch.dict("os.environ", {"GH_TOKEN": "synthetic-read-token"}):
                opener = unittest.mock.MagicMock()
                opener.open.return_value.__enter__.return_value = io.BytesIO(b'{}')
                with patch.object(VERIFY.urllib.request, "build_opener", return_value=opener), \
                     patch.object(VERIFY.urllib.request, "urlopen", side_effect=AssertionError("network forbidden")):
                    VERIFY.fetch_json(url)
                request = opener.open.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"),
                                 "Bearer synthetic-read-token" if authorized else None)

    def test_authenticated_redirects_stay_on_the_github_api_origin(self):
        request = urllib.request.Request("https://api.github.com/repos/old/name",
                                         headers={"Authorization": "Bearer synthetic-read-token"})
        handler = VERIFY.ApiRedirectHandler()
        result = handler.redirect_request(request, None, 301, "moved", {},
                                          "https://api.github.com/repos/new/name")
        self.assertEqual(result.get_header("Authorization"), "Bearer synthetic-read-token")
        for target in ["https://example.invalid/leak", "http://api.github.com/leak",
                       "https://api.github.com.evil.invalid/leak"]:
            with self.subTest(target=target), self.assertRaises(urllib.error.URLError):
                handler.redirect_request(request, None, 302, "moved", {}, target)


if __name__ == "__main__":
    unittest.main()
