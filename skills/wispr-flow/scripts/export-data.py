#!/usr/bin/env python3
"""Export Wispr Flow data to various formats."""

import sqlite3
import argparse
import json
from pathlib import Path

DB_PATH = Path.home() / "Library/Application Support/Wispr Flow/flow.sqlite"
TZ_OFFSET = "-5 hours"  # EST


def export_json(output, from_date=None, to_date=None):
    """Export to JSON (text only, no audio blobs)."""
    conn = sqlite3.connect(DB_PATH)

    filters = ["formattedText IS NOT NULL"]
    if from_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') >= '{from_date}'")
    if to_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') <= '{to_date}'")

    where = " AND ".join(filters)

    results = conn.execute(f"""
        SELECT
            transcriptEntityId as id,
            datetime(timestamp, '{TZ_OFFSET}') as timestamp,
            app,
            url,
            asrText,
            formattedText,
            editedText,
            duration,
            numWords
        FROM History
        WHERE {where}
        ORDER BY timestamp
    """).fetchall()

    data = []
    for row in results:
        data.append({
            "id": row[0],
            "timestamp": row[1],
            "app": row[2],
            "url": row[3],
            "asrText": row[4],
            "formattedText": row[5],
            "editedText": row[6],
            "duration": row[7],
            "numWords": row[8]
        })

    conn.close()

    output_path = Path(output).expanduser()
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    size_mb = output_path.stat().st_size / 1e6
    print(f"✅ Exported {len(data):,} dictations to {output_path}")
    print(f"   Size: {size_mb:.1f} MB")


def export_obsidian(output_dir, from_date=None, to_date=None):
    """Export to Obsidian daily notes format."""
    conn = sqlite3.connect(DB_PATH)

    filters = ["formattedText IS NOT NULL", "formattedText != ''"]
    if from_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') >= '{from_date}'")
    if to_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') <= '{to_date}'")

    where = " AND ".join(filters)

    results = conn.execute(f"""
        SELECT
            date(timestamp, '{TZ_OFFSET}') as day,
            time(timestamp, '{TZ_OFFSET}') as time,
            CASE
                WHEN app LIKE '%todesktop%' THEN 'Claude'
                WHEN app LIKE '%ghostty%' THEN 'Ghostty'
                WHEN app LIKE '%brave%' THEN 'Brave'
                WHEN app LIKE '%obsidian%' THEN 'Obsidian'
                WHEN app LIKE '%session%' THEN 'Session'
                ELSE COALESCE(app, 'Unknown')
            END as app_name,
            formattedText,
            numWords
        FROM History
        WHERE {where}
        ORDER BY timestamp
    """).fetchall()

    conn.close()

    # Group by day
    days = {}
    for day, time, app, text, words in results:
        if day not in days:
            days[day] = []
        days[day].append({"time": time, "app": app, "text": text, "words": words or 0})

    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    for day, entries in days.items():
        total_words = sum(e['words'] for e in entries)
        content = f"""---
type: voice-log
date: {day}
total_words: {total_words}
dictations: {len(entries)}
---

# Voice Log - {day}

Total: {total_words:,} words across {len(entries)} dictations

"""
        for e in entries:
            content += f"## {e['time'][:5]} ({e['app']})\n\n{e['text']}\n\n"

        filepath = output_path / f"{day} Voice Log.md"
        with open(filepath, 'w') as f:
            f.write(content)

    print(f"✅ Exported {len(days)} daily notes to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Export Wispr Flow data")
    parser.add_argument("--output", "-o", required=True, help="Output path (file for JSON, directory for Obsidian)")
    parser.add_argument("--format", "-f", choices=["json", "obsidian"], default="json", help="Export format")
    parser.add_argument("--from", dest="from_date", help="From date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="To date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Error: Wispr Flow database not found.")
        return 1

    if args.format == "json":
        export_json(args.output, args.from_date, args.to_date)
    elif args.format == "obsidian":
        export_obsidian(args.output, args.from_date, args.to_date)

    return 0


if __name__ == "__main__":
    exit(main())
