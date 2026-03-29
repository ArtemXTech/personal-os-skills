---
name: notebooklm
description: Import NotebookLM notebooks into your Obsidian vault as linked knowledge graphs. Sources become wikilink-able files, Q&A answers get citations resolved to [[wikilinks]] with passage-level deep links. Use when user says "notebooklm import", "import notebook", "notebooklm ask", "notebooklm sources", or wants to turn NotebookLM research into vault knowledge.
---

# NotebookLM - Vault Knowledge Graph

> **Claude Code CLI only.** This skill runs Python scripts via Bash and requires `notebooklm-py` + Playwright installed locally. It will not work in Claude Cowork or other browser-based interfaces — those fall back to Computer Use, which cannot substitute for local subprocess execution.

Turn NotebookLM notebooks into persistent, linked vault knowledge. Sources become files you can `[[wikilink]]`, Q&A answers get `[N]` citations resolved to those wikilinks, dashboards tie it all together.

## Prerequisites

### 1. Install notebooklm-py

```bash
pip install "notebooklm-py[browser]"
playwright install chromium
```

### 2. Authenticate

```bash
notebooklm login
```

Opens a browser window - log in with your Google account. Cookies are saved to `~/.notebooklm/storage_state.json`.

Re-run `notebooklm login` when cookies expire (you'll see auth errors).

### 3. Obsidian Plugins

- **Dataview** (required) - citation tables and dashboard queries use Dataview/DataviewJS

### 4. Vault Setup

Copy the templates from `templates/` into your vault:
- `templates/notebook-source.md` -> `Templates/Types/notebook-source.md`
- `templates/dashboard.md` -> use as reference when creating dashboards

## Quick Start

```bash
# Check current notebook
notebooklm status

# Switch notebook
notebooklm use <notebook-id>

# List notebooks
notebooklm list
```

## Workflow Routing

| User says | Workflow |
|-----------|----------|
| "import notebook", "notebooklm import", "import sources" | [workflows/import.md](workflows/import.md) |
| "notebooklm ask", "ask notebook", "Q&A" | [workflows/ask.md](workflows/ask.md) |

## Architecture

```
Your Vault
├── Notes/NotebookLM/{notebook-slug}/
│   ├── Sources/          # One .md per source (YouTube, PDF, web, etc.)
│   │   ├── Video Title.md
│   │   └── Article Title.md
│   └── QA/               # Q&A notes with resolved citations
│       └── 2026-02-23 Emerging Themes.md
└── Notes/Dashboards/
    └── My Research.md     # Dashboard with Dataview queries
```

- **Source files** have type `notebook-source` with frontmatter: `source_id`, `notebook_id`, `url`, `source_type`, topics as `[[wikilinks]]`
- **Q&A notes** have type `reference` with `[N]` citations resolved to `[[Source Title#Passage N]]` wikilinks
- **Dashboards** use Dataview queries to list sources and Q&A notes

## Data Model

**notebook-source frontmatter:**
```yaml
type: notebook-source
source_id: "uuid"        # NotebookLM source ID
notebook_id: "uuid"      # NotebookLM notebook ID
url: ""                  # Original URL
source_type: youtube     # youtube, pdf, web, text, gdocs, gslides
status: active
date: YYYY-MM-DD
topics:
  - "[[Topic Name]]"     # AI-extracted topics as wikilinks
related:
  - "[[Notes/Dashboards/Dashboard Name]]"
```

**Q&A reference frontmatter:**
```yaml
type: reference
status: current
date: YYYY-MM-DD
source: "notebooklm:{notebook-slug}"
related:
  - "[[Notes/Dashboards/Dashboard Name]]"
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/import_sources.py` | Import sources as vault files with AI-generated guides and topics |
| `scripts/extract_passages.py` | Extract cited passages from Q&A into source files |
| `scripts/resolve_citations.py` | Replace `[N]` markers with `[[wikilinks]]` in Q&A answers |

All scripts use `Path.cwd()` as vault root - run them from your vault directory.
