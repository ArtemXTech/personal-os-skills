#!/usr/bin/env python3
"""Recall sessions by date from native Claude Code JSONL files.

Usage:
    recall-day.py list DATE_EXPR [--project PATH] [--all-projects] [--min-msgs N]
    recall-day.py expand SESSION_ID [--project PATH] [--all-projects] [--max-msgs N]

DATE_EXPR examples: yesterday, today, 2026-02-25, "last tuesday", "this week",
                    "last week", "3 days ago", "last 3 days"

Every Claude Code user has JSONL session files in ~/.claude/projects/.
No custom setup needed.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"

# Reuse from extract-sessions.py
STRIP_PATTERNS = [
    re.compile(r'<system-reminder>.*?</system-reminder>', re.DOTALL),
    re.compile(r'<local-command-caveat>.*?</local-command-caveat>', re.DOTALL),
    re.compile(r'<local-command-stdout>.*?</local-command-stdout>', re.DOTALL),
    re.compile(r'<command-name>.*?</command-name>\s*<command-message>.*?</command-message>\s*(?:<command-args>.*?</command-args>)?', re.DOTALL),
    re.compile(r'<task-notification>.*?</task-notification>', re.DOTALL),
    re.compile(r'<teammate-message[^>]*>.*?</teammate-message>', re.DOTALL),
]

DAY_NAMES = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
}


def clean_content(text: str) -> str:
    """Strip system tags, keep only human-written content."""
    if not isinstance(text, str):
        return ""
    for pat in STRIP_PATTERNS:
        text = pat.sub('', text)
    return text.strip()


def extract_text(content) -> str:
    """Extract text from message content (string or list of content blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'text':
                parts.append(block.get('text', ''))
            elif isinstance(block, str):
                parts.append(block)
        return '\n'.join(parts)
    return ""


def parse_date_expr(expr: str) -> tuple[datetime, datetime]:
    """Parse a date expression into (start, end) date range (UTC, day boundaries).

    Returns start of day (inclusive) and end of day (exclusive).
    """
    expr = expr.strip().lower()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if expr == 'today':
        return today_start, today_start + timedelta(days=1)

    if expr == 'yesterday':
        start = today_start - timedelta(days=1)
        return start, today_start

    # YYYY-MM-DD
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', expr)
    if m:
        d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        return d, d + timedelta(days=1)

    # "N days ago"
    m = re.match(r'^(\d+)\s+days?\s+ago$', expr)
    if m:
        n = int(m.group(1))
        start = today_start - timedelta(days=n)
        return start, start + timedelta(days=1)

    # "last N days"
    m = re.match(r'^last\s+(\d+)\s+days?$', expr)
    if m:
        n = int(m.group(1))
        start = today_start - timedelta(days=n)
        return start, today_start + timedelta(days=1)

    # "this week" (Monday-based)
    if expr == 'this week':
        monday = today_start - timedelta(days=today_start.weekday())
        return monday, today_start + timedelta(days=1)

    # "last week"
    if expr == 'last week':
        this_monday = today_start - timedelta(days=today_start.weekday())
        last_monday = this_monday - timedelta(days=7)
        return last_monday, this_monday

    # "last monday" .. "last sunday"
    m = re.match(r'^last\s+(\w+)$', expr)
    if m and m.group(1) in DAY_NAMES:
        target_dow = DAY_NAMES[m.group(1)]
        current_dow = today_start.weekday()
        days_back = (current_dow - target_dow) % 7
        if days_back == 0:
            days_back = 7
        start = today_start - timedelta(days=days_back)
        return start, start + timedelta(days=1)

    print(f"Error: Can't parse date expression: '{expr}'", file=sys.stderr)
    print("Supported: today, yesterday, YYYY-MM-DD, 'N days ago', 'last N days',", file=sys.stderr)
    print("           'this week', 'last week', 'last monday'...'last sunday'", file=sys.stderr)
    sys.exit(1)


def get_project_dirs(project_path: str | None, all_projects: bool) -> list[Path]:
    """Get list of project directories to scan."""
    if project_path:
        encoded = project_path.replace('/', '-')
        p = CLAUDE_PROJECTS / encoded
        if p.exists():
            return [p]
        # Try as-is
        p = Path(project_path)
        if p.exists():
            return [p]
        print(f"Error: Project path not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    if all_projects:
        return [d for d in CLAUDE_PROJECTS.iterdir() if d.is_dir()]

    # Default: detect project dir from CWD
    cwd = os.getcwd()
    encoded = cwd.replace("/", "-")
    default = CLAUDE_PROJECTS / encoded
    if default.exists():
        return [default]
    # Fallback: all projects
    return [d for d in CLAUDE_PROJECTS.iterdir() if d.is_dir()]


def scan_session_metadata(filepath: Path, date_start: datetime, date_end: datetime) -> dict | None:
    """Fast scan: read first ~30 lines for metadata, count user messages."""
    session_id = filepath.stem
    start_time = None
    first_user_msg = None
    user_msg_count = 0
    file_size = filepath.stat().st_size

    try:
        with open(filepath) as f:
            for i, line in enumerate(f):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Get session ID from data if available
                if obj.get('sessionId'):
                    session_id = obj['sessionId']

                ts_str = obj.get('timestamp')
                if ts_str and not start_time:
                    try:
                        start_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass

                # Count user messages and capture first
                if obj.get('type') == 'user' and obj.get('message', {}).get('role') == 'user':
                    user_msg_count += 1
                    if first_user_msg is None:
                        raw = extract_text(obj['message'].get('content', ''))
                        cleaned = clean_content(raw)
                        if cleaned and len(cleaned) >= 5:
                            # Skip pure slash commands
                            if not re.match(r'^/\w+\s*$', cleaned):
                                first_user_msg = cleaned

                # Early exit: if we have start_time and it's outside range, skip
                if start_time and i < 5:
                    if start_time >= date_end or start_time < date_start - timedelta(days=1):
                        return None

    except (OSError, UnicodeDecodeError):
        return None

    if not start_time:
        return None

    # Final date check
    if start_time < date_start or start_time >= date_end:
        return None

    # Derive title from first message
    title = "Untitled"
    if first_user_msg:
        first_line = first_user_msg.split('\n')[0].strip()
        first_line = re.sub(r'^#+\s*', '', first_line)
        if first_line.startswith('## Continue:'):
            m = re.match(r'## Continue:\s*(.+?)(?:\n|$)', first_user_msg)
            if m:
                first_line = m.group(1).strip()
        if len(first_line) > 80:
            first_line = first_line[:77] + '...'
        if len(first_line) >= 3:
            title = first_line

    return {
        'session_id': session_id,
        'start_time': start_time,
        'user_msg_count': user_msg_count,
        'file_size': file_size,
        'title': title,
        'filepath': str(filepath),
    }


def format_size(size_bytes: int) -> str:
    """Format file size human-readable."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def cmd_list(args):
    """List sessions for a date range."""
    date_start, date_end = parse_date_expr(args.date_expr)
    project_dirs = get_project_dirs(args.project, args.all_projects)

    sessions = []
    noise_count = 0
    total_scanned = 0

    for proj_dir in project_dirs:
        jsonl_files = list(proj_dir.glob("*.jsonl"))
        total_scanned += len(jsonl_files)

        for filepath in jsonl_files:
            # Coarse filter: mtime must be within range (with 1 day buffer)
            try:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
                if mtime < date_start - timedelta(days=1):
                    continue
            except OSError:
                continue

            meta = scan_session_metadata(filepath, date_start, date_end)
            if meta is None:
                continue

            if meta['user_msg_count'] < args.min_msgs:
                noise_count += 1
                continue

            sessions.append(meta)

    sessions.sort(key=lambda s: s['start_time'])

    # Format date range for header
    if date_end - date_start <= timedelta(days=1):
        header_date = date_start.strftime('%Y-%m-%d (%A)')
    else:
        header_date = f"{date_start.strftime('%Y-%m-%d')} to {(date_end - timedelta(days=1)).strftime('%Y-%m-%d')}"

    print(f"\nSessions for {header_date}\n")

    if not sessions:
        print("No sessions found.")
        if noise_count:
            print(f"({noise_count} filtered as noise, try --min-msgs 1)")
        return

    # Print table
    print(f" {'#':>2}  {'Time':5}  {'Msgs':>4}  {'Size':>6}  First Message")
    print(f" {'--':>2}  {'-----':5}  {'----':>4}  {'------':>6}  -------------")

    for i, s in enumerate(sessions, 1):
        time_str = s['start_time'].strftime('%H:%M')
        size_str = format_size(s['file_size'])
        title = s['title'][:60]
        sid_short = s['session_id'][:8]
        print(f" {i:2}  {time_str}  {s['user_msg_count']:4}  {size_str:>6}  {title}")

    print(f"\n{len(sessions)} sessions", end="")
    if noise_count:
        print(f" ({noise_count} filtered as noise)", end="")
    print()

    # Print session IDs for expand
    print(f"\nSession IDs (for expand):")
    for i, s in enumerate(sessions, 1):
        print(f"  {i:2}. {s['session_id'][:8]}")


def cmd_expand(args):
    """Expand a session by ID - show conversation summary."""
    project_dirs = get_project_dirs(args.project, args.all_projects)
    target_id = args.session_id.lower()

    # Find the JSONL file
    target_file = None
    for proj_dir in project_dirs:
        for filepath in proj_dir.glob("*.jsonl"):
            if filepath.stem.lower().startswith(target_id):
                target_file = filepath
                break
        if target_file:
            break

    if not target_file:
        print(f"Error: No session found matching '{args.session_id}'", file=sys.stderr)
        sys.exit(1)

    print(f"\nSession: {target_file.stem}")
    print(f"File: {target_file}")
    print()

    msg_count = 0
    max_msgs = args.max_msgs

    with open(target_file) as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get('type')
            msg = obj.get('message', {})
            role = msg.get('role')
            ts_str = obj.get('timestamp', '')

            # Format timestamp
            ts_label = ''
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    ts_label = dt.strftime('%H:%M')
                except (ValueError, TypeError):
                    pass

            if msg_type == 'user' and role == 'user':
                raw = extract_text(msg.get('content', ''))
                cleaned = clean_content(raw)
                if not cleaned or len(cleaned) < 5:
                    continue
                if re.match(r'^/\w+\s*$', cleaned):
                    continue

                msg_count += 1
                if max_msgs and msg_count > max_msgs:
                    print(f"\n... truncated at {max_msgs} messages (use --max-msgs to show more)")
                    break

                # Truncate long messages
                display = cleaned
                if len(display) > 200:
                    display = display[:197] + '...'
                display = display.replace('\n', '\n    ')

                print(f"[{ts_label}] USER: {display}")

            elif msg_type == 'assistant' and role == 'assistant':
                content = msg.get('content', [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get('type') == 'text':
                                text = block.get('text', '')
                                first_line = text.split('\n')[0][:120]
                                if first_line.strip():
                                    print(f"  [{ts_label}] ASST: {first_line}")
                                break
                            elif block.get('type') == 'tool_use':
                                tool_name = block.get('name', '?')
                                print(f"  [{ts_label}] TOOL: {tool_name}")

    print(f"\n{msg_count} user messages total")


def main():
    parser = argparse.ArgumentParser(
        description='Recall sessions by date from Claude Code JSONL files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # list
    p_list = sub.add_parser('list', help='List sessions for a date')
    p_list.add_argument('date_expr', nargs='+', help='Date expression (e.g. yesterday, today, 2026-02-25)')
    p_list.add_argument('--project', help='Project path to scan')
    p_list.add_argument('--all-projects', action='store_true', help='Scan all projects')
    p_list.add_argument('--min-msgs', type=int, default=3, help='Min user messages (default: 3)')

    # expand
    p_expand = sub.add_parser('expand', help='Expand a session by ID')
    p_expand.add_argument('session_id', help='Session ID (prefix match)')
    p_expand.add_argument('--project', help='Project path to scan')
    p_expand.add_argument('--all-projects', action='store_true', help='Scan all projects')
    p_expand.add_argument('--max-msgs', type=int, default=50, help='Max messages to show (default: 50)')

    args = parser.parse_args()

    if args.command == 'list':
        # Join multi-word date expressions
        args.date_expr = ' '.join(args.date_expr)
        cmd_list(args)
    elif args.command == 'expand':
        cmd_expand(args)


if __name__ == '__main__':
    main()
