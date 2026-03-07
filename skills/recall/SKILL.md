---
name: recall
description: Load context from vault memory. Temporal queries (yesterday, last week, session history) use native JSONL timeline. Topic queries use QMD BM25 search. "recall graph" generates interactive temporal graph of sessions and files. Every recall ends with "One Thing" - the single highest-leverage next action synthesized from results. Use when user says "recall", "what did we work on", "load context about", "remember when we", "prime context", "yesterday", "what was I doing", "last week", "session history", "recall graph", "session graph".
argument-hint: [yesterday|today|last week|this week|TOPIC|graph DATE_EXPR]
allowed-tools: Bash(qmd:*), Bash(python3:*)
---

# Recall Skill

Three modes: temporal (date-based session timeline), topic (BM25 search across QMD collections), and graph (interactive visualization of session-file relationships). Every recall ends with the **One Thing** - a concrete, highest-leverage next action synthesized from the results.

## What It Does

- **Temporal queries** ("yesterday", "last week", "what was I doing"): Scans native Claude Code or Codex JSONL files by date. Shows a table of sessions with time, message count, and first message. Expand any session for conversation details.
- **Topic queries** ("QMD video", "authentication"): BM25 search across sessions, notes, and daily logs in QMD collections.
- **Graph queries** ("graph yesterday", "graph last week"): Generates an interactive HTML graph showing sessions as nodes connected to files they touched. Sessions colored by day, files colored by folder. Clusters reveal related work streams, shared files show cross-session dependencies.
- **One Thing synthesis**: After presenting results, synthesizes the single most impactful next action based on what has momentum, what's blocked, and what's closest to done. Not generic - specific and actionable.

No custom setup needed for temporal recall - both Claude Code and Codex persist JSONL session history locally.

## Auto-Indexing (Optional)

You can auto-index sessions into QMD on every session end via a Claude Code hook. Codex support is currently focused on reading/exporting saved sessions; hook docs are still Claude-oriented.

## Usage

```
/recall yesterday
/recall last week
/recall 2026-02-25
/recall QMD video
/recall authentication work
```

**Graph mode** - visualize session relationships over time:
```
/recall graph yesterday        # what you touched today
/recall graph last week        # week overview - find clusters
/recall graph this week        # current week so far
/recall graph last 3 days      # recent activity window
```

Graph options: `--min-files 5` for cleaner graphs (only sessions touching 5+ files), `--all-projects` to scan beyond current vault.

## Workflow

See `workflows/recall.md` for routing logic and step-by-step process.
