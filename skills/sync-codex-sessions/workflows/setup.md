# Setup: Codex Session Sync

Export and manage Codex sessions in Obsidian.

If you are using these scripts from the repo checkout, install the Python deps once with:

```bash
uv sync
```

Codex workflow from the repo checkout:

```bash
uv run python scripts/codex-memory sync-sessions export --all
uv run python scripts/codex-memory sync-sessions list --all
uv run python scripts/codex-memory sync-sessions resume --pick
```

## 1. Export sessions

```bash
uv run python scripts/codex-memory sync-sessions export --all
uv run python scripts/codex-memory sync-sessions export --today
```

## 2. Add Shell Alias (Optional)

Add to `~/.zshrc`:

```bash
alias cxs="uv run python scripts/codex-memory sync-sessions"
```

Then:
- `cxs list` - list active sessions
- `cxs note "got it working"` - add note
- `cxs close "done"` - mark done
- `cxs resume --pick` - resume session

For Codex-exported notes, `cxs resume` will call `codex resume` / `codex fork` automatically based on the note frontmatter.

## 3. Verify

```bash
uv run python scripts/codex-memory sync-sessions list --all
```

## What Gets Synced

- **On every message:** Session metadata, skills used, artifacts created/modified
- **Preserved:** `## My Notes` section, `log`, `projects`, `status`, `comments` fields
