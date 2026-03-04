# Ask Notebook Workflow

Ask a NotebookLM notebook a question and save the answer as a vault reference note with `[N]` citations resolved to `[[wikilinks]]`.

## Inputs

- **question**: The question to ask
- **title**: Short title for the Q&A note (e.g. "Emerging Themes Across 20 Videos")
- **notebook-slug**: Which notebook folder to use
- **dashboard-title**: Dashboard to link to via `related`

If asking multiple questions, batch them into one note or create separate notes.

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Ask the Question

```bash
QA_FILE=$(mktemp /tmp/notebooklm-qa-XXXXXX.json)
notebooklm ask --new --json "{question}" > "$QA_FILE"
```

Flags:
- `--new`: Start a fresh conversation (prevents context leak from prior Q&A)
- `--json`: Get structured output with `references[]` for citation resolution

## Step 3: Extract Passages

```bash
PASSAGE_MAP=$(mktemp /tmp/notebooklm-passages-XXXXXX.json)
python3 .claude/skills/notebooklm/scripts/extract_passages.py \
  --qa "$QA_FILE" \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} > "$PASSAGE_MAP"
```

This writes `## Cited Passages / ### Passage N` sections into source files using the `cited_text` from references (the actual transcript chunks NotebookLM used as evidence). Idempotent - skips sources that already have passages. Outputs a passage mapping JSON for the resolver.

For multiple Q&As, pass all JSON files: `--qa /tmp/qa-1.json /tmp/qa-2.json ...`

## Step 4: Resolve Citations

```bash
python3 .claude/skills/notebooklm/scripts/resolve_citations.py \
  --qa "$QA_FILE" \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} \
  --passages "$PASSAGE_MAP" \
  --title "{title}" \
  --dashboard "{dashboard-title}" \
  --output "Notes/NotebookLM/{notebook-slug}/QA/{date} {title}.md"
```

This:
1. Deduplicates references by `cited_text` to find unique evidence chunks
2. Maps answer `[N]` to the Nth unique chunk (not to `citation_number` field)
3. Expands citation specs (`[1, 2]`, `[3-5]`) into individual numbers
4. Maps each chunk to its `source_id` -> source file title
5. Replaces `[N]` markers with `[[Source Title#Passage N]]` wikilinks (passage-level when `--passages` provided)
6. Writes a `reference` type note with resolved answer + sources table
7. Lists uncited sources separately (NotebookLM often cites only a subset)

**Known limitation:** NotebookLM's `references[]` often covers only a few sources even when the answer synthesizes across all of them. The resolver warns about this and lists uncited sources in a separate section.

## Step 5: Verify

Open the Q&A note in Obsidian and check:
- [ ] Wikilinks render (not raw `[N]` markers)
- [ ] Clicking a source wikilink opens the correct source file at the passage
- [ ] `#Passage N` anchors scroll to the cited evidence in source files
- [ ] Sources Referenced section at bottom lists all cited sources
- [ ] Uncited Sources section lists sources without granular citations

## Batch Mode

For multiple questions at once:

```python
questions = [
    {"question": "What are the main themes?", "title": "Main Themes"},
    {"question": "What tools are used?", "title": "Tools Compared"},
]

for q in questions:
    # Run notebooklm ask --new --json for each
    # Run extract_passages.py with ALL Q&A JSONs so far
    # Run resolve_citations.py with --passages for each
```

Each question gets `--new` to start a fresh conversation. Ask them in parallel if independent. Run extract_passages once with all Q&A files to accumulate passages.

## Output

- Q&A reference note at `Notes/NotebookLM/{notebook-slug}/QA/{date} {title}.md`
- All `[N]` citations resolved to `[[Source Title#Passage N]]` wikilinks (passage-level)
- Source files enriched with `## Cited Passages` sections containing the actual evidence
- Uncited sources listed separately
- `related` links to dashboard
