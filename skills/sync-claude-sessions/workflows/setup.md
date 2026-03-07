# Setup: Live Session Sync

Enable automatic syncing of Claude Code sessions to Obsidian.

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

## 3. Verify

```bash
# Test sync
echo '{"session_id":"test","transcript_path":"/tmp/fake.jsonl"}' | python3 .claude/skills/sync-claude-sessions/scripts/claude-sessions sync

# Should output "Error" or "Synced" depending on file existence
```

## What Gets Synced

- **On every message:** Session metadata, skills used, artifacts created/modified
- **Preserved:** `## My Notes` section, `log`, `projects`, `status`, `comments` fields
