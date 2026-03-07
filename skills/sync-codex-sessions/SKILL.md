---
name: sync-codex-sessions
description: Sync Codex sessions to Obsidian markdown. Export, resume, add notes, close sessions. USE WHEN user says "sync codex sessions", "export codex sessions", "resume codex session", "add codex session note", "close codex session", "log codex session".
---

# Sync Codex Sessions

Export Codex conversations to Obsidian for observability and analysis.

## Quick Reference

```bash
# Alias (add to ~/.zshrc, or use `uv run python scripts/codex-memory sync-sessions`)
alias cxs="python3 ~/.codex/skills/sync-codex-sessions/scripts/codex-sessions"

# Common commands
cxs list                    # Active sessions
cxs list --all              # All sessions
cxs export --today          # Export today's sessions
cxs resume --pick           # Interactive resume
cxs note "got it working"   # Add timestamped comment
cxs close "done"            # Mark session done
```

## Commands

| Command | Description |
|---------|-------------|
| `sync` | Sync session (hook or explicit) |
| `export` | Batch export (`--today`, `--all`, `<file>`) |
| `resume` | Resume session (`--pick`, `--active`, `<file>`) |
| `note` | Add timestamped comment |
| `close` | Mark done + optional comment |
| `list` | List sessions (`--active`, `--all`, `--json`) |

## Workflow Routing

| Task | Workflow |
|------|----------|
| Enable live sync hooks | [workflows/setup.md](workflows/setup.md) |
| Log/annotate session | [workflows/log-session.md](workflows/log-session.md) |

## Output

Sessions exported to `Codex-Sessions/` with:
- Frontmatter: `type`, `date`, `session_id`, `title`, `summary`, `skills`, `messages`, `status`, `tags`, `rating`, `comments`
- Content: Summary, Skills Used (linked), Artifacts (wiki-linked), My Notes, Conversation

## Preserved on Sync

- `## My Notes` section
- Frontmatter: `comments`, `related`, `status`, `tags`, `rating`

## Frontmatter Schema

> See the YAML example below for the canonical Codex session note shape.

```yaml
type: codex-session
date: YYYY-MM-DD
session_id: uuid
title: "..."
summary: "..." # auto-generated when available
skills: [skill1, skill2]
messages: 42
last_activity: ISO timestamp
status: active | done | blocked | handoff
tags: []          # see schema/tags.yaml
rating: null      # 1-10
comments: |
  [2026-02-05 14:30] Comment here
  [2026-02-05 15:00] Another comment
related: []
```

## Tags Schema

Tags are defined in `schema/tags.yaml` with descriptions, keywords, and examples.

**Type tags:** research, implementation, debugging, planning, brainstorm, admin, quick, video, automation, writing

**Project tags:** lab, openclaw, personal, client

Agent should read `schema/tags.yaml` to validate tags when logging sessions.
