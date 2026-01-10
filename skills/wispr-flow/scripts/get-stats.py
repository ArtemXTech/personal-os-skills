#!/usr/bin/env python3
"""Get Wispr Flow statistics."""

import sqlite3
import argparse
import json
from pathlib import Path

DB_PATH = Path.home() / "Library/Application Support/Wispr Flow/flow.sqlite"
TZ_OFFSET = "-5 hours"  # EST


def get_stats(period=None):
    conn = sqlite3.connect(DB_PATH)

    # Build date filter
    date_filter = ""
    if period == "today":
        date_filter = f"AND date(timestamp, '{TZ_OFFSET}') = date('now', '{TZ_OFFSET}')"
    elif period == "week":
        date_filter = f"AND date(timestamp, '{TZ_OFFSET}') >= date('now', '{TZ_OFFSET}', '-7 days')"
    elif period == "month":
        date_filter = f"AND date(timestamp, '{TZ_OFFSET}') >= date('now', '{TZ_OFFSET}', '-30 days')"

    # Overall stats
    stats = conn.execute(f"""
        SELECT
            COUNT(*) as total_dictations,
            COALESCE(SUM(numWords), 0) as total_words,
            ROUND(COALESCE(SUM(duration), 0)/3600.0, 1) as total_hours,
            ROUND(COALESCE(AVG(numWords), 0), 1) as avg_words,
            date(MIN(timestamp), '{TZ_OFFSET}') as first_date,
            date(MAX(timestamp), '{TZ_OFFSET}') as last_date
        FROM History
        WHERE status != 'cancelled' {date_filter}
    """).fetchone()

    # Top apps (with friendly names)
    apps = conn.execute(f"""
        SELECT
            CASE
                WHEN app LIKE '%todesktop%' THEN 'Claude Desktop'
                WHEN app LIKE '%ghostty%' THEN 'Ghostty'
                WHEN app LIKE '%brave%' THEN 'Brave'
                WHEN app LIKE '%obsidian%' THEN 'Obsidian'
                WHEN app LIKE '%session%' THEN 'Session'
                WHEN app LIKE '%zed%' THEN 'Zed'
                WHEN app LIKE '%cursor%' THEN 'Cursor'
                WHEN app LIKE '%Terminal%' THEN 'Terminal'
                WHEN app IS NULL OR app = '' THEN 'Unknown'
                ELSE app
            END as app_name,
            COUNT(*) as count,
            SUM(numWords) as words
        FROM History
        WHERE status != 'cancelled' {date_filter}
        GROUP BY app_name
        ORDER BY words DESC
        LIMIT 10
    """).fetchall()

    # Daily breakdown
    daily = conn.execute(f"""
        SELECT
            date(timestamp, '{TZ_OFFSET}') as day,
            COUNT(*) as dictations,
            SUM(numWords) as words,
            ROUND(SUM(duration)/60.0, 1) as minutes
        FROM History
        WHERE status != 'cancelled' {date_filter}
        GROUP BY day
        ORDER BY day DESC
        LIMIT 7
    """).fetchall()

    # Hourly pattern
    hourly = conn.execute(f"""
        SELECT
            strftime('%H', timestamp, '{TZ_OFFSET}') as hour,
            COUNT(*) as count,
            SUM(numWords) as words
        FROM History
        WHERE status != 'cancelled' {date_filter}
        GROUP BY hour
        ORDER BY hour
    """).fetchall()

    conn.close()

    return {
        "period": period or "all",
        "total_dictations": stats[0],
        "total_words": stats[1],
        "total_hours": stats[2],
        "avg_words_per_dictation": stats[3],
        "first_date": stats[4],
        "last_date": stats[5],
        "top_apps": [{"app": a[0], "count": a[1], "words": a[2]} for a in apps],
        "daily": [{"date": d[0], "dictations": d[1], "words": d[2], "minutes": d[3]} for d in daily],
        "hourly": [{"hour": h[0], "count": h[1], "words": h[2]} for h in hourly if h[0]]
    }


def print_stats(stats):
    print(f"\n🎙️  Wispr Flow Stats ({stats['period']})")
    print("=" * 50)
    print(f"\n📊 Overview:")
    print(f"   Dictations:  {stats['total_dictations']:,}")
    print(f"   Total Words: {stats['total_words']:,}")
    print(f"   Hours:       {stats['total_hours']}h")
    print(f"   Avg/Dict:    {stats['avg_words_per_dictation']} words")
    print(f"   Period:      {stats['first_date']} to {stats['last_date']}")

    print(f"\n📱 Top Apps:")
    for app in stats['top_apps'][:7]:
        words = app['words'] or 0
        print(f"   {app['app']:20} {words:,} words ({app['count']} dictations)")

    print(f"\n📅 Recent Days:")
    for day in stats['daily'][:7]:
        words = day['words'] or 0
        print(f"   {day['date']}: {words:,} words ({day['dictations']} dict, {day['minutes']}min)")

    # Find peak hours
    if stats['hourly']:
        peak = max(stats['hourly'], key=lambda x: x['count'])
        print(f"\n⏰ Peak Hour: {peak['hour']}:00 ({peak['count']} dictations)")

    print()


def main():
    parser = argparse.ArgumentParser(description="Wispr Flow statistics")
    parser.add_argument("--period", choices=["today", "week", "month"], help="Time period")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Error: Wispr Flow database not found.")
        print(f"Expected: {DB_PATH}")
        return 1

    stats = get_stats(args.period)

    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print_stats(stats)

    return 0


if __name__ == "__main__":
    exit(main())
