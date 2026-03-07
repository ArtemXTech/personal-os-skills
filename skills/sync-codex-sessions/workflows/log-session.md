# Log Session

Annotate the current session with title, tags, status, rating, comments, and auto-summary.

## Behavior

- **Always generates summary** via haiku subagent (analyzes conversation)
- Reads valid tags from `schema/tags.yaml`
- Updates frontmatter via **Obsidian CLI** (atomic, no file read needed)
- Fields: title, tags, status, rating, comments, summary

## Via Voice/Text (Agent Workflow)

User says: "log session - Enhanced sync skill, done, implementation automation, 8"

Agent:
1. Parses intent from natural language:
   - title: "Enhanced sync skill"
   - status: done
   - tags: [implementation, automation]
   - rating: 8
   - comment: (auto-generated from context)
2. Reads `schema/tags.yaml` to validate tags
3. Runs haiku subagent to generate 2-3 line summary
4. **Updates via Obsidian CLI** (see below)

### Example Inputs

```
"log session - title: Built auth system, done, implementation, 9"
"log this - blocked on API, debugging"
"close session - shipped it, implementation, 8"
```

### Parsing Rules

- **Title:** after "title:" or first quoted phrase
- **Status:** done, active, blocked, handoff
- **Rating:** number 1-10
- **Tags:** match against schema/tags.yaml
- **Comment:** everything else, or auto-generate

## Update via Obsidian CLI

**Primary method** - atomic update, no file read race conditions:

```bash
# Update individual fields
obsidian property:set path="Codex-Sessions/2026-02-05-XXXXXXXX.md" name="title" value="New Title" type=text
obsidian property:set path="Codex-Sessions/2026-02-05-XXXXXXXX.md" name="status" value="done" type=text
obsidian property:set path="Codex-Sessions/2026-02-05-XXXXXXXX.md" name="tags" value='["implementation", "automation"]' type=list
obsidian property:set path="Codex-Sessions/2026-02-05-XXXXXXXX.md" name="rating" value="8" type=number
```

**Add comment** (append to existing - use eval for complex logic):

```bash
obsidian eval code="(async()=>{const f=app.vault.getAbstractFileByPath('Codex-Sessions/2026-02-05-XXXXXXXX.md');const ts=new Date().toISOString().slice(0,16).replace('T',' ');await app.fileManager.processFrontMatter(f,fm=>{const c=fm.comments||'';fm.comments=c?c+'\\n['+ts+'] New comment':'['+ts+'] New comment'});return 'updated'})()"
```

## Via CLI

```bash
# Add comment only
cxs note "got the sync working"

# Close session (mark done + comment)
cxs close "finished the feature"
```

## Finding Current Session

Get current session file path:
```bash
# From env
echo $CODEX_SESSION_ID

# Session file pattern
Codex-Sessions/YYYY-MM-DD-{session_id[:8]}.md
```

## Schema Reference

### Status Values

| Status | When to use |
|--------|-------------|
| `active` | Still working on this |
| `done` | Finished, goal achieved |
| `blocked` | Stuck, waiting for something |
| `handoff` | Branched to new session |

### Tags

See `schema/tags.yaml` for full list with descriptions and examples.

**Type tags:** research, implementation, debugging, planning, brainstorm, admin, quick, video, automation, writing

**Project tags:** lab, openclaw, personal, client

## Frontmatter Updated

```yaml
title: "Enhanced sync-codex-sessions with tags, rating, comments"
status: done
tags:
  - implementation
  - automation
rating: 8
comments: |
  [2026-02-05 14:30] Productive session - built new schema
```
