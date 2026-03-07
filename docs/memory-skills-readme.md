# Claude Code Memory Skills

Give Claude Code persistent memory across sessions using Obsidian + QMD local search.

Initial Codex support is available for the session-based scripts behind `/recall` and `/sync-claude-sessions`. The hook/setup examples below are still Claude-oriented.

Two skills:

**`/recall`** - Load context from previous sessions. Three modes:
- Temporal: "what did I work on yesterday?" (scans native JSONL logs)
- Topic: "recall authentication work" (BM25 search via QMD)
- Graph: "recall graph last week" (interactive session visualization for Claude Code or Codex rollouts)

**`/sync-claude-sessions`** - Export Claude Code or Codex conversations to Obsidian markdown. Auto-sync via hooks, add notes, resume sessions.

## Quick Start

1. Copy skills to your project:
   ```bash
   cp -r recall/ .claude/skills/recall/
   cp -r sync-claude-sessions/ .claude/skills/sync-claude-sessions/
   ```

2. Install QMD (local search engine):
   ```bash
   npm install -g @tobilu/qmd
   ```

3. Install Python deps (for graph visualization):
   ```bash
   uv sync
   ```

4. Try it:
   ```
   /recall yesterday
   /recall graph last week
   ```

Temporal recall works immediately - it reads native Claude Code or Codex session files. Topic search requires QMD collections (see AGENTS.md for full setup).

## Full Setup

See [AGENTS.md](AGENTS.md) for complete setup instructions including QMD collections, auto-sync hooks, and auto-indexing.

## Native Obsidian Graph Export

The graph script can export native Obsidian graph artifacts as linked Markdown notes:

```bash
uv run python skills/recall/scripts/session-graph.py last week \
  --obsidian-export /path/to/your/vault/Session-Graphs/last-week
```

This creates session notes, file notes, and an index note connected with wikilinks so Obsidian's graph view can render them directly.

## Tests

Run the session-backend regression tests with:

```bash
uv run python -m unittest discover -s tests -v
```

## Video

Watch the full walkthrough: https://youtu.be/RDoTY4_xh0s
