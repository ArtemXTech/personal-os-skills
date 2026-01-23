#!/usr/bin/env python3
"""
Granola CLI - Query and sync Granola meetings to Obsidian.

Reads from local Granola cache (no API needed).

Usage:
    python3 granola.py list                    # List all meetings
    python3 granola.py list --limit 5          # List last 5 meetings
    python3 granola.py get <id>                # Get full meeting with transcript
    python3 granola.py sync                    # Sync new meetings to vault
    python3 granola.py sync --id <id>          # Sync specific meeting
    python3 granola.py sync --all              # Re-sync all meetings

Examples:
    python3 granola.py list
    python3 granola.py get f5f1d2f9-4920-4670-8e3e-f356bd58e1b4
    python3 granola.py sync --id f5f1d2f9-4920-4670-8e3e-f356bd58e1b4
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Configuration
CACHE_PATH = Path.home() / "Library/Application Support/Granola/cache-v3.json"
# Auto-detect vault path from script location (.claude/skills/granola/scripts/granola.py)
VAULT_PATH = Path(__file__).resolve().parents[4]
MEETINGS_FOLDER = VAULT_PATH / "Meetings"
TEMPLATE_PATH = Path(__file__).parent.parent / "templates/granola-meeting.md"


def load_cache() -> dict:
    """Load and parse Granola cache file."""
    if not CACHE_PATH.exists():
        print(f"Error: Granola cache not found at {CACHE_PATH}")
        print("Make sure Granola is installed and you've logged in.")
        sys.exit(1)

    data = json.loads(CACHE_PATH.read_text())
    inner = json.loads(data["cache"])
    return inner.get("state", {})


def get_documents(state: dict) -> dict:
    """Get all documents from state."""
    return state.get("documents", {})


def get_transcripts(state: dict) -> dict:
    """Get all transcripts from state."""
    return state.get("transcripts", {})


def format_duration(segments: list) -> int:
    """Calculate duration in minutes from transcript segments."""
    if not segments:
        return 0

    first_ts = segments[0].get("start_timestamp", "")
    last_ts = segments[-1].get("end_timestamp", "")

    try:
        start = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
        end = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        return int((end - start).total_seconds() / 60)
    except (ValueError, TypeError):
        return 0


def format_transcript(segments: list) -> str:
    """Format transcript segments into readable text with local time."""
    lines = []
    for seg in segments:
        text = seg.get("text", "").strip()
        source = seg.get("source", "unknown")
        ts = seg.get("start_timestamp", "")

        # Parse timestamp and convert to local time for display
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            # Convert to local time (naive datetime for display)
            local_dt = dt.astimezone()
            time_str = local_dt.strftime("%H:%M:%S")
        except (ValueError, TypeError):
            time_str = "??:??:??"

        # Mark source (microphone vs system audio)
        source_icon = "🎤" if source == "microphone" else "🔊"
        lines.append(f"[{time_str}] {source_icon} {text}")

    return "\n".join(lines)


def extract_people(doc: dict) -> list[str]:
    """Extract attendee names from document."""
    people_data = doc.get("people", {})
    attendees = people_data.get("attendees", [])

    names = []
    for att in attendees:
        if isinstance(att, dict):
            name = att.get("name") or att.get("email", "").split("@")[0]
            if name:
                names.append(name)
        elif isinstance(att, str):
            names.append(att)

    return names


def cmd_list(args):
    """List all Granola meetings."""
    state = load_cache()
    docs = get_documents(state)
    transcripts = get_transcripts(state)

    if not docs:
        print("No meetings found in Granola cache.")
        return 0

    # Sort by created_at descending
    sorted_docs = sorted(
        docs.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True
    )

    if args.limit:
        sorted_docs = sorted_docs[:args.limit]

    print(f"Found {len(docs)} meetings:\n")

    for doc_id, doc in sorted_docs:
        title = doc.get("title") or "Untitled"
        created = doc.get("created_at", "")[:10]
        seg_count = len(transcripts.get(doc_id, []))
        duration = format_duration(transcripts.get(doc_id, []))

        # Check if already synced
        synced = "✓" if is_synced(doc_id) else " "

        print(f"[{synced}] {created}  {title}")
        print(f"    ID: {doc_id}")
        print(f"    Transcript: {seg_count} segments, ~{duration} min")
        print()

    return 0


def cmd_get(args):
    """Get full meeting details with transcript."""
    state = load_cache()
    docs = get_documents(state)
    transcripts = get_transcripts(state)

    doc_id = args.id

    if doc_id not in docs:
        print(f"Error: Meeting not found: {doc_id}")
        return 1

    doc = docs[doc_id]
    transcript = transcripts.get(doc_id, [])

    title = doc.get("title") or "Untitled"
    created = doc.get("created_at", "")
    notes = doc.get("notes_markdown") or doc.get("notes_plain", "")
    people = extract_people(doc)
    duration = format_duration(transcript)

    print(f"# {title}")
    print(f"Date: {created[:10]}")
    print(f"Duration: ~{duration} min")
    print(f"People: {', '.join(people) if people else 'None'}")
    print(f"Transcript segments: {len(transcript)}")
    print()

    if notes:
        print("## Notes")
        print(notes)
        print()

    if transcript and not args.no_transcript:
        print("## Transcript")
        print(format_transcript(transcript))

    return 0


def is_synced(doc_id: str) -> bool:
    """Check if a meeting is already synced to vault."""
    for f in MEETINGS_FOLDER.glob("*.md"):
        try:
            content = f.read_text()
            if f"granola_id: {doc_id}" in content:
                return True
        except:
            pass
    return False


def sync_meeting(doc: dict, transcript: list, force: bool = False) -> Path | None:
    """Sync a single meeting to vault. Returns path if created."""
    doc_id = doc["id"]

    # Check if already synced
    if not force and is_synced(doc_id):
        return None

    title = doc.get("title") or "Untitled"
    created = doc.get("created_at", "")
    notes = doc.get("notes_markdown") or doc.get("notes_plain", "")
    people = extract_people(doc)
    duration = format_duration(transcript)

    # Parse date/time and convert to local time
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        local_dt = dt.astimezone()  # Convert to local timezone
        date_str = local_dt.strftime("%Y-%m-%d")
        time_str = local_dt.strftime("%H%M")
    except (ValueError, TypeError):
        local_dt = None
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = "0000"

    # Clean title for filename
    clean_title = re.sub(r'[<>:"/\\|?*]', '', title)[:50]

    # Build filename
    filename = f"{date_str} {time_str} {clean_title}.md"
    filepath = MEETINGS_FOLDER / filename

    # Format people for frontmatter
    people_yaml = "\n".join([f'  - "[[{p}]]"' for p in people]) if people else ""

    # Build content
    content = f"""---
