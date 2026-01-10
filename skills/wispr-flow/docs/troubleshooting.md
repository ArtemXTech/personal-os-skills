# Troubleshooting

## Database Not Found

**Error:** `Wispr Flow database not found`

**Solution:** Wispr Flow stores data at:
```
~/Library/Application Support/Wispr Flow/flow.sqlite
```

If missing:
1. Make sure Wispr Flow is installed
2. Dictate something to create the database
3. Check if path has changed: `find ~/Library -name "flow.sqlite" 2>/dev/null`

## Empty Results

**Issue:** Stats show 0 dictations

**Check:**
```bash
# Verify data exists
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "SELECT COUNT(*) FROM History"

# Check for cancelled entries
sqlite3 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite "
SELECT status, COUNT(*) FROM History GROUP BY status
"
```

## Timezone Issues

**Issue:** Times appear wrong

The database stores UTC timestamps. Scripts use `-5 hours` offset for EST.

**Adjust for your timezone:**
- EST: `-5 hours`
- PST: `-8 hours`
- UTC: no offset

Edit the `TZ_OFFSET` constant in scripts if needed.

## Large Database

**Issue:** Database is very large (>5GB)

Most space is audio blobs. See [space-management.md](space-management.md) for cleanup.

## Permission Denied

**Error:** Cannot read database

```bash
# Check permissions
ls -la ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite

# Fix if needed
chmod 644 ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite
```

## Database Locked

**Error:** `database is locked`

Wispr Flow is actively writing. Either:
1. Wait a moment and retry
2. Make a copy and query that:
   ```bash
   cp ~/Library/Application\ Support/Wispr\ Flow/flow.sqlite /tmp/wispr-copy.sqlite
   sqlite3 /tmp/wispr-copy.sqlite "SELECT COUNT(*) FROM History"
   ```
