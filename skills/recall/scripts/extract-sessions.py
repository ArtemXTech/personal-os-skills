#!/usr/bin/env python3
"""Extract user messages from Claude Code or Codex session logs into QMD-friendly markdown.

Usage:
    python3 extract-sessions.py [--days 21] [--source DIR] [--output DIR]

Extracts only YOUR messages from Claude Code JSONL session logs.
Strips system tags, slash commands, and agent noise.
Creates one markdown file per session with timestamp headers.

Output files are named: YYYY-MM-DD-HHMM-{session_id_short}.md
Each file has frontmatter (date, session_id, title, type, messages count)
and each user message as its own ## section with timestamp.

After running, add as QMD collection:
    qmd collection add /path/to/output --name sessions
    qmd update && qmd embed
"""

import json
import glob
import os
import re
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLAUDE_BACKEND = "claude"
CODEX_BACKEND = "codex"

def _detect_backend():
    override = os.environ.get("SESSION_BACKEND", "").strip().lower()
    if override in {CLAUDE_BACKEND, CODEX_BACKEND}:
        return override
    cwd = os.getcwd()
    encoded = cwd.replace("/", "-")
    candidate = os.path.expanduser(f"~/.claude/projects/{encoded}")
    if os.path.isdir(candidate):
        return CLAUDE_BACKEND
    codex_sessions = os.path.expanduser("~/.codex/sessions")
    if os.path.isdir(codex_sessions):
        return CODEX_BACKEND
    return CLAUDE_BACKEND

def _detect_default_source():
    """Auto-detect Claude or Codex session source directory."""
    if _detect_backend() == CODEX_BACKEND:
        return os.path.expanduser("~/.codex/sessions")
    cwd = os.getcwd()
    encoded = cwd.replace("/", "-")
    candidate = os.path.expanduser(f"~/.claude/projects/{encoded}")
    if os.path.isdir(candidate):
        return candidate
    # Fallback: first project dir that exists
    projects_dir = os.path.expanduser("~/.claude/projects")
    if os.path.isdir(projects_dir):
        dirs = [d for d in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, d))]
        if dirs:
            return os.path.join(projects_dir, dirs[0])
    return projects_dir

def _detect_default_output():
    """Auto-detect output directory for QMD session markdown."""
    vault = os.environ.get("VAULT_DIR")
    if not vault:
        cwd = Path(os.getcwd())
        for parent in [cwd, *cwd.parents]:
            if (parent / ".obsidian").is_dir():
                vault = str(parent)
                break
    if vault:
        return os.path.join(vault, "Notes", "Projects", "claude-sessions-qmd")
    return os.path.expanduser("~/claude-sessions-qmd")

DEFAULT_SOURCE = _detect_default_source()
DEFAULT_OUTPUT = _detect_default_output()
DEFAULT_DAYS = 21
SESSION_BACKEND = _detect_backend()

# Patterns to strip from user messages
STRIP_PATTERNS = [
    r'<system-reminder>.*?</system-reminder>',
    r'<local-command-caveat>.*?</local-command-caveat>',
    r'<local-command-stdout>.*?</local-command-stdout>',
    r'<command-name>.*?</command-name>\s*<command-message>.*?</command-message>\s*(?:<command-args>.*?</command-args>)?',
]


def clean_content(text: str) -> str:
    """Strip system tags, keep only human-written content."""
    if not isinstance(text, str):
        return ""
    for pat in STRIP_PATTERNS:
        text = re.sub(pat, '', text, flags=re.DOTALL)
    text = text.strip()
    return text


def derive_title(messages: list[dict]) -> str:
    """Derive a short title from the first meaningful user message."""
    for msg in messages:
        content = msg['content']
        # Skip very short messages
        if len(content) < 10:
            continue
        # Skip messages that are mostly handoff/context blocks
        if content.startswith('## Continue:') or content.startswith('**IMPORTANT'):
            # Extract the title from handoff blocks
            m = re.match(r'## Continue:\s*(.+?)(?:\n|$)', content)
            if m:
                return m.group(1).strip()[:80]
            continue
        # Take first line, clean it up
        first_line = content.split('\n')[0].strip()
        # Remove markdown headers
        first_line = re.sub(r'^#+\s*', '', first_line)
        # Truncate to 80 chars
        if len(first_line) > 80:
            first_line = first_line[:77] + '...'
        if len(first_line) >= 5:
            return first_line
    return "Untitled session"


