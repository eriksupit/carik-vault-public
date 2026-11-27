#!/usr/bin/env python3
"""Canonical credential redaction for Interview Protocol persistence.

The public API returns redacted text plus detector-family identifiers only. It never
returns matched values or derivative metadata. Destination scanning is a separate
fail-closed post-condition and returns no bytes.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

REPLACEMENT = "[REDACTED-CREDENTIAL]"

DETECTOR_FAMILIES = (
    "pem-private-key",
    "authorization-bearer",
    "authorization-basic",
    "uri-userinfo",
    "provider-token-prefix",
    "environment-assignment",
    "cli-assignment",
    "structured-secret-field",
)

_FAILURE_IDENTIFIERS = frozenset(("redactor-failure", "scanner-failure"))
_PLACEHOLDER_IDENTIFIER = (
    r"(?:YOUR_|REPLACE_WITH_|INSERT_|EXAMPLE_)?"
    r"(?:USER(?:NAME)?|PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|ACCESS_KEY|"
    r"ACCESS_TOKEN|REFRESH_TOKEN|AUTH_TOKEN|PRIVATE_KEY|CLIENT_SECRET|CREDENTIALS?)"
    r"(?:_HERE)?"
)
_PLACEHOLDER_PATTERNS = (
    re.compile(rf"^\[{_PLACEHOLDER_IDENTIFIER}\]$"),
    re.compile(rf"^<{_PLACEHOLDER_IDENTIFIER}>$"),
    re.compile(rf"^\$\{{{_PLACEHOLDER_IDENTIFIER}\}}$"),
    re.compile(rf"^\{{\{{{_PLACEHOLDER_IDENTIFIER}\}}\}}$"),
)


class CredentialSafetyError(ValueError):
    """Bounded failure whose message is only a detector-family identifier."""

    __slots__ = ("family",)

    def __init__(self, family: str) -> None:
        allowed = set(DETECTOR_FAMILIES) | _FAILURE_IDENTIFIERS
        bounded_family = family if family in allowed else "scanner-failure"
        self.family = bounded_family
        super().__init__(bounded_family)


@dataclass(frozen=True)
class _Recognizer:
    family: str
    pattern: re.Pattern[str]
    replacement: str | Callable[[re.Match[str]], str]


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].strip()
    return value.strip()


def _is_placeholder(value: str) -> bool:
    candidate = _unquote(value)
    if candidate == REPLACEMENT:
        return True
    return any(pattern.fullmatch(candidate) for pattern in _PLACEHOLDER_PATTERNS)


def _userinfo_is_placeholder(value: str) -> bool:
    parts = value.split(":")
    return bool(parts) and all(_is_placeholder(part) for part in parts)


def _replace_value(match: re.Match[str]) -> str:
    value = match.group("value")
    if _is_placeholder(value):
        return match.group(0)
    return f"{match.group('prefix')}{REPLACEMENT}"


def _replace_environment_value(match: re.Match[str]) -> str:
    name = match.group("name").lower()
    if not any(
        name == suffix or name.endswith(f"_{suffix}")
        for suffix in _SENSITIVE_ASSIGNMENT_SUFFIXES
    ):
        return match.group(0)
    return _replace_value(match)


def _replace_structured_value(match: re.Match[str]) -> str:
    value = match.group("value")
    if _is_placeholder(value):
        return match.group(0)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return f"{match.group('prefix')}{value[0]}{REPLACEMENT}{value[0]}"
    return f"{match.group('prefix')}{REPLACEMENT}"


def _replace_uri_userinfo(match: re.Match[str]) -> str:
    userinfo = match.group("userinfo")
    if _userinfo_is_placeholder(userinfo):
        return match.group(0)
    return f"{match.group('scheme')}{REPLACEMENT}@"


_SENSITIVE_FIELD_PATTERN = (
    r"(?:password|passwd|secret[-_]?access[-_]?key|client[-_]?secret|secret|"
    r"api[-_]?key|access[-_]?key|access[-_]?token|refresh[-_]?token|"
    r"auth[-_]?token|token|private[-_]?key|credentials?)"
)
_MACHINE_STRUCTURED_FIELD_PATTERN = (
    r"(?:secret[-_]access[-_]key|client[-_]secret|api[-_]key|access[-_]key|"
    r"access[-_]token|refresh[-_]token|auth[-_]token|private[-_]key)"
)
_SENSITIVE_ASSIGNMENT_SUFFIXES = (
    "password",
    "passwd",
    "secret_access_key",
    "client_secret",
    "secret",
    "api_key",
    "access_key",
    "access_token",
    "refresh_token",
    "auth_token",
    "token",
    "private_key",
    "credential",
    "credentials",
)
_VALUE = r'(?P<value>"[^"\r\n]*"|\'[^\'\r\n]*\'|[^\s#;,}]+)'

_RECOGNIZERS = (
    _Recognizer(
        "pem-private-key",
        re.compile(
            r"-----BEGIN (?P<pem_label>(?:[A-Z0-9]+[ \t]+)*PRIVATE KEY)-----"
            r".*?"
            r"-----END (?P=pem_label)-----",
            re.DOTALL,
        ),
        REPLACEMENT,
    ),
    _Recognizer(
        "authorization-bearer",
        re.compile(
            r"\b(?P<prefix>(?:proxy-)?authorization[ \t]*:[ \t]*bearer[ \t]+)"
            r"(?P<value>[^\s,;]+)",
            re.IGNORECASE,
        ),
        _replace_value,
    ),
    _Recognizer(
        "authorization-basic",
        re.compile(
            r"\b(?P<prefix>(?:proxy-)?authorization[ \t]*:[ \t]*basic[ \t]+)"
            r"(?P<value>[^\s,;]+)",
            re.IGNORECASE,
        ),
        _replace_value,
    ),
    _Recognizer(
        "uri-userinfo",
        re.compile(
            r"\b(?P<scheme>[A-Za-z][A-Za-z0-9+.-]{1,31}://)"
            r"(?P<userinfo>[^\s/@]+)@"
        ),
        _replace_uri_userinfo,
    ),
    _Recognizer(
        "provider-token-prefix",
        re.compile(
            r"(?<![A-Za-z0-9_-])(?:"
            r"github_pat_[A-Za-z0-9_]{20,255}"
            r"|gh[pousr]_[A-Za-z0-9]{20,255}"
            r"|sk-ant-(?:api[0-9]{2}-)?[A-Za-z0-9_-]{20,255}"
            r"|sk-proj-[A-Za-z0-9_-]{20,255}"
            r"|sk-[A-Za-z0-9_-]{20,255}"
            r"|xox[baprs]-[A-Za-z0-9-]{16,255}"
            r"|glpat-[A-Za-z0-9_-]{20,255}"
            r"|npm_[A-Za-z0-9]{20,255}"
            r"|AIza[A-Za-z0-9_-]{35}"
            r"|(?:AKIA|ASIA)[A-Z0-9]{16}"
            r"|(?:sk|rk)_live_[A-Za-z0-9]{16,255}"
            r")(?![A-Za-z0-9_-])"
        ),
        REPLACEMENT,
    ),
    _Recognizer(
        "environment-assignment",
        re.compile(
            rf"(?<![A-Za-z0-9_-])(?P<prefix>(?:export[ \t]+)?"
            rf"(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*=[ \t]*){_VALUE}",
            re.IGNORECASE,
        ),
        _replace_environment_value,
    ),
    _Recognizer(
        "cli-assignment",
        re.compile(
            rf"(?P<prefix>--(?:password|passwd|secret|token|api[-_]key|access[-_]key|"
            rf"access[-_]token|refresh[-_]token|auth[-_]token|private[-_]key|"
            rf"client[-_]secret|credentials?)"
            rf"(?:[ \t]*=[ \t]*|[ \t]+)){_VALUE}",
            re.IGNORECASE,
        ),
        _replace_value,
    ),
    _Recognizer(
        "structured-secret-field",
        re.compile(
            rf"(?P<prefix>(?:"
            rf"(?:^[ \t]*|[{{,][ \t]*)[\"']{_SENSITIVE_FIELD_PATTERN}[\"']"
            rf"[ \t]*:[ \t]*"
            rf"|[{{,][ \t]*{_SENSITIVE_FIELD_PATTERN}[ \t]*:[ \t]*"
            rf"|^[ \t]*{_MACHINE_STRUCTURED_FIELD_PATTERN}[ \t]*:[ \t]*"
            rf"|^---[ \t]*\r?\n[ \t]*{_SENSITIVE_FIELD_PATTERN}[ \t]*:[ \t]*"
            rf")){_VALUE}",
            re.IGNORECASE | re.MULTILINE,
        ),
        _replace_structured_value,
    ),
)


def _redact_ordered(text: str) -> tuple[str, tuple[str, ...]]:
    rendered = text
    fired: list[str] = []
    for recognizer in _RECOGNIZERS:
        updated = recognizer.pattern.sub(recognizer.replacement, rendered)
        if updated != rendered:
            fired.append(recognizer.family)
            rendered = updated
    return rendered, tuple(fired)


def redact_text(text: str) -> tuple[str, tuple[str, ...]]:
    """Replace supported credentials before any limit check or persistence."""

    try:
        if not isinstance(text, str):
            raise TypeError
        return _redact_ordered(text)
    except Exception:
        raise CredentialSafetyError("redactor-failure") from None


def assert_destination_safe(destination: bytes) -> None:
    """Fail closed when UTF-8 destination bytes contain a supported credential."""

    try:
        if not isinstance(destination, bytes):
            raise TypeError
        text = destination.decode("utf-8", errors="strict")
        _, families = _redact_ordered(text)
    except Exception:
        raise CredentialSafetyError("scanner-failure") from None

    if families:
        raise CredentialSafetyError(families[0]) from None
