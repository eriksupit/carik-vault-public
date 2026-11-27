#!/usr/bin/env python3
"""Behavior tests for canonical Interview Protocol credential redaction."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOKS_DIR = Path(__file__).resolve().parent
REDACTOR_PATH = HOOKS_DIR / "interview_credential_redactor.py"
REDACTOR_SPEC = importlib.util.spec_from_file_location(
    "interview_credential_redactor", REDACTOR_PATH
)
if REDACTOR_SPEC is None or REDACTOR_SPEC.loader is None:
    raise RuntimeError("canonical redactor module is unavailable")
redactor = importlib.util.module_from_spec(REDACTOR_SPEC)
sys.modules[REDACTOR_SPEC.name] = redactor
REDACTOR_SPEC.loader.exec_module(redactor)


class InterviewCredentialRedactorTest(unittest.TestCase):
    def assert_redacted(self, source: str, family: str, raw_value: str) -> str:
        rendered, families = redactor.redact_text(source)
        self.assertNotIn(raw_value, rendered)
        self.assertIn(redactor.REPLACEMENT, rendered)
        self.assertIn(family, families)
        return rendered

    def test_redacts_multiline_pem_private_keys(self) -> None:
        body = "ZmFrZS1wcml2YXRlLWtleS1jYW5hcnk="
        source = (
            "before\n-----BEGIN RSA PRIVATE KEY-----\n"
            f"{body}\n"
            "-----END RSA PRIVATE KEY-----\nafter"
        )
        rendered = self.assert_redacted(source, "pem-private-key", body)
        self.assertEqual(rendered, f"before\n{redactor.REPLACEMENT}\nafter")

    def test_redacts_bearer_and_basic_authorization(self) -> None:
        fixtures = (
            (
                "Authorization: Bearer bearer.canary.value",
                "authorization-bearer",
                "bearer.canary.value",
            ),
            (
                "Proxy-Authorization: Basic dXNlcjpjYW5hcnktcGFzcw==",
                "authorization-basic",
                "dXNlcjpjYW5hcnktcGFzcw==",
            ),
        )
        for source, family, raw_value in fixtures:
            with self.subTest(family=family):
                rendered = self.assert_redacted(source, family, raw_value)
                self.assertTrue(rendered.endswith(redactor.REPLACEMENT))

    def test_redacts_uri_user_information(self) -> None:
        raw_value = "operator:uri-canary-pass"
        source = f"postgresql://{raw_value}@db.example.test:5432/appdb"
        rendered = self.assert_redacted(source, "uri-userinfo", raw_value)
        self.assertEqual(
            rendered,
            f"postgresql://{redactor.REPLACEMENT}@db.example.test:5432/appdb",
        )

    def test_redacts_known_provider_token_prefixes(self) -> None:
        tokens = (
            "ghp_abcdefghijklmnopqrstuvwxyz123456",
            "github_pat_11_abcdefghijklmnopqrstuvwxyz123456",
            "sk-proj-abcdefghijklmnopqrstuvwxyz123456",
            "sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456",
            "xoxb-1234567890-abcdefghijklmnop",
            "glpat-abcdefghijklmnopqrstuvwxyz1234",
            "npm_abcdefghijklmnopqrstuvwxyz123456",
            "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz0123456",
            "AKIAABCDEFGHIJKLMNOP",
            "sk_live_abcdefghijklmnopqrstuvwxyz",
        )
        for token in tokens:
            with self.subTest(prefix=token.split("_")[0].split("-")[0]):
                rendered = self.assert_redacted(token, "provider-token-prefix", token)
                self.assertEqual(rendered, redactor.REPLACEMENT)

    def test_redacts_environment_assignments(self) -> None:
        fixtures = (
            ("API_TOKEN=environment-canary-token", "environment-canary-token"),
            (
                'export CLIENT_SECRET="environment canary secret"',
                "environment canary secret",
            ),
            (
                "DATABASE_PASSWORD='environment-canary-password'",
                "environment-canary-password",
            ),
        )
        for source, raw_value in fixtures:
            with self.subTest(source=source.split("=")[0]):
                rendered = self.assert_redacted(
                    source, "environment-assignment", raw_value
                )
                self.assertTrue(rendered.endswith(redactor.REPLACEMENT))

    def test_redacts_exact_and_serialized_environment_assignments(self) -> None:
        fixtures = (
            ("PASSWORD=exact-password-canary", "exact-password-canary"),
            ("TOKEN=exact-token-canary", "exact-token-canary"),
            ("API_KEY=exact-api-key-canary", "exact-api-key-canary"),
            ("User: API_TOKEN=user-content-canary", "user-content-canary"),
            ("Agent: TOKEN=agent-content-canary", "agent-content-canary"),
        )
        for source, raw_value in fixtures:
            with self.subTest(source=source.split("=")[0]):
                self.assert_redacted(source, "environment-assignment", raw_value)
                with self.assertRaises(redactor.CredentialSafetyError) as caught:
                    redactor.assert_destination_safe(source.encode("utf-8"))
                self.assertEqual(str(caught.exception), "environment-assignment")

    def test_redacts_cli_assignments(self) -> None:
        fixtures = (
            ("tool --api-key=cli-canary-key run", "cli-canary-key"),
            ('tool --client-secret "cli canary secret" run', "cli canary secret"),
            ("tool --password cli-canary-password", "cli-canary-password"),
        )
        for source, raw_value in fixtures:
            with self.subTest(raw_value=raw_value):
                self.assert_redacted(source, "cli-assignment", raw_value)

    def test_redacts_high_confidence_structured_secret_fields(self) -> None:
        fixtures = (
            (
                '{"password": "json-canary-password", "safe": true}',
                "json-canary-password",
            ),
            ("client_secret: yaml-canary-secret", "yaml-canary-secret"),
            ("  access_token: 'yaml canary token'", "yaml canary token"),
        )
        for source, raw_value in fixtures:
            with self.subTest(raw_value=raw_value):
                self.assert_redacted(source, "structured-secret-field", raw_value)

    def test_false_positive_fixtures_remain_byte_identical(self) -> None:
        fixtures = (
            "Kata sandi dalam cerita itu hanya metafora, bukan data akses.",
            "MIRA\nAku tidak punya rahasia untuk kamu.\n\nBUDI\nKalau begitu, kita mulai.",
            "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
            "SRC-2026-0042",
            "INT. RUANG KERJA - MALAM",
            "[YOUR_API_KEY] [TOKEN] <PASSWORD> ${CLIENT_SECRET} {{ACCESS_TOKEN}}",
            "password is a recurring motif in this screenplay",
            "https://example.test/@public-profile",
        )
        for source in fixtures:
            with self.subTest(source=source[:32]):
                rendered, families = redactor.redact_text(source)
                self.assertEqual(rendered, source)
                self.assertEqual(families, ())

    def test_fountain_sensitive_label_is_not_structured_secret_data(self) -> None:
        source = "MIRA\nPassword: mawar merah.\n\nBUDI\nItu bukan jawabannya."
        rendered, families = redactor.redact_text(source)
        self.assertEqual(rendered, source)
        self.assertEqual(families, ())
        self.assertIsNone(redactor.assert_destination_safe(source.encode("utf-8")))

    def test_bracketed_placeholders_in_secret_positions_remain_unchanged(self) -> None:
        fixtures = (
            "API_TOKEN=[YOUR_API_KEY]",
            "tool --password <PASSWORD>",
            '"client_secret": "${CLIENT_SECRET}"',
            "Authorization: Bearer [TOKEN]",
            "postgresql://[USER]:[PASSWORD]@db.example.test/appdb",
        )
        for source in fixtures:
            with self.subTest(source=source):
                rendered, families = redactor.redact_text(source)
                self.assertEqual(rendered, source)
                self.assertEqual(families, ())

    def test_bracket_delimited_real_credentials_are_not_placeholders(self) -> None:
        fixtures = (
            (
                "DB_PASSWORD=[real-environment-secret]",
                "real-environment-secret",
                "environment-assignment",
            ),
            (
                "tool --password [real-cli-secret]",
                "real-cli-secret",
                "cli-assignment",
            ),
            (
                '{"client_secret":"[real-structured-secret]"}',
                "real-structured-secret",
                "structured-secret-field",
            ),
        )
        for source, raw_value, family in fixtures:
            with self.subTest(family=family):
                self.assert_redacted(source, family, raw_value)
                with self.assertRaises(redactor.CredentialSafetyError) as caught:
                    redactor.assert_destination_safe(source.encode("utf-8"))
                self.assertEqual(str(caught.exception), family)

    def test_redaction_is_idempotent(self) -> None:
        source = "API_TOKEN=idempotence-canary-token"
        once, first_families = redactor.redact_text(source)
        twice, second_families = redactor.redact_text(once)
        self.assertEqual(twice, once)
        self.assertEqual(first_families, ("environment-assignment",))
        self.assertEqual(second_families, ())

    def test_api_leaks_no_raw_value_hash_length_or_diagnostic(self) -> None:
        raw_value = "opaque-canary-value-with-unique-length-xxxxxxxxxxxxxxxxx"
        source = f"API_TOKEN={raw_value}"
        result = redactor.redact_text(source)
        serialized_result = repr(result)
        self.assertEqual(len(result), 2)
        self.assertNotIn(raw_value, serialized_result)
        self.assertNotIn(
            hashlib.sha256(raw_value.encode("utf-8")).hexdigest(), serialized_result
        )
        self.assertNotIn(str(len(raw_value)), serialized_result)
        self.assertEqual(result[1], ("environment-assignment",))

        with self.assertRaises(redactor.CredentialSafetyError) as caught:
            redactor.assert_destination_safe(source.encode("utf-8"))
        self.assertEqual(str(caught.exception), "environment-assignment")
        self.assertNotIn(raw_value, str(caught.exception))

    def test_redaction_occurs_before_content_length_validation(self) -> None:
        raw_value = "x" * 400
        source = f"API_TOKEN={raw_value}"
        self.assertGreater(len(source), 160)
        rendered, families = redactor.redact_text(source)
        self.assertLessEqual(len(rendered), 160)
        self.assertEqual(families, ("environment-assignment",))

    def test_destination_scanner_succeeds_silently_for_redacted_bytes(self) -> None:
        rendered, _ = redactor.redact_text("API_TOKEN=scanner-canary-token")
        self.assertIsNone(redactor.assert_destination_safe(rendered.encode("utf-8")))

    def test_destination_scanner_fails_closed_for_each_supported_family(self) -> None:
        fixtures = (
            (
                "pem-private-key",
                "-----BEGIN PRIVATE KEY-----\nY2FuYXJ5\n-----END PRIVATE KEY-----",
            ),
            ("authorization-bearer", "Authorization: Bearer scanner.canary.token"),
            ("authorization-basic", "Authorization: Basic c2Nhbm5lcjpjYW5hcnk="),
            ("uri-userinfo", "https://user:scanner-canary@host.test/path"),
            ("provider-token-prefix", "ghp_abcdefghijklmnopqrstuvwxyz123456"),
            ("environment-assignment", "API_TOKEN=scanner-canary-token"),
            ("cli-assignment", "tool --password scanner-canary-password"),
            ("structured-secret-field", '"password": "scanner-canary-password"'),
        )
        for expected_family, source in fixtures:
            with self.subTest(family=expected_family):
                with self.assertRaises(redactor.CredentialSafetyError) as caught:
                    redactor.assert_destination_safe(source.encode("utf-8"))
                self.assertEqual(str(caught.exception), expected_family)

    def test_scanner_internal_failure_returns_no_destination_bytes_or_raw_diagnostic(
        self,
    ) -> None:
        internal_diagnostic = "internal scanner leaked scanner-canary-value"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
            mock.patch.object(
                redactor,
                "_redact_ordered",
                side_effect=RuntimeError(internal_diagnostic),
            ),
            self.assertRaises(redactor.CredentialSafetyError) as caught,
        ):
            redactor.assert_destination_safe(b"ordinary destination bytes")
        self.assertEqual(caught.exception.args, ("scanner-failure",))
        self.assertNotIn(internal_diagnostic, str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_redactor_internal_failure_exposes_only_bounded_family_identifier(
        self,
    ) -> None:
        internal_diagnostic = "redactor encountered raw-canary-value"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
            mock.patch.object(
                redactor,
                "_redact_ordered",
                side_effect=RuntimeError(internal_diagnostic),
            ),
            self.assertRaises(redactor.CredentialSafetyError) as caught,
        ):
            redactor.redact_text("ordinary text")
        self.assertEqual(caught.exception.args, ("redactor-failure",))
        self.assertNotIn(internal_diagnostic, str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_invalid_utf8_destination_fails_closed_without_echoing_bytes(self) -> None:
        with self.assertRaises(redactor.CredentialSafetyError) as caught:
            redactor.assert_destination_safe(b"\xff\xfe\xfd")
        self.assertEqual(str(caught.exception), "scanner-failure")

    def test_repository_destination_canary_writes_only_redacted_bytes(self) -> None:
        canary = "repository-destination-canary-value"
        source = f"API_TOKEN={canary}\nAgent: safe summary"
        rendered, families = redactor.redact_text(source)
        self.assertEqual(families, ("environment-assignment",))
        redactor.assert_destination_safe(rendered.encode("utf-8"))

        with tempfile.TemporaryDirectory(
            prefix="redactor-canary-", dir=HOOKS_DIR
        ) as raw_dir:
            root = Path(raw_dir)
            (root / "nested").mkdir()
            (root / "session.txt").write_bytes(rendered.encode("utf-8"))
            (root / "nested" / "state.json").write_bytes(b'{"status":"safe"}\n')
            for path in root.rglob("*"):
                if path.is_file():
                    self.assertNotIn(canary.encode("utf-8"), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
