#!/usr/bin/env python3
"""Standard-library local HTML preview engine for Markdown and JSON Canvas artifacts.

Renders .md and .canvas files to .agents/previews/<target_stem>.html using pure
Python standard library modules with self-bootstrapping CSS and process safety.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
import webbrowser

MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB

DEFAULT_CSS = """:root {
  --bg-color: #ffffff;
  --text-color: #1a1a1a;
  --link-color: #0969da;
  --border-color: #d0d7de;
  --code-bg: #f6f8fa;
  --table-stripe: #f6f8fa;
  --callout-bg: #f0f7ff;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #0d1117;
    --text-color: #c9d1d9;
    --link-color: #58a6ff;
    --border-color: #30363d;
    --code-bg: #161b22;
    --table-stripe: #161b22;
    --callout-bg: #1f242c;
  }
}

body {
  font-family: var(--font-body);
  background-color: var(--bg-color);
  color: var(--text-color);
  line-height: 1.6;
  max-width: 860px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

h1, h2, h3, h4, h5, h6 {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  line-height: 1.25;
}

a {
  color: var(--link-color);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

pre, code {
  font-family: var(--font-mono);
  background-color: var(--code-bg);
  border-radius: 4px;
}

code {
  padding: 0.2em 0.4em;
  font-size: 85%;
}

pre {
  padding: 1rem;
  overflow-x: auto;
}

pre code {
  padding: 0;
  font-size: 100%;
}

.table-container {
  overflow-x: auto;
  margin: 1rem 0;
}

table {
  border-collapse: collapse;
  width: 100%;
}

th, td {
  border: 1px solid var(--border-color);
  padding: 0.5rem 0.75rem;
  text-align: left;
}

tr:nth-child(even) {
  background-color: var(--table-stripe);
}

blockquote {
  margin: 1rem 0;
  padding: 0.5rem 1rem;
  border-left: 4px solid var(--border-color);
  background-color: var(--callout-bg);
}

.canvas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}

.canvas-card {
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 1rem;
  background-color: var(--code-bg);
}
"""


def ensure_preview_assets(previews_dir: Path) -> Path:
    previews_dir.mkdir(parents=True, exist_ok=True)
    css_file = previews_dir / "style.css"
    if not css_file.is_file():
        css_file.write_text(DEFAULT_CSS, encoding="utf-8")
    return css_file


def render_markdown_inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r'<a href="\1.html">\2</a>', text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r'<a href="\1.html">\1</a>', text)
    return text


def render_markdown(content: str) -> str:
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    lines = content.splitlines()
    html_out: list[str] = []
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    in_table = False
    table_lines: list[str] = []

    def flush_table():
        nonlocal in_table, table_lines
        if not table_lines:
            return
        html_out.append('<div class="table-container"><table>')
        for i, row in enumerate(table_lines):
            cells = [c.strip() for c in row.strip("|").split("|")]
            if i == 1 and all(set(c).issubset({"-", ":", " "}) for c in cells):
                continue
            tag = "th" if i == 0 else "td"
            rendered_cells = "".join(f"<{tag}>{render_markdown_inline(c)}</{tag}>" for c in cells)
            html_out.append(f"<tr>{rendered_cells}</tr>")
        html_out.append("</table></div>")
        table_lines = []
        in_table = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                joined = "\n".join(code_lines)
                escaped_code = html.escape(joined)
                lang_cls = f' class="language-{code_lang}"' if code_lang else ""
                html_out.append(f'<pre><code{lang_cls}>{escaped_code}</code></pre>')
                code_lines = []
                in_code_block = False
            else:
                if in_table:
                    flush_table()
                in_code_block = True
                code_lang = stripped[3:].strip()
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        elif in_table:
            flush_table()

        if not stripped:
            continue

        m_h = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m_h:
            level = len(m_h.group(1))
            header_text = render_markdown_inline(m_h.group(2))
            html_out.append(f"<h{level}>{header_text}</h{level}>")
            continue

        if stripped.startswith(">"):
            quote_text = render_markdown_inline(stripped.lstrip("> ").strip())
            html_out.append(f"<blockquote><p>{quote_text}</p></blockquote>")
            continue

        if stripped.startswith(("- ", "* ", "+ ")):
            item_text = render_markdown_inline(stripped[2:])
            html_out.append(f"<ul><li>{item_text}</li></ul>")
            continue

        p_text = render_markdown_inline(stripped)
        html_out.append(f"<p>{p_text}</p>")

    if in_table:
        flush_table()
    if in_code_block:
        joined = "\n".join(code_lines)
        escaped_code = html.escape(joined)
        html_out.append(f"<pre><code>{escaped_code}</code></pre>")

    return "\n".join(html_out)


def render_canvas(content: str) -> str:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        return f'<p class="error">Invalid JSON Canvas: {html.escape(str(e))}</p>'

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return "<p>Empty canvas.</p>"

    cards_html: list[str] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type", "unknown")
        raw_text = node.get("text", "")
        if node_type == "file":
            file_name = html.escape(str(node.get("file", "")))
            card_body = f"<strong>File Node:</strong> {file_name}"
        else:
            card_body = render_markdown_inline(str(raw_text))

        cards_html.append(f'<div class="canvas-card">{card_body}</div>')

    return f'<div class="canvas-grid">{"".join(cards_html)}</div>'


def render_json(content: str) -> str:
    try:
        parsed = json.loads(content)
        formatted = json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        formatted = content
    escaped = html.escape(formatted)
    return f'<pre><code class="language-json">{escaped}</code></pre>'


def render_html_passthrough(content: str) -> str:
    m_body = re.search(r"<body[^>]*>(.*?)</body>", content, re.DOTALL | re.IGNORECASE)
    if m_body:
        return m_body.group(1).strip()
    return content

def build_html_document(title: str, body_html: str, relative_css: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{relative_css}">
</head>
<body>
  <article>
    {body_html}
  </article>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile Markdown / Canvas / JSON / HTML to HTML preview.")
    parser.add_argument("target", help="Path to source artifact file")
    parser.add_argument("--vault", help="Vault root directory", default=None)
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    parser.add_argument("--open", action="store_true", help="Open in default browser")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    if not target_path.is_file():
        err = f"Error: Target file not found: {target_path}\n"
        sys.stderr.write(err)
        if args.json:
            sys.stdout.write(json.dumps({"status": "error", "error": err.strip()}) + "\n")
        return 1

    try:
        size = target_path.stat().st_size
        if size > MAX_FILE_SIZE_BYTES:
            msg = f"Advisory: File exceeds 2MB limit ({size} bytes), skipping HTML compilation.\n"
            sys.stderr.write(msg)
            if args.json:
                sys.stdout.write(json.dumps({"status": "skipped", "message": msg.strip()}) + "\n")
            return 0
    except OSError as e:
        err = f"Error reading file stat: {e}\n"
        sys.stderr.write(err)
        if args.json:
            sys.stdout.write(json.dumps({"status": "error", "error": err.strip()}) + "\n")
        return 1

    if args.vault:
        vault_root = Path(args.vault).resolve()
    else:
        vault_root = Path(__file__).resolve().parent.parent

    previews_dir = vault_root / ".agents" / "previews"
    ensure_preview_assets(previews_dir)

    try:
        content = target_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        err = f"Error reading {target_path}: {e}\n"
        sys.stderr.write(err)
        if args.json:
            sys.stdout.write(json.dumps({"status": "error", "error": err.strip()}) + "\n")
        return 1

    ext = target_path.suffix.lower()
    if ext == ".canvas":
        body_html = render_canvas(content)
    elif ext == ".json":
        body_html = render_json(content)
    elif ext in (".html", ".htm"):
        body_html = render_html_passthrough(content)
    else:
        body_html = render_markdown(content)

    out_file = previews_dir / f"{target_path.stem}.html"
    relative_css = "style.css"
    full_html = build_html_document(target_path.name, body_html, relative_css)

    try:
        out_file.write_text(full_html, encoding="utf-8")
    except OSError as e:
        err = f"Error writing preview to {out_file}: {e}\n"
        sys.stderr.write(err)
        if args.json:
            sys.stdout.write(json.dumps({"status": "error", "error": err.strip()}) + "\n")
        return 1

    abs_uri = out_file.as_uri()
    abs_path = str(out_file.resolve())

    if args.open:
        webbrowser.open(abs_uri)

    if args.json:
        sys.stdout.write(json.dumps({
            "status": "ok",
            "file_uri": abs_uri,
            "html_path": abs_path,
            "target": str(target_path)
        }, indent=2) + "\n")
    else:
        sys.stdout.write(f"{abs_uri}\n{abs_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
