# Local Data Sources Reference

All queryable data on your Mac.

## Quick Reference

| Source | DB Path | Size | Key Table |
|--------|---------|------|-----------|
| Wispr Flow | `~/Library/Application Support/Wispr Flow/flow.sqlite` | 5.3GB | `History` |
| Brave | `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History` | 35MB | `urls`, `visits` |
| Chrome | `~/Library/Application Support/Google/Chrome/Default/History` | 1.1MB | `urls`, `visits` |
| Safari | `~/Library/Safari/History.db` | 756KB | `history_items` |
| Screen Time | `~/Library/Application Support/Knowledge/knowledgeC.db` | 12MB | `ZOBJECT` |
| ActivityWatch | `~/Library/Application Support/activitywatch/aw-server/peewee-sqlite.v2.db` | 1.5MB | `eventmodel` |
| Apple Notes | `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite` | 7.9MB | `ZICCLOUDSYNCINGOBJECT` |
| iMessage | `~/Library/Messages/chat.db` | 480KB | `message`, `handle` |
| Contacts | `~/Library/Application Support/AddressBook/AddressBook-v22.abcddb` | 480KB | `ZABCDRECORD` |

**Note:** Browser and Messages databases are locked while apps run. Copy to /tmp first:
```bash
cp ~/Library/Application\ Support/BraveSoftware/Brave-Browser/Default/History /tmp/brave.db
```

---

## 1. Wispr Flow (Voice Dictation)

**Database:** `~/Library/Application Support/Wispr Flow/flow.sqlite`

**Key fields:**
```sql
transcriptEntityId  -- unique ID
timestamp           -- UTC datetime
formattedText       -- AI-formatted transcription
asrText             -- raw ASR output
editedText          -- user's final edit
app                 -- active app bundle ID (e.g., com.mitchellh.ghostty)
url                 -- active URL if browser
numWords            -- word count
duration            -- seconds
audio               -- BLOB (raw recording)
screenshot          -- BLOB
```

**Sample query:**
```sql
SELECT datetime(timestamp, '-5 hours') as time, app, substr(formattedText, 1, 80)
FROM History ORDER BY timestamp DESC LIMIT 10;
```

**Stats query:**
```sql
SELECT COUNT(*), SUM(numWords), ROUND(SUM(duration)/3600, 1) as hours FROM History;
```

---

## 2. Brave/Chrome Browser History

**Database:** `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History`

**Tables:**
- `urls` - unique URLs with visit counts
- `visits` - individual page visits with timestamps

**Key fields (urls):**
```sql
id                  -- URL ID
url                 -- full URL
title               -- page title
visit_count         -- total visits
last_visit_time     -- Chrome timestamp (microseconds since 1601)
```

**Timestamp conversion:** `datetime(last_visit_time/1000000-11644473600, 'unixepoch', '-5 hours')`

**Sample query:**
```sql
SELECT datetime(last_visit_time/1000000-11644473600, 'unixepoch', '-5 hours') as time,
       title, url
FROM urls ORDER BY last_visit_time DESC LIMIT 20;
```

**Top sites:**
```sql
SELECT
    CASE WHEN url LIKE '%youtube.com%' THEN 'YouTube'
         WHEN url LIKE '%github.com%' THEN 'GitHub'
         ELSE 'Other' END as site,
    SUM(visit_count) as visits
FROM urls GROUP BY site ORDER BY visits DESC;
```

---

## 3. Screen Time (Apple Knowledge)

**Database:** `~/Library/Application Support/Knowledge/knowledgeC.db`

**Main table:** `ZOBJECT`

**Key streams (ZSTREAMNAME):**
- `/app/usage` - app usage events
- `/app/webUsage` - web browsing
- `/notification/usage` - notification interactions
- `/display/isBacklit` - screen on/off
- `/media/nowPlaying` - media playback

**Key fields:**
```sql
ZSTREAMNAME         -- event type
ZSTARTDATE          -- Apple timestamp (seconds since 2001-01-01)
ZENDDATE            -- end time
ZVALUESTRING        -- app bundle ID or value
ZVALUEDOUBLE        -- numeric value
```

**Timestamp conversion:** `datetime(ZSTARTDATE + 978307200, 'unixepoch', '-5 hours')`

**Sample query (app usage):**
```sql
SELECT datetime(ZSTARTDATE + 978307200, 'unixepoch', '-5 hours') as time,
       ZVALUESTRING as app
FROM ZOBJECT
WHERE ZSTREAMNAME = '/app/usage'
ORDER BY ZSTARTDATE DESC LIMIT 20;
```

