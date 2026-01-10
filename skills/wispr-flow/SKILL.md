---
name: wispr-flow
description: Analyze Wispr Flow voice dictation data. Stats, search, export, visualizations. Use when user says "dictation history", "word counts", "voice analytics", "how much did I dictate", "search my dictation".
---

# Wispr Flow Skill

Access and analyze your Wispr Flow voice dictation history.

## Quick Stats

```bash
# Overall stats
{baseDir}/scripts/get-stats.py

# Today only
{baseDir}/scripts/get-stats.py --period today

# This week
{baseDir}/scripts/get-stats.py --period week

# JSON output
{baseDir}/scripts/get-stats.py --json
```

## Search

```bash
# Search all dictations
{baseDir}/scripts/search-history.py "keyword"

# Filter by app
{baseDir}/scripts/search-history.py "keyword" --app ghostty

# Date range
{baseDir}/scripts/search-history.py "keyword" --from 2026-01-01 --to 2026-01-10
```

## Export

```bash
# JSON backup (text only, portable)
{baseDir}/scripts/export-data.py -o ~/Downloads/wispr-backup.json

# Obsidian daily notes format
{baseDir}/scripts/export-data.py --format obsidian -o ~/vault/Voice/
```

## Visualization

```bash
# Generate interactive HTML dashboard
{baseDir}/scripts/create-dashboard.py -o ~/Downloads/wispr-dashboard.html
open ~/Downloads/wispr-dashboard.html
```

## Quick Queries (Direct SQL)

```bash
# Recent dictations (EST timezone)
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT datetime(timestamp, '-5 hours') as time, app, substr(formattedText, 1, 80)
FROM History ORDER BY timestamp DESC LIMIT 10
"

# Words by app
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT app, SUM(numWords) as words FROM History
WHERE app IS NOT NULL GROUP BY app ORDER BY words DESC LIMIT 10
"

# Today's word count
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT SUM(numWords) FROM History
WHERE date(timestamp, '-5 hours') = date('now', '-5 hours')
"
```

## Database

**Location:** `~/Library/Application Support/Wispr Flow/flow.sqlite`

**Key tables:**
- `History` - all dictations (timestamp, app, formattedText, numWords, duration, audio blob)

**Timezone:** Database stores UTC. Use `-5 hours` for EST.

## Space Management

See [docs/space-management.md](docs/space-management.md) for cleaning up audio blobs.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues.