def extract_session(filepath: str) -> dict | None:
    """Extract user messages from a single Claude or Codex JSONL session file."""
    messages = []
    session_id = None
    first_ts = None

    with open(filepath) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            if SESSION_BACKEND == CODEX_BACKEND:
                if obj.get('type') == 'session_meta' and not session_id:
                    session_id = obj.get('payload', {}).get('id')
                    first_ts = first_ts or obj.get('payload', {}).get('timestamp') or obj.get('timestamp', '')
                    continue
                if obj.get('type') != 'response_item':
                    continue
                payload = obj.get('payload', {})
                if payload.get('type') != 'message' or payload.get('role') != 'user':
                    continue
                blocks = payload.get('content', [])
                content = "\n".join(
                    item.get('text', '')
                    for item in blocks
                    if isinstance(item, dict) and item.get('type') == 'input_text'
                )
                timestamp = obj.get('timestamp', '')
            else:
                if not session_id and obj.get('sessionId'):
                    session_id = obj['sessionId']
                if obj.get('type') != 'user':
                    continue
                if obj.get('message', {}).get('role') != 'user':
                    continue
                content = obj['message'].get('content', '')
                timestamp = obj.get('timestamp', '')

            cleaned = clean_content(content)
            if not cleaned or len(cleaned) < 5:
                continue

            # Skip pure slash commands with no substance
            if re.match(r'^/\w+\s*$', cleaned):
                continue

            if not first_ts and timestamp:
                first_ts = timestamp

            messages.append({
                'content': cleaned,
                'timestamp': timestamp,
            })

    if not messages:
        return None

    return {
        'session_id': session_id or Path(filepath).stem,
        'first_ts': first_ts,
        'messages': messages,
        'filepath': filepath,
    }


def format_timestamp(ts_str: str) -> str:
    """Parse ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M')
    except:
        return ''


def write_session_md(session: dict, output_dir: str) -> str:
    """Write a session's user messages as structured markdown."""
    ts = session['first_ts']
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%H%M')
    except:
        date_str = 'unknown'
        time_str = '0000'

    title = derive_title(session['messages'])
    sid_short = session['session_id'][:8]
    filename = f"{date_str}-{time_str}-{sid_short}.md"
    filepath = os.path.join(output_dir, filename)

    lines = []
    lines.append('---')
    lines.append(f'date: {date_str}')
    lines.append(f'session_id: {session["session_id"]}')
    lines.append(f'title: "{title}"')
    lines.append(f'type: session-log')
    lines.append(f'messages: {len(session["messages"])}')
    lines.append('---')
    lines.append('')
    lines.append(f'# {title}')
    lines.append('')

    for msg in session['messages']:
        ts_label = format_timestamp(msg['timestamp'])
        if ts_label:
            lines.append(f'## {ts_label}')
        else:
            lines.append('## Message')
        lines.append('')
        lines.append(msg['content'])
        lines.append('')

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

    return filepath


def main():
    parser = argparse.ArgumentParser(description='Extract user messages from Claude Code or Codex sessions')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS, help=f'How many days back to extract (default: {DEFAULT_DAYS})')
    parser.add_argument('--source', default=DEFAULT_SOURCE, help='Source directory with JSONL files')
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help='Output directory for markdown files')
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    if SESSION_BACKEND == CODEX_BACKEND:
        pattern = os.path.join(args.source, "**", "*.jsonl")
        all_files = glob.glob(pattern, recursive=True)
    else:
        pattern = os.path.join(args.source, "*.jsonl")
        all_files = glob.glob(pattern)

    # Filter by file modification time
    recent_files = []
    for f in all_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=timezone.utc)
        if mtime >= cutoff:
            recent_files.append(f)

    print(f"Found {len(recent_files)} session files from last {args.days} days (of {len(all_files)} total)")

    os.makedirs(args.output, exist_ok=True)

    extracted = 0
    skipped = 0
    total_messages = 0

    for filepath in sorted(recent_files):
        session = extract_session(filepath)
        if session is None:
            skipped += 1
            continue

        # Check if first timestamp is within our window
        if session['first_ts']:
            try:
                dt = datetime.fromisoformat(session['first_ts'].replace('Z', '+00:00'))
                if dt < cutoff:
                    skipped += 1
                    continue
            except:
                pass

        outpath = write_session_md(session, args.output)
        extracted += 1
        total_messages += len(session['messages'])

    print(f"Extracted: {extracted} sessions, {total_messages} messages")
    print(f"Skipped: {skipped} sessions (no user messages or sub-agents)")
    print(f"Output: {args.output}")


if __name__ == '__main__':
    main()
