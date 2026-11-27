#!/usr/bin/env python3
"""Regression tests for the artifact-research-gate PreToolUse hook."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("artifact-research-gate.py")

REGISTRY = """# Raw KB Source Registry

## Entry contract

```yaml
source_id:
local_path:
```

### sample

```yaml
source_id: 2026-07-02-sample-memoir-ocr-teks
local_path: raw-kb/user-provided/x.txt
```
"""


def run(root: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=10,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": "/usr/bin:/bin"},
    )


def write_payload(root: Path, rel: str, content: str) -> dict:
    return {"tool_input": {"file_path": str(root / rel), "content": content}}


class ArtifactResearchGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "raw-kb").mkdir()
        (self.root / "raw-kb" / "SOURCES.md").write_text(REGISTRY, encoding="utf-8")
        for stage in ("concept", "orientation", "reference", "foundation"):
            (self.root / "work" / stage).mkdir(parents=True)
        (self.root / ".agents").mkdir()
        (self.root / ".agents" / "policy.json").write_text(json.dumps({
            "evidence_bearing": ["concept/premise.md", "foundation/foundation.md"],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ungrounded_artifact_is_blocked(self) -> None:
        result = run(self.root, write_payload(self.root, "work/concept/premise.md", "# Premis\n\nTokoh pulang."))
        self.assertEqual(2, result.returncode)
        self.assertIn("work/concept/premise.md", result.stderr)

    def test_cited_source_id_passes(self) -> None:
        body = "# Premis\n\nTokoh pulang [[2026-07-02-sample-memoir-ocr-teks]]."
        result = run(self.root, write_payload(self.root, "work/concept/premise.md", body))
        self.assertEqual(0, result.returncode)

    def test_bare_template_source_id_is_not_a_citation(self) -> None:
        result = run(self.root, write_payload(self.root, "work/concept/premise.md", "source_id:"))
        self.assertEqual(2, result.returncode)

    def test_exempt_paths_pass_ungrounded(self) -> None:
        for rel in ("work/WORKFLOW.md", "work/orientation/intake.md", "work/reference/method.md"):
            with self.subTest(rel=rel):
                result = run(self.root, write_payload(self.root, rel, "no citation here"))
                self.assertEqual(0, result.returncode)

    def test_edit_sees_citation_already_in_the_file(self) -> None:
        target = self.root / "work" / "concept" / "premise.md"
        target.write_text("# Premis\n\nSumber: 2026-07-02-sample-memoir-ocr-teks\n", encoding="utf-8")
        payload = {"tool_input": {"file_path": str(target), "old_string": "Premis", "new_string": "Premis v2"}}
        self.assertEqual(0, run(self.root, payload).returncode)

    def test_write_cannot_inherit_the_citation_it_overwrites(self) -> None:
        target = self.root / "work" / "concept" / "premise.md"
        target.write_text("Sumber: 2026-07-02-sample-memoir-ocr-teks\n", encoding="utf-8")
        result = run(self.root, write_payload(self.root, "work/concept/premise.md", "# Premis\n\nTokoh pulang."))
        self.assertEqual(2, result.returncode)

    def test_non_work_path_is_ignored(self) -> None:
        result = run(self.root, write_payload(self.root, "docs/design/x.md", "no citation"))
        self.assertEqual(0, result.returncode)

    def test_missing_registry_blocks_gated_artifact(self) -> None:
        (self.root / "raw-kb" / "SOURCES.md").unlink()
        result = run(self.root, write_payload(self.root, "work/concept/premise.md", "no citation"))
        self.assertEqual(2, result.returncode)

    def test_malformed_json_fails_open(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input="not json{{{", text=True, capture_output=True, timeout=10
        )
        self.assertEqual(0, result.returncode)


class EvidenceBearingScopeTest(ArtifactResearchGateTest):
    def test_non_evidence_bearing_artifact_passes_uncited(self) -> None:
        result = run(self.root, write_payload(self.root, "work/concept/transformation.md", "# Transformasi\n\nTanpa sitasi."))
        self.assertEqual(0, result.returncode)

    def test_evidence_bearing_artifact_blocks_uncited(self) -> None:
        result = run(self.root, write_payload(self.root, "work/foundation/foundation.md", "# Fondasi\n\nTanpa sitasi."))
        self.assertEqual(2, result.returncode)

    def test_no_policy_file_gates_nothing(self) -> None:
        (self.root / ".agents" / "policy.json").unlink()
        result = run(self.root, write_payload(self.root, "work/foundation/foundation.md", "# Fondasi\n\nTanpa sitasi."))
        self.assertEqual(0, result.returncode)

    def test_relative_agents_path_is_never_gated(self) -> None:
        payload = {"tool_input": {"file_path": ".agents/telemetry/skill-usage.jsonl", "content": "{}"}}
        result = run(self.root, payload)
        self.assertEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