type: granola-meeting
date: {date_str}
time: "{local_dt.strftime('%H:%M') if local_dt else time_str}"
duration_min: {duration}
granola_id: {doc_id}
people:
{people_yaml}
topics: []
status: raw
---

# {title}

## Notes

{notes.strip() if notes else "(No notes taken)"}

## Transcript

{format_transcript(transcript) if transcript else "(No transcript)"}
"""

    # Ensure folder exists
    MEETINGS_FOLDER.mkdir(parents=True, exist_ok=True)

    # Write file
    filepath.write_text(content)

    return filepath


def cmd_sync(args):
    """Sync Granola meetings to vault."""
    state = load_cache()
    docs = get_documents(state)
    transcripts = get_transcripts(state)

    if not docs:
        print("No meetings found in Granola cache.")
        return 0

    synced = []
    skipped = []

    # Filter to specific ID if provided
    if args.id:
        if args.id not in docs:
            print(f"Error: Meeting not found: {args.id}")
            return 1
        items = [(args.id, docs[args.id])]
    else:
        items = docs.items()

    for doc_id, doc in items:
        transcript = transcripts.get(doc_id, [])

        result = sync_meeting(doc, transcript, force=args.all)

        if result:
            synced.append((doc.get("title", "Untitled"), result))
        else:
            skipped.append(doc.get("title", "Untitled"))

    # Report results
    if synced:
        print(f"Synced {len(synced)} meetings:\n")
        for title, path in synced:
            print(f"  ✓ {title}")
            print(f"    → {path.name}")
        print()

    if skipped and not args.id:
        print(f"Skipped {len(skipped)} (already synced)")

    if not synced and not skipped:
        print("Nothing to sync.")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Granola CLI - Query and sync meetings to Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                    List all meetings
  %(prog)s list --limit 5          List last 5 meetings
  %(prog)s get <id>                Get full meeting with transcript
  %(prog)s sync                    Sync new meetings to vault
  %(prog)s sync --id <id>          Sync specific meeting
  %(prog)s sync --all              Re-sync all meetings (overwrites)
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    list_parser = subparsers.add_parser("list", help="List all meetings")
    list_parser.add_argument("-n", "--limit", type=int, help="Limit number of results")

    # get command
    get_parser = subparsers.add_parser("get", help="Get full meeting details")
    get_parser.add_argument("id", help="Meeting ID (from list command)")
    get_parser.add_argument("--no-transcript", action="store_true", help="Skip transcript output")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync meetings to vault")
    sync_parser.add_argument("--id", help="Sync specific meeting by ID")
    sync_parser.add_argument("--all", action="store_true", help="Re-sync all (overwrites existing)")

    args = parser.parse_args()

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "get":
        return cmd_get(args)
    elif args.command == "sync":
        return cmd_sync(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
