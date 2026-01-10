#!/usr/bin/env python3
"""Search Wispr Flow dictation history."""

import sqlite3
import argparse
from pathlib import Path

DB_PATH = Path.home() / "Library/Application Support/Wispr Flow/flow.sqlite"
TZ_OFFSET = "-5 hours"  # EST


def search(query, app=None, from_date=None, to_date=None, limit=20):
    conn = sqlite3.connect(DB_PATH)

    # Escape query for SQL LIKE
    safe_query = query.replace("'", "''")
    filters = [f"formattedText LIKE '%{safe_query}%'"]

    if app:
        safe_app = app.replace("'", "''")
        filters.append(f"app LIKE '%{safe_app}%'")
    if from_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') >= '{from_date}'")
    if to_date:
        filters.append(f"date(timestamp, '{TZ_OFFSET}') <= '{to_date}'")

    where = " AND ".join(filters)

    results = conn.execute(f"""
        SELECT
            datetime(timestamp, '{TZ_OFFSET}') as time,
            CASE
                WHEN app LIKE '%todesktop%' THEN 'Claude'
                WHEN app LIKE '%ghostty%' THEN 'Ghostty'
                WHEN app LIKE '%brave%' THEN 'Brave'
                WHEN app LIKE '%obsidian%' THEN 'Obsidian'
                WHEN app LIKE '%session%' THEN 'Session'
                ELSE COALESCE(SUBSTR(app, -20), 'Unknown')
            END as app_short,
            formattedText,
            numWords
        FROM History
        WHERE {where}
        ORDER BY timestamp DESC
        LIMIT {limit}
    """).fetchall()

    conn.close()
    return results


def main():
    parser = argparse.ArgumentParser(description="Search Wispr Flow history")
    parser.add_argument("query", help="Search term")
    parser.add_argument("--app", help="Filter by app (e.g., ghostty, brave)")
    parser.add_argument("--from", dest="from_date", help="From date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="To date (YYYY-MM-DD)")
    parser.add_argument("--limit", "-n", type=int, default=20, help="Max results (default: 20)")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Error: Wispr Flow database not found.")
        return 1

    results = search(args.query, args.app, args.from_date, args.to_date, args.limit)

    print(f"\n🔍 Search: '{args.query}' ({len(results)} results)")
    print("=" * 60)

    if not results:
        print("\nNo matches found.")
        return 0

    for time, app, text, words in results:
        words = words or 0
        print(f"\n📅 {time} | {app} | {words} words")
        # Highlight search term in context
        preview = text[:200] + ('...' if len(text) > 200 else '')
        print(f"   {preview}")

    print()
    return 0


if __name__ == "__main__":
    exit(main())
