# Setup: Live Session Sync

Enable automatic syncing of Claude Code sessions to Obsidian.

Codex note: the export/resume script supports Codex rollouts, but the live hook examples below are still Claude-specific.

If you are using these scripts from the repo checkout, install the Python deps once with:

```bash
uv sync
```

Codex workflow from the repo checkout:

```bash
SESSION_BACKEND=codex uv run python skills/sync-claude-sessions/scripts/claude-sessions export --all
SESSION_BACKEND=codex uv run python skills/sync-claude-sessions/scripts/claude-sessions list --all
SESSION_BACKEND=codex uv run python skills/sync-claude-sessions/scripts/claude-sessions resume --pick
```

## 1. Add Hooks to Settings

Edit `~/.claude/settings.json`:

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

## 2. Add Shell Alias (Optional)

Add to `~/.zshrc`:

```bash
alias cs="python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions"
```

Then:
- `cs list` - list active sessions
- `cs note "got it working"` - add note
- `cs close "done"` - mark done
- `cs resume --pick` - resume session

For Codex-exported notes, `cs resume` will call `codex resume` / `codex fork` automatically based on the note frontmatter.

## 3. Verify

```bash
# Test sync
echo '{"session_id":"test","transcript_path":"/tmp/fake.jsonl"}' | python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions sync

# Should output "Error" or "Synced" depending on file existence
```

## What Gets Synced

- **On every message:** Session metadata, skills used, artifacts created/modified
- **Preserved:** `## My Notes` section, `log`, `projects`, `status`, `comments` fields
