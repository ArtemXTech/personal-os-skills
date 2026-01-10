#!/usr/bin/env python3
"""Create interactive HTML dashboard for Wispr Flow data."""

import sqlite3
import argparse
import json
from pathlib import Path

DB_PATH = Path.home() / "Library/Application Support/Wispr Flow/flow.sqlite"
TZ_OFFSET = "-5 hours"  # EST


def create_dashboard(output):
    conn = sqlite3.connect(DB_PATH)

    # Overall stats
    stats = conn.execute(f"""
        SELECT
            COUNT(*) as total_dictations,
            COALESCE(SUM(numWords), 0) as total_words,
            ROUND(COALESCE(SUM(duration), 0)/3600.0, 1) as total_hours,
            date(MIN(timestamp), '{TZ_OFFSET}') as first_date,
            date(MAX(timestamp), '{TZ_OFFSET}') as last_date
        FROM History WHERE status != 'cancelled'
    """).fetchone()

    # Daily words
    daily = conn.execute(f"""
        SELECT date(timestamp, '{TZ_OFFSET}') as day, SUM(numWords) as words, COUNT(*) as count
        FROM History WHERE status != 'cancelled'
        GROUP BY day ORDER BY day
    """).fetchall()

    # Hourly pattern
    hourly = conn.execute(f"""
        SELECT strftime('%H', timestamp, '{TZ_OFFSET}') as hour, SUM(numWords) as words, COUNT(*) as count
        FROM History WHERE hour IS NOT NULL GROUP BY hour ORDER BY hour
    """).fetchall()

    # App breakdown
    apps = conn.execute(f"""
        SELECT
          CASE
            WHEN app LIKE '%todesktop%' THEN 'Claude Desktop'
            WHEN app LIKE '%ghostty%' THEN 'Ghostty'
            WHEN app LIKE '%brave%' THEN 'Brave'
            WHEN app LIKE '%obsidian%' THEN 'Obsidian'
            WHEN app LIKE '%session%' THEN 'Session'
            WHEN app LIKE '%zed%' THEN 'Zed'
            ELSE 'Other'
          END as app_name,
          SUM(numWords) as words
        FROM History GROUP BY app_name ORDER BY words DESC
    """).fetchall()

    conn.close()

    # Prepare JSON for charts
    daily_json = json.dumps([{'date': d[0], 'words': d[1] or 0} for d in daily])
    hourly_json = json.dumps([{'hour': h[0], 'words': h[1] or 0} for h in hourly if h[0]])
    app_json = json.dumps([{'app': a[0], 'words': a[1] or 0} for a in apps])

    # Create HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Wispr Flow Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            margin: 0;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #4A90D9; margin-bottom: 5px; }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 30px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; gap: 15px; }}
        .stat {{
            text-align: center;
            background: #16213e;
            padding: 20px 40px;
            border-radius: 12px;
            min-width: 120px;
        }}
        .stat-value {{ font-size: 2.5em; font-weight: bold; color: #4A90D9; }}
        .stat-label {{ color: #888; margin-top: 5px; }}
        .chart-container {{ background: #16213e; border-radius: 12px; padding: 20px; margin: 20px 0; }}
        .chart-row {{ display: flex; gap: 20px; flex-wrap: wrap; }}
        .chart-row > div {{ flex: 1; min-width: 300px; }}
        canvas {{ max-height: 300px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Wispr Flow Dashboard</h1>
        <p class="subtitle">{stats[3]} to {stats[4]}</p>

        <div class="stats">
            <div class="stat"><div class="stat-value">{stats[1]:,}</div><div class="stat-label">Total Words</div></div>
            <div class="stat"><div class="stat-value">{stats[0]:,}</div><div class="stat-label">Dictations</div></div>
            <div class="stat"><div class="stat-value">{stats[2]}h</div><div class="stat-label">Hours Speaking</div></div>
            <div class="stat"><div class="stat-value">{round(stats[1]/max(stats[0],1))}</div><div class="stat-label">Avg Words/Dict</div></div>
        </div>

        <div class="chart-container">
            <canvas id="dailyChart"></canvas>
        </div>

        <div class="chart-row">
            <div class="chart-container">
                <canvas id="hourlyChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="appChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const dailyData = {daily_json};
        const hourlyData = {hourly_json};
        const appData = {app_json};

        // Daily chart
        new Chart(document.getElementById('dailyChart'), {{
            type: 'line',
            data: {{
                labels: dailyData.map(d => d.date),
                datasets: [{{
                    label: 'Words per Day',
                    data: dailyData.map(d => d.words),
                    borderColor: '#4A90D9',
                    backgroundColor: 'rgba(74, 144, 217, 0.2)',
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{
                plugins: {{
                    title: {{ display: true, text: 'Daily Words Dictated', color: '#eee', font: {{size: 16}} }},
                    legend: {{ labels: {{ color: '#888' }} }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }},
                    y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }}
                }}
            }}
        }});

        // Hourly chart
        new Chart(document.getElementById('hourlyChart'), {{
            type: 'bar',
            data: {{
                labels: hourlyData.map(d => d.hour + ':00'),
                datasets: [{{
                    label: 'Words by Hour',
                    data: hourlyData.map(d => d.words),
                    backgroundColor: hourlyData.map(d =>
                        parseInt(d.hour) >= 20 || parseInt(d.hour) <= 4 ? '#E74C3C' : '#4A90D9'
                    )
                }}]
            }},
            options: {{
                plugins: {{
                    title: {{ display: true, text: 'When You Dictate (Night = Red)', color: '#eee', font: {{size: 16}} }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }},
                    y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#333' }} }}
                }}
            }}
        }});

        // App chart
        new Chart(document.getElementById('appChart'), {{
            type: 'doughnut',
            data: {{
                labels: appData.map(d => d.app),
                datasets: [{{
                    data: appData.map(d => d.words),
                    backgroundColor: ['#4A90D9', '#E74C3C', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C', '#34495E']
                }}]
            }},
            options: {{
                plugins: {{
                    title: {{ display: true, text: 'Words by App', color: '#eee', font: {{size: 16}} }},
                    legend: {{ labels: {{ color: '#888' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''

    output_path = Path(output).expanduser()
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"✅ Created dashboard: {output_path}")
    print("   Open in browser to view interactive charts")


def main():
    parser = argparse.ArgumentParser(description="Create Wispr Flow dashboard")
    parser.add_argument("--output", "-o", default="~/Downloads/wispr-dashboard.html", help="Output HTML file")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("Error: Wispr Flow database not found.")
        return 1

    create_dashboard(args.output)
    return 0


if __name__ == "__main__":
    exit(main())
