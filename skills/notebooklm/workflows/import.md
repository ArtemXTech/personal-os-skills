# Import Notebook Workflow

Import all sources from a NotebookLM notebook into the vault as linked `notebook-source` files with AI-generated guides, plus a dashboard.

## Inputs

- **notebook-slug**: short kebab-case name for the notebook (e.g. `obsidian-x-claude-code`)
- **dashboard-title**: human-readable title for the dashboard (e.g. `Obsidian x Claude Code Research`)

If user doesn't specify these, derive from `notebooklm status` output.

## Step 1: Verify Auth

```bash
notebooklm status
```

If auth error: run `notebooklm login` to re-authenticate.

## Step 2: Get Notebook Info

```bash
notebooklm status
# Note the notebook_id and title
```

## Step 3: Create Folder Structure

```bash
mkdir -p "Notes/NotebookLM/{notebook-slug}/Sources"
mkdir -p "Notes/NotebookLM/{notebook-slug}/QA"
```

## Step 4: Export Source List

```bash
SOURCES_FILE=$(mktemp /tmp/notebooklm-sources-XXXXXX.json)
notebooklm source list --json > "$SOURCES_FILE"
```

Inspect the JSON to understand the schema. Key fields: `id`, `title`, `type`, `url`, `created_at`.

## Step 5: Create Source Files

Run the import script:

```bash
python3 .claude/skills/notebooklm/scripts/import_sources.py \
  --sources "$SOURCES_FILE" \
  --slug {notebook-slug} \
  --dashboard "{dashboard-title}"
```

This creates one `.md` file per source with proper frontmatter and `related` linking to dashboard.

## Step 6: Fetch Source Guides

The import script also fetches AI-generated source guides via `notebooklm source guide {id} --json` and writes them into each file's `## Source Guide` section.

**Note:** This is sequential (one API call per source). For 20 sources, expect ~2-3 minutes.

## Step 7: Create Dashboard

Create `Notes/Dashboards/{dashboard-title}.md` using the dashboard template from `templates/dashboard.md`.

Replace `{notebook-slug}` in the Dataview queries with the actual slug.

## Step 8: Verify

```bash
# Check source count
ls "Notes/NotebookLM/{notebook-slug}/Sources/" | wc -l
```

Open the dashboard in Obsidian and verify Dataview queries render.

## Output

- `N` source files in `Notes/NotebookLM/{notebook-slug}/Sources/`
- Dashboard at `Notes/Dashboards/{dashboard-title}.md`
- Empty `QA/` folder ready for ask workflow
