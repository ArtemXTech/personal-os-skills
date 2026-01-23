# CLAUDE.md

Public repository of Claude Code skills for Obsidian workflows.

## Repo Structure

```
personal-os-skills/
├── .claude-plugin/
│   └── marketplace.json    # Plugin registry
├── skills/
│   └── <skill-name>/       # One folder per skill
│       ├── SKILL.md        # Required
│       ├── scripts/        # Optional
│       └── templates/      # Optional
├── docs/
├── README.md
└── CLAUDE.md
```

## Skill Folder Format

Each skill folder must contain:

```
<skill-name>/
├── SKILL.md                # Required: frontmatter with name + description
├── scripts/                # Optional: Python/bash scripts
└── templates/              # Optional: output templates
```

**SKILL.md frontmatter:**
```yaml
---
name: <skill-name>
description: One-line description. Include trigger phrases.
---
```

## Publishing a Skill

**Procedure:**

1. Copy skill folder to `skills/`
   ```bash
   cp -r <source-path>/<skill-name> skills/
   ```

2. Add to `marketplace.json` plugins array:
   ```json
   {
     "name": "<skill-name>-skill",
     "description": "What this skill does",
     "source": "./",
     "strict": false,
     "skills": ["./skills/<skill-name>"]
   }
   ```

3. Add row to README.md skills table:
   ```markdown
   | [<skill-name>](skills/<skill-name>/) | Description | Resources |
   ```

4. Commit and push

## Checklist

Before committing, verify consistency:

- [ ] Skill folder exists in `skills/`
- [ ] SKILL.md has valid frontmatter (name, description)
- [ ] Scripts are self-contained (no external pip dependencies)
- [ ] Entry added to `marketplace.json` plugins array
- [ ] Row added to README.md skills table
- [ ] All three locations match (skills/, marketplace.json, README.md)
