# Database Schema

## Tables

- `History` - main table with all dictations
- `Dictionary` - custom words/phrases
- `Notes` - saved notes
- `FlowLensHistory` - AI suggestions history
- `RemoteNotifications` - push notifications

## History Table (Main)

```sql
CREATE TABLE History (
    transcriptEntityId VARCHAR(36) PRIMARY KEY,
    asrText TEXT,               -- Raw ASR output
    formattedText TEXT,         -- AI-formatted text
    editedText TEXT,            -- User's final edit
    timestamp DATETIME,         -- UTC timestamp
    audio BLOB,                 -- Raw audio recording
    screenshot BLOB,            -- Context screenshot
    additionalContext JSON,     -- Extra context
    status VARCHAR(255),        -- completed, cancelled, etc.
    app VARCHAR(255),           -- Active application bundle ID
    url VARCHAR(255),           -- Active URL (browser)
    e2eLatency FLOAT,           -- End-to-end latency
    duration FLOAT,             -- Recording duration (seconds)
    numWords INTEGER,           -- Word count
    language TEXT,              -- Detected language
    micDevice TEXT,             -- Microphone used
    conversationId VARCHAR(255) -- Conversation grouping
    -- ... additional metadata fields
);
```

## Useful Queries

### Recent dictations with context
```sql
SELECT
    datetime(timestamp, '-5 hours') as time,
    app,
    numWords,
    substr(formattedText, 1, 100) as preview
FROM History
ORDER BY timestamp DESC
LIMIT 20;
```

### Words by app
```sql
SELECT
    app,
    COUNT(*) as dictations,
    SUM(numWords) as total_words,
    ROUND(AVG(numWords), 1) as avg_words
FROM History
WHERE app IS NOT NULL
GROUP BY app
ORDER BY total_words DESC;
```

### Daily summary
```sql
SELECT
    date(timestamp, '-5 hours') as day,
    COUNT(*) as dictations,
    SUM(numWords) as words,
    ROUND(SUM(duration)/60, 1) as minutes
FROM History
GROUP BY day
ORDER BY day DESC
LIMIT 30;
```

### Hourly pattern
```sql
SELECT
    strftime('%H', timestamp, '-5 hours') as hour,
    COUNT(*) as count,
    SUM(numWords) as words
FROM History
GROUP BY hour
ORDER BY hour;
```

### Search text
```sql
SELECT
    datetime(timestamp, '-5 hours') as time,
    app,
    formattedText
FROM History
WHERE formattedText LIKE '%search term%'
ORDER BY timestamp DESC
LIMIT 10;
```

### Size analysis
```sql
SELECT
    COUNT(*) as total,
    ROUND(SUM(LENGTH(audio))/1e9, 2) as audio_gb,
    ROUND(SUM(LENGTH(screenshot))/1e9, 2) as screenshot_gb,
    ROUND(SUM(LENGTH(formattedText))/1e6, 2) as text_mb
FROM History;
```
