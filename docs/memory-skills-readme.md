# Claude Code Memory Skills

Give Claude Code persistent memory across sessions using Obsidian + QMD local search.

Two skills:

**`/recall`** - Load context from previous sessions. Three modes:
- Temporal: "what did I work on yesterday?" (scans native JSONL logs)
- Topic: "recall authentication work" (BM25 search via QMD)
- Graph: "recall graph last week" (interactive session visualization)

**`/sync-claude-sessions`** - Export Claude Code conversations to Obsidian markdown. Auto-sync via hooks, add notes, resume sessions.

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
   pip install networkx pyvis
   ```

4. Try it:
   ```
   /recall yesterday
   /recall graph last week
   ```

Temporal recall works immediately - it reads native Claude Code session files. Topic search requires QMD collections (see AGENTS.md for full setup).

## Full Setup

See [AGENTS.md](AGENTS.md) for complete setup instructions including QMD collections, auto-sync hooks, and auto-indexing.

## Video

Watch the full walkthrough: https://youtu.be/RDoTY4_xh0s
