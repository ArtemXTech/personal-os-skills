import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path("/home/tools/personal-os-skills")
WRAPPER_SCRIPT = ROOT / "scripts" / "codex-memory"
SYNC_SCRIPT = ROOT / "skills" / "sync-claude-sessions" / "scripts" / "claude-sessions"
RECALL_DAY_SCRIPT = ROOT / "skills" / "recall" / "scripts" / "recall-day.py"
EXTRACT_SCRIPT = ROOT / "skills" / "recall" / "scripts" / "extract-sessions.py"
GRAPH_SCRIPT = ROOT / "skills" / "recall" / "scripts" / "session-graph.py"


def load_module(path: Path, module_name: str):
    loader = importlib.machinery.SourceFileLoader(module_name, str(path))
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_codex_rollout(path: Path, session_id: str, user_messages, *, function_calls=None):
    function_calls = function_calls or []
    lines = [
        {
            "timestamp": "2026-03-08T10:00:00.000Z",
            "type": "session_meta",
            "payload": {
                "id": session_id,
                "timestamp": "2026-03-08T10:00:00.000Z",
                "cwd": "/home/test-project",
            },
        }
    ]
    for idx, text in enumerate(user_messages, start=1):
        lines.append(
            {
                "timestamp": f"2026-03-08T10:00:0{idx}.000Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}],
                },
            }
        )
    for idx, call in enumerate(function_calls, start=1):
        lines.append(
            {
                "timestamp": f"2026-03-08T10:01:0{idx}.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": call["name"],
                    "arguments": call["arguments"],
                },
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


class CodexSessionSupportTests(unittest.TestCase):
    def test_recall_day_codex_scan_and_dedupe(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SESSION_BACKEND"] = "codex"
            recall_day = load_module(RECALL_DAY_SCRIPT, "recall_day_test_a")

            root = Path(tmp)
            a = root / "2026" / "03" / "08" / "rollout-a.jsonl"
            b = root / "2026" / "03" / "08" / "rollout-b.jsonl"
            write_codex_rollout(a, "sess-1", ["first title"])
            write_codex_rollout(b, "sess-1", ["second title"])

            start = recall_day.datetime(2026, 3, 8, tzinfo=recall_day.timezone.utc)
            end = start + recall_day.timedelta(days=1)
            meta_a = recall_day.scan_session_metadata(a, start, end)
            meta_b = recall_day.scan_session_metadata(b, start, end)
            self.assertEqual(meta_a["session_id"], "sess-1")
            self.assertEqual(meta_b["user_msg_count"], 1)

            deduped = recall_day.dedupe_session_metadata([meta_a, meta_b])
            self.assertEqual(len(deduped), 1)
            self.assertEqual(deduped[0]["session_id"], "sess-1")

    def test_extract_sessions_codex_dedupes_latest_rollout(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sessions"
            output = Path(tmp) / "out"
            older = source / "2026" / "03" / "08" / "rollout-older.jsonl"
            newer = source / "2026" / "03" / "08" / "rollout-newer.jsonl"
            write_codex_rollout(older, "sess-2", ["older message"])
            time.sleep(0.01)
            write_codex_rollout(newer, "sess-2", ["newer message"])

            env = os.environ.copy()
            env["SESSION_BACKEND"] = "codex"
            subprocess.run(
                [
                    "python3",
                    str(EXTRACT_SCRIPT),
                    "--days",
                    "30",
                    "--source",
                    str(source),
                    "--output",
                    str(output),
                ],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )

            files = sorted(output.glob("*.md"))
            self.assertEqual(len(files), 1)
            content = files[0].read_text(encoding="utf-8")
            self.assertIn("newer message", content)

    def test_sync_script_exports_codex_and_builds_resume_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            (vault / ".obsidian").mkdir(parents=True)
            transcript = Path(tmp) / "rollout.jsonl"
            write_codex_rollout(transcript, "sess-3", ["resume me"])

            os.environ["SESSION_BACKEND"] = "codex"
            os.environ["VAULT_DIR"] = str(vault)
            sync_mod = load_module(SYNC_SCRIPT, "sync_codex_test")

            out = sync_mod.sync_session("sess-3", str(transcript), quiet=True)
            self.assertTrue(out.exists())
            content = out.read_text(encoding="utf-8")
            self.assertIn("agent_backend: codex", content)
            self.assertEqual(
                sync_mod.build_resume_command("codex", "sess-3", False),
                ["codex", "resume", "sess-3"],
            )
            self.assertEqual(
                sync_mod.build_resume_command("codex", "sess-3", True),
                ["codex", "fork", "sess-3"],
            )

    def test_session_graph_extracts_codex_file_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "rollout.jsonl"
            home = Path.home()
            write_codex_rollout(
                rollout,
                "sess-4",
                ["graph this"],
                function_calls=[
                    {
                        "name": "exec_command",
                        "arguments": json.dumps(
                            {
                                "cmd": f"sed -n '1,20p' {home}/tools/demo/README.md",
                                "workdir": f"{home}/tools/demo",
                            }
                        ),
                    },
                    {
                        "name": "apply_patch",
                        "arguments": "*** Begin Patch\n*** Update File: /root/tools/demo/src/app.py\n+print('x')\n*** End Patch\n",
                    },
                ],
            )

            os.environ["SESSION_BACKEND"] = "codex"
            graph_mod = load_module(GRAPH_SCRIPT, "session_graph_codex_test")
            result = graph_mod.extract_file_paths(rollout)

            self.assertIsNotNone(result)
            self.assertIn("tools/demo/README.md", result["files"])
            self.assertIn("tools/demo/src/app.py", result["files"])

    def test_session_graph_exports_obsidian_notes(self):
        os.environ["SESSION_BACKEND"] = "codex"
        graph_mod = load_module(GRAPH_SCRIPT, "session_graph_obsidian_test")
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp) / "obsidian-graph"
            sessions = [
                {
                    "session_id": "sess-5",
                    "start_time": graph_mod.datetime(2026, 3, 8, 10, 0, tzinfo=graph_mod.timezone.utc),
                    "title": "Build graph support",
                    "msg_count": 12,
                    "filepath": "/root/.codex/sessions/example.jsonl",
                    "files": {"tools/demo/README.md", "tools/demo/src/app.py"},
                }
            ]

            info = graph_mod.export_obsidian_graph_artifacts(
                sessions,
                export_dir,
                "2026-03-08",
                min_files=1,
            )

            self.assertEqual(info["sessions"], 1)
            self.assertEqual(info["files"], 2)
            index = (export_dir / "session-graph-index.md").read_text(encoding="utf-8")
            self.assertIn("[[session-sess-5|Build graph support]]", index)

            session_note = (export_dir / "session-sess-5.md").read_text(encoding="utf-8")
            self.assertIn("[[file-tools__demo__README_md|README.md]]", session_note)

            file_note = (export_dir / "file-tools__demo__README_md.md").read_text(encoding="utf-8")
            self.assertIn("[[session-sess-5]]", file_note)

    def test_session_graph_default_obsidian_export_dir_uses_vault(self):
        os.environ["VAULT_DIR"] = "/tmp/example-vault"
        graph_mod = load_module(GRAPH_SCRIPT, "session_graph_default_export_test")
        expected = Path("/tmp/example-vault/Session-Graphs/last-week")
        self.assertEqual(graph_mod.default_obsidian_export_dir("Last Week"), expected)

    def test_codex_memory_wrapper_sets_backend_and_dispatches(self):
        content = WRAPPER_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('os.environ.setdefault("SESSION_BACKEND", "codex")', content)
        self.assertIn('"session-graph"', content)
        self.assertIn('"sync-sessions"', content)


if __name__ == "__main__":
    unittest.main()
