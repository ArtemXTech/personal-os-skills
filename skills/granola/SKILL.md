---
name: granola
description: Query and sync Granola meetings to Obsidian vault. Use when user mentions Granola, meeting transcripts, or wants to sync meeting notes. Reads from local cache - no API needed.
---

# Granola Skill

Query and sync Granola AI meeting notes to Obsidian vault.

## How It Works

Granola stores everything locally at `~/Library/Application Support/Granola/cache-v3.json`:
- Documents (meetings with title, notes, people)
- Transcripts (real-time, with timestamps and source)
- Updates in real-time as you record

No API calls needed - reads directly from local cache.

## Quick Start

```bash
# List all meetings
python3 .claude/skills/granola/scripts/granola.py list

# Get specific meeting with transcript
python3 .claude/skills/granola/scripts/granola.py get <id>

# Sync new meetings to vault
python3 .claude/skills/granola/scripts/granola.py sync

# Sync specific meeting
python3 .claude/skills/granola/scripts/granola.py sync --id <id>
```

## Commands

### list

List all Granola meetings with sync status.

```bash
python3 .claude/skills/granola/scripts/granola.py list
python3 .claude/skills/granola/scripts/granola.py list --limit 5
```

Output:
```
[✓] 2026-01-09  Team Sync - Weekly
    ID: abc123...
    Transcript: 450 segments, ~86 min

[ ] 2026-01-10  Team Standup
    ID: def456...
    Transcript: 120 segments, ~15 min
```

- `[✓]` = already synced to vault
- `[ ]` = not synced yet

### get

View full meeting details and transcript.

```bash
python3 .claude/skills/granola/scripts/granola.py get <id>
python3 .claude/skills/granola/scripts/granola.py get <id> --no-transcript
```

### sync

Sync meetings to `Meetings/` as structured Markdown.

```bash
# Sync new meetings only
python3 .claude/skills/granola/scripts/granola.py sync

# Sync specific meeting
python3 .claude/skills/granola/scripts/granola.py sync --id <id>

# Re-sync all (overwrites existing)
python3 .claude/skills/granola/scripts/granola.py sync --all
```

## Output Format

Synced meetings are saved to `Meetings/` with this structure:

```markdown
---
type: granola-meeting
date: 2026-01-09
time: "19:30"
duration_min: 86
granola_id: abc123...
people:
  - "[[Sarah Chen]]"
topics: []
status: raw
---

# Meeting Title

## Notes

(Your notes from Granola)

## Transcript

[19:30:45] 🎤 Hey, how's it going?
[19:30:48] 🎤 Great to meet you...
```

**Transcript icons:**
- 🎤 = microphone (you)
- 🔊 = system audio (others on call)

## Workflow

1. **Record meeting** in Granola (real-time transcription)
2. **Sync to vault**: `python3 .claude/skills/granola/scripts/granola.py sync`
3. **Process meeting**: Extract action items, update people notes
4. **Mark as processed**: Change `status: raw` to `status: processed`

## Querying with Bases

Use `Granola.base` to query synced meetings:

| View | Filter |
|------|--------|
| Recent | Last 7 days |
| Needs Processing | status = raw |
| By Person | Grouped by people field |

## Data Structure

**Local cache:** `~/Library/Application Support/Granola/cache-v3.json`

```
cache (JSON string) → state →
  ├── documents: {id: {title, notes_plain, notes_markdown, people, created_at}}
  └── transcripts: {id: [{text, source, start_timestamp, end_timestamp}]}
```

**Transcript segment:**
```json
{
  "text": "Hey, how's it going?",
  "source": "microphone",
  "start_timestamp": "2026-01-09T19:30:45.123Z",
  "end_timestamp": "2026-01-09T19:30:48.456Z"
}
```

## Tips

- **Real-time access**: Cache updates as you record - can query mid-meeting
- **Free tier hack**: Sync hourly to bypass 7-day history limit
- **No auth needed**: Uses local files, not API