**Daily app totals:**
```sql
SELECT date(ZSTARTDATE + 978307200, 'unixepoch', '-5 hours') as day,
       ZVALUESTRING as app,
       COUNT(*) as sessions
FROM ZOBJECT
WHERE ZSTREAMNAME = '/app/usage'
GROUP BY day, app
ORDER BY day DESC, sessions DESC;
```

---

## 4. ActivityWatch

**Database:** `~/Library/Application Support/activitywatch/aw-server/peewee-sqlite.v2.db`

**Tables:**
- `bucketmodel` - data sources (window watcher, AFK watcher)
- `eventmodel` - individual events

**Key fields:**
```sql
timestamp           -- ISO datetime
duration            -- seconds
datastr             -- JSON with app/title info
bucket_id           -- source bucket
```

**Sample query:**
```sql
SELECT datetime(timestamp), duration, datastr
FROM eventmodel ORDER BY timestamp DESC LIMIT 10;
```

---

## 5. Apple Notes

**Database:** `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`

**Main table:** `ZICCLOUDSYNCINGOBJECT`

**Key fields:**
```sql
ZTITLE              -- note title
ZSNIPPET            -- preview text
ZMODIFICATIONDATE   -- last modified (Apple timestamp)
```

**Sample query:**
```sql
SELECT ZTITLE, ZSNIPPET,
       datetime(ZMODIFICATIONDATE + 978307200, 'unixepoch', '-5 hours') as modified
FROM ZICCLOUDSYNCINGOBJECT
WHERE ZTITLE IS NOT NULL
ORDER BY ZMODIFICATIONDATE DESC LIMIT 10;
```

---

## 6. iMessage

**Database:** `~/Library/Messages/chat.db`

**Tables:**
- `message` - all messages
- `handle` - contacts (phone/email)
- `chat` - conversations

**Key fields (message):**
```sql
text                -- message content
date                -- timestamp (nanoseconds since 2001)
is_from_me          -- 1 if sent, 0 if received
handle_id           -- link to contact
```

**Timestamp conversion:** `datetime(date/1000000000 + 978307200, 'unixepoch', '-5 hours')`

**Sample query:**
```sql
SELECT datetime(m.date/1000000000 + 978307200, 'unixepoch', '-5 hours') as time,
       h.id as contact,
       m.is_from_me,
       substr(m.text, 1, 50) as preview
FROM message m
LEFT JOIN handle h ON m.handle_id = h.ROWID
WHERE m.text IS NOT NULL
ORDER BY m.date DESC LIMIT 20;
```

---

## 7. Contacts

**Database:** `~/Library/Application Support/AddressBook/AddressBook-v22.abcddb`

**Main table:** `ZABCDRECORD`

**Related tables:**
- `ZABCDEMAILADDRESS` - emails
- `ZABCDPHONENUMBER` - phones
- `ZABCDURLADDRESS` - websites

**Key fields:**
```sql
ZFIRSTNAME, ZLASTNAME, ZORGANIZATION
ZMODIFICATIONDATE   -- Apple timestamp
```

**Sample query:**
```sql
SELECT ZFIRSTNAME, ZLASTNAME, ZORGANIZATION
FROM ZABCDRECORD
WHERE ZFIRSTNAME IS NOT NULL
ORDER BY ZMODIFICATIONDATE DESC LIMIT 20;
```

---

## Timestamp Cheat Sheet

| Source | Format | Conversion to EST |
|--------|--------|-------------------|
| Wispr Flow | UTC datetime | `datetime(timestamp, '-5 hours')` |
| Brave/Chrome | Microseconds since 1601 | `datetime(time/1000000-11644473600, 'unixepoch', '-5 hours')` |
| Apple (Screen Time, Notes, Contacts) | Seconds since 2001-01-01 | `datetime(time + 978307200, 'unixepoch', '-5 hours')` |
| iMessage | Nanoseconds since 2001-01-01 | `datetime(time/1000000000 + 978307200, 'unixepoch', '-5 hours')` |

---

## Cross-Reference Ideas

**What was I browsing when I dictated about X?**
```sql
-- Get dictation timestamp, then query browser history within ±5 minutes
```

**Daily timeline (all sources):**
```sql
-- Union queries from Wispr, Browser, Screen Time with normalized timestamps
```

**Rabbit holes (long browser sessions):**
```sql
SELECT url, visit_count,
       (SELECT COUNT(*) FROM visits WHERE visits.url = urls.id) as total_visits
FROM urls ORDER BY total_visits DESC;
```
