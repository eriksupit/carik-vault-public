#!/usr/bin/env python3
"""Optional fail-open browser helper for the browsing skill.

Uses Python standard library only (zero external dependencies, zero installs):
- open <url>: open an http/https URL in the user's default desktop browser.
- cdp-tabs [--port 9222]: inspect open tabs if the user explicitly enabled
  local Chrome DevTools Protocol remote debugging on 127.0.0.1.
- fetch-text <url>: fetch clean visible text from a public http/https page.
"""
from __future__ import annotations

import argparse
import html.parser
import json
import platform
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def _validate_http_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Hanya URL http:// atau https:// yang diizinkan: {url!r}")
    return url.strip()


class _TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self.title_parts: list[str] = []
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        elif lower == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif lower == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        else:
            self.chunks.append(text)


def cmd_open(url: str) -> int:
    safe_url = _validate_http_url(url)
    system = platform.system().lower()
    if system == "darwin":
        cmd = ["open", safe_url]
    elif system == "windows":
        cmd = ["cmd", "/c", "start", "", safe_url]
    else:
        cmd = ["xdg-open", safe_url]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(json.dumps({"status": "ok", "action": "open", "url": safe_url}, ensure_ascii=False))
        return 0
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "action": "open",
                    "url": safe_url,
                    "reason": str(exc),
                    "fallback": "Gunakan jalur kolaboratif manual: minta pemilik membuka URL di browser komputernya.",
                },
                ensure_ascii=False,
            )
        )
        return 0


def cmd_cdp_tabs(port: int) -> int:
    if not (1024 <= port <= 65535):
        raise ValueError(f"Port tidak valid: {port}")
    endpoint = f"http://127.0.0.1:{port}/json/list"
    req = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        items = json.loads(raw)
        tabs = []
        for item in items:
            if item.get("type") != "page":
                continue
            tab_url = str(item.get("url", ""))
            if not (tab_url.startswith("http://") or tab_url.startswith("https://")):
                continue
            tabs.append({"title": str(item.get("title", "")), "url": tab_url})
        print(json.dumps({"status": "ok", "port": port, "tab_count": len(tabs), "tabs": tabs}, ensure_ascii=False))
        return 0
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "port": port,
                    "reason": str(exc),
                    "fallback": "Port CDP lokal tidak aktif. Lanjutkan dengan jalur kolaboratif manual tanpa mengubah pengaturan browser secara paksa.",
                },
                ensure_ascii=False,
            )
        )
        return 0


def cmd_fetch_text(url: str, max_chars: int) -> int:
    safe_url = _validate_http_url(url)
    req = urllib.request.Request(
        safe_url,
        headers={"User-Agent": "CarikVault-Browsing/1.0 (+https://carik.local)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(2_000_000).decode("utf-8", errors="replace")
        parser = _TextExtractor()
        parser.feed(body)
        title = " ".join(parser.title_parts).strip()
        text = "\n".join(parser.chunks)
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]
        print(
            json.dumps(
                {
                    "status": "ok",
                    "url": safe_url,
                    "content_type": content_type,
                    "title": title,
                    "truncated": truncated,
                    "text": text,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "url": safe_url,
                    "reason": str(exc),
                    "fallback": "Halaman tidak dapat diambil langsung. Gunakan browser bawaan harness atau jalur kolaboratif manual.",
                },
                ensure_ascii=False,
            )
        )
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-open browser helper for browsing skill.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_open = sub.add_parser("open", help="Open an http/https URL in the user's default browser.")
    p_open.add_argument("url")

    p_cdp = sub.add_parser("cdp-tabs", help="List open http/https tabs via local CDP if enabled by user.")
    p_cdp.add_argument("--port", type=int, default=9222)

    p_fetch = sub.add_parser("fetch-text", help="Fetch visible text from a public http/https URL.")
    p_fetch.add_argument("url")
    p_fetch.add_argument("--max-chars", type=int, default=12000)

    args = parser.parse_args(argv)
    try:
        if args.command == "open":
            return cmd_open(args.url)
        if args.command == "cdp-tabs":
            return cmd_cdp_tabs(args.port)
        if args.command == "fetch-text":
            return cmd_fetch_text(args.url, args.max_chars)
    except ValueError as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
