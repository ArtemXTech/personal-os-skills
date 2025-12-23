# TaskNotes Skill

Manage Obsidian tasks via the TaskNotes plugin HTTP API.

## Requirements

1. **TaskNotes Obsidian plugin** installed
2. **Enable HTTP API** in TaskNotes settings:
   - Open Obsidian Settings → TaskNotes
   - Enable "HTTP API"
   - Set API port (default: 8080)
   - API token: leave empty for no auth
3. **Python 3.11+** with `uv`

### Optional: API Authentication

If you set an API token in TaskNotes, create `.env` in your vault root:
```
TASKNOTES_API_KEY=your_token_here
```

## Usage

After installation, ask Claude:

```
"show my tasks"
"create a task to finish landing page"
"mark the landing page task as done"
"what should I work on?"
```

## Resources

- [Blog post](https://artemxtech.github.io/AI-Powered-Task-Management-in-Obsidian-(TaskNotes-+-Claude-Code))
- [Video demo](https://youtu.be/ePFAVGcPh7U)
