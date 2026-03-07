# Personal OS Skills

Claude Code skills for Obsidian workflows, with initial Codex support for session-based memory tools.

> **Claude Code x Obsidian Lab** - 6 weeks, 12 live sessions. [lab.artemzhutov.com](https://lab.artemzhutov.com/)

## Installation

### Claude Code

1. Add marketplace (run in Claude Code):
   ```
   /plugin marketplace add ArtemXTech/personal-os-skills
   ```
2. Run `/plugin` in Claude Code
3. Go to **Discover** tab, find the skill
4. Select **Install for you (user scope)**
5. Restart Claude Code

### Codex

Use Codex's built-in skill installer with the skill path you want from this repo.

Example:

```bash
python3 ~/.codex/skills/skill-installer/scripts/install-skill-from-github.py \
  --repo ArtemXTech/personal-os-skills \
  --path skills/recall \
  --path skills/sync-claude-sessions
```

Restart Codex after installation.

## Python Setup

The graph and session scripts now use a minimal `uv` project:

```bash
cd personal-os-skills
uv sync
```

Run scripts with `uv run`, for example:

```bash
uv run python skills/recall/scripts/session-graph.py today --min-msgs 1 --min-files 1
```

For Codex-specific memory workflows, use the helper wrapper:

```bash
uv run python scripts/codex-memory recall-day today --min-msgs 1
uv run python scripts/codex-memory sync-sessions export --all
uv run python scripts/codex-memory session-graph last week
```

## Available Skills

| Skill | Description | Resources |
|-------|-------------|-----------|
| [granola](skills/granola/) | Sync Granola meeting notes to Obsidian | Local cache, no API needed |
| [wispr-flow](skills/wispr-flow/) | Analyze voice dictation data from Wispr Flow | Stats, search, export, dashboard |
| [tasknotes](docs/tasknotes/) | Manage Obsidian tasks via TaskNotes API | [Video](https://youtu.be/ePFAVGcPh7U) · [Blog](https://artemxtech.github.io/AI-Powered-Task-Management-in-Obsidian-(TaskNotes-+-Claude-Code)) |
| [notebooklm](skills/notebooklm/) | Import NotebookLM notebooks into Obsidian as linked knowledge graphs | [Video](https://youtu.be/qiOu7Ptjxng) |
| [recall](skills/recall/) | Load context from previous sessions - Claude Code and Codex temporal recall, plus topic search (QMD) and graph visualization | [Video](https://youtu.be/RDoTY4_xh0s) · [Setup](docs/memory-skills-setup.md) |
| [sync-claude-sessions](skills/sync-claude-sessions/) | Export Claude Code or Codex conversations to Obsidian markdown with sync/resume helpers | [Setup](docs/memory-skills-setup.md) |

## Links

- [YouTube](https://www.youtube.com/@artemxtech)
- [Discord](https://discord.gg/g5Z4Wk2fDk)

## License

MIT
