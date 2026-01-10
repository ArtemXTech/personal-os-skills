# Space Management

The Wispr Flow database can grow large due to audio blobs stored with each dictation.

## Check Space Usage

```bash
# Total database size
ls -lh ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite

# Audio blob size
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT
    ROUND(SUM(LENGTH(audio))/1e9, 2) as audio_gb,
    ROUND(SUM(LENGTH(screenshot))/1e9, 2) as screenshot_gb
FROM History
"

# Size breakdown by month
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT
    strftime('%Y-%m', timestamp) as month,
    COUNT(*) as dictations,
    ROUND(SUM(LENGTH(audio))/1e6, 1) as audio_mb
FROM History
GROUP BY month
ORDER BY month
"
```

## Clean Up Audio (Keep Text)

Delete audio blobs older than 30 days while keeping all text:

```bash
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
UPDATE History
SET audio = NULL, builtInAudio = NULL
WHERE timestamp < datetime('now', '-30 days')
"

# Reclaim space (important!)
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "VACUUM"
```

## Backup Before Cleaning

Always backup first:

```bash
cp ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite ~/Downloads/wispr-backup-$(date +%Y%m%d).sqlite
```

## Typical Sizes

- Text only: ~1-2 MB per 1000 dictations
- With audio: ~300 MB per 1000 dictations (varies by length)

## Full Backup

```bash
# Full database (with audio)
cp ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite ~/Downloads/wispr-full-backup.sqlite

# Text-only export (portable JSON)
.claude/skills/wispr-flow/scripts/export-data.py -o ~/Downloads/wispr-text-backup.json
```
