# Memory Skills for Claude Code + Obsidian

Agent-readable setup guide. Follow these steps to give Claude Code persistent memory across sessions using QMD local search and Obsidian.

Codex note: the session parsing scripts now understand Codex rollouts in `~/.codex/sessions`, but the install paths and hook examples in this document are still written for Claude Code.

If you want to install the skills in Codex instead of Claude Code, use Codex's skill installer:

```bash
python3 ~/.codex/skills/skill-installer/scripts/install-skill-from-github.py \
  --repo ArtemXTech/personal-os-skills \
  --path skills/recall \
  --path skills/sync-codex-sessions
```

Then install the Python environment from the repo checkout:

```bash
cd /path/to/personal-os-skills
uv sync
```

Optional Codex helper wrapper from the repo checkout:

```bash
uv run python scripts/codex-memory --help
```

## Prerequisites

- Claude Code installed and working
- An Obsidian vault (any vault works)
- Node.js >= 22 or Bun >= 1.0

## Step 1: Install Skills

Copy both skill folders into your project's `.claude/skills/` directory:

```bash
cp -r recall/ .claude/skills/recall/
cp -r sync-claude-sessions/ .claude/skills/sync-claude-sessions/
```

## Step 2: Install QMD

QMD is the local search engine that powers topic-based recall. Install globally:

```bash
npm install -g @tobilu/qmd
```

First run downloads models (~2GB). Verify:

```bash
qmd status
```

## Step 3: Create QMD Collections

Index your vault and Claude Code sessions for search:

```bash
# Index your Obsidian vault notes
qmd collection add /path/to/your/vault --name notes

# Create a directory for extracted session markdown
mkdir -p /path/to/your/vault/Notes/Projects/claude-sessions-qmd

# Extract recent sessions to markdown (run from your vault directory)
python3 .claude/skills/recall/scripts/extract-sessions.py --days 30

# Index the extracted sessions
qmd collection add /path/to/your/vault/Notes/Projects/claude-sessions-qmd --name sessions

# Build the index
qmd update
qmd embed
```

Replace `/path/to/your/vault` with your actual Obsidian vault path.

## Step 4: Install Python Dependencies

The graph visualization requires NetworkX and pyvis. This repo now includes a `uv` project:

```bash
uv sync
```

Run the scripts with `uv run`:

```bash
uv run python skills/recall/scripts/session-graph.py today --min-msgs 1 --min-files 1
```

## Step 5: Set Up Auto-Sync Hook (Optional)

Auto-sync sessions to Obsidian on every prompt. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions sync",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions sync",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

## Step 6: Set Up Auto-Index Hook (Optional)

Keep QMD sessions index fresh automatically. Create `~/.claude/hooks/index-sessions.sh`:

```bash
#!/bin/bash
VAULT_DIR="/path/to/your/vault"
cd "$VAULT_DIR"
python3 .claude/skills/recall/scripts/extract-sessions.py --days 3
qmd update
```

Make it executable:

```bash
chmod +x ~/.claude/hooks/index-sessions.sh
```

Add a `SessionEnd` hook to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/index-sessions.sh >> ~/.claude/hooks/index-sessions.log 2>&1",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Step 7: Add Shell Alias (Optional)

```bash
# Add to ~/.zshrc or ~/.bashrc
alias cs="python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions"
```

Codex-friendly alias from the repo checkout:

```bash
alias cxs="uv run python scripts/codex-memory sync-sessions"
```

## Step 8: Codex Workflow

Typical Codex workflow from the repo checkout:

```bash
# Export saved Codex sessions into Obsidian markdown
uv run python scripts/codex-memory sync-sessions export --all

# Recall recent Codex sessions by date
uv run python scripts/codex-memory recall-day list last week --min-msgs 1

# Build the interactive HTML graph plus native Obsidian graph notes.
# If VAULT_DIR is set (or CWD is inside a vault), the Obsidian export path is chosen automatically.
uv run python scripts/codex-memory session-graph last week \
  --min-msgs 1 \
  --min-files 1
```

When you export a Codex session note, `cxs resume` will resume it with `codex resume`, and `cxs resume --fork` will use `codex fork`.

## How It Works

### /recall (temporal)
Scans native Claude Code JSONL session logs by date. No QMD needed.

```
/recall yesterday
/recall last week
/recall 2026-02-25
```

### /recall (topic)
BM25 search across QMD collections. Requires QMD setup (steps 2-3).

```
/recall authentication work
/recall QMD video
```

### /recall graph
Interactive HTML visualization of sessions and files touched. Requires networkx + pyvis.

```
/recall graph last week
/recall graph yesterday
```

Native Obsidian graph export:

```bash
uv run python scripts/codex-memory session-graph last week \
  --obsidian-export /path/to/your/vault/Session-Graphs/last-week
```

### /sync-claude-sessions
Export Claude Code conversations to Obsidian markdown with frontmatter, artifacts, and preserved notes.

### /sync-codex-sessions
Export Codex conversations to `Codex-Sessions/`, preserve notes/status/tags, and resume or fork the exported session directly back into Codex.

```bash
cs export --today    # Export today's sessions
cs list              # List active sessions
cs resume --pick     # Resume a session
cs note "progress"   # Add timestamped note
cs close "done"      # Mark session done
```

## Environment Variables

- `VAULT_DIR` - Override auto-detection of Obsidian vault path. If not set, scripts walk up from CWD looking for `.obsidian/` directory.

## Auto-Detection

All scripts auto-detect paths:
- **Vault directory**: walks up from CWD looking for `.obsidian/` folder, or uses `VAULT_DIR` env var
- **Claude project directory**: derives from CWD using Claude Code's encoding scheme (`/path/to/dir` -> `-path-to-dir`)
- **Codex session directory**: uses `~/.codex/sessions` when `SESSION_BACKEND=codex` or when Claude project logs are not present
- **No hardcoded paths** - works with any vault, any username, any OS
