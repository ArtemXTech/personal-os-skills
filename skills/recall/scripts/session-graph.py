#!/usr/bin/env python3
"""Build a temporal graph of sessions and files touched, visualize with pyvis.

Usage:
    session-graph.py DATE_EXPR [--min-msgs N] [--min-files N] [--day DAY] [--no-open]

DATE_EXPR: same as recall-day.py (yesterday, "last week", 2026-02-25, etc.)
--day: filter to specific day within range (e.g. "monday", "2026-02-20")

Outputs interactive HTML to /tmp/session-graph.html and opens in browser.
Features: Obsidian-style theme, neighbor highlighting on hover, click-to-select
nodes, copy selected file paths to clipboard.
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import networkx as nx
from pyvis.network import Network

# Import recall-day as module
import importlib.util
spec = importlib.util.spec_from_file_location("recall_day", Path(__file__).parent / "recall-day.py")
recall_day = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recall_day)

def _detect_vault_prefix():
    """Auto-detect vault prefix from CWD or VAULT_DIR env var."""
    if os.environ.get("VAULT_DIR"):
        p = os.environ["VAULT_DIR"]
        return p if p.endswith("/") else p + "/"
    # Walk up from CWD looking for .obsidian/ directory
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".obsidian").is_dir():
            return str(parent) + "/"
    # Fallback: use CWD
    return str(cwd) + "/"

VAULT_PREFIX = _detect_vault_prefix()
SKIP_PREFIXES = ["/tmp/", "/private/tmp/", "/dev/", "/var/", "/usr/"]
SKIP_PATTERNS = [
    re.compile(r'\.claude/projects/'),
    re.compile(r'node_modules/'),
    re.compile(r'\.git/'),
    re.compile(r'__pycache__/'),
    re.compile(r'\.DS_Store'),
]

FILE_PATH_RE = re.compile(
    r'(?:^|[\s"\'=])(' + re.escape(VAULT_PREFIX) + r'[^\s"\';<>|&\)]+)',
)

# Obsidian-inspired palette
DAY_COLORS = {
    0: "#B4A7FA",  # Mon - soft lavender
    1: "#7DDCB5",  # Tue - mint
    2: "#FDBA8C",  # Wed - peach
    3: "#FCA5A5",  # Thu - blush
    4: "#D8B4FE",  # Fri - lilac
    5: "#FDE68A",  # Sat - butter
    6: "#93C5FD",  # Sun - periwinkle
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_NAME_MAP = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
}

FOLDER_COLORS = {
    "Notes/Sessions/": "#FCA5A5",
    "Notes/Plans/": "#D8B4FE",
    "Notes/Goals/": "#FDBA8C",
    "Notes/Dashboards/": "#B4A7FA",
    "Notes/Content/": "#7DDCB5",
    "Notes/Research/": "#93C5FD",
    "Notes/Voice/": "#D9F99D",
    "Notes/Docs/": "#CBD5E1",
    "Notes/Projects/": "#A7F3D0",
    ".claude/skills/": "#A5F3FC",
    "Templates/": "#FDE68A",
    "Daily/": "#BBF7D0",
    "External/": "#E7E5E4",
}

# Folders that get clickable filter buttons in the legend
FILTERABLE_FOLDERS = [
    "Notes/Goals/",
    "Notes/Research/",
    "Notes/Voice/",
    "Notes/Docs/",
    "Notes/Sessions/",
    "Notes/Content/",
    ".claude/skills/",
]

# Files that are touched by almost every session - skip them
NOISE_FILES = {
    "CLAUDE.md",
    ".claude/settings.json",
    ".claude/settings.local.json",
}


def extract_file_paths(jsonl_path: Path) -> dict | None:
    """Extract all file paths from tool calls in a JSONL session file."""
    files = set()
    ops = defaultdict(set)
    session_id = jsonl_path.stem
    start_time = None
    first_user_msg = None
    user_msg_count = 0

    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if obj.get('sessionId'):
                    session_id = obj['sessionId']

                ts_str = obj.get('timestamp')
                if ts_str and not start_time:
                    try:
                        start_time = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        pass

                if obj.get('type') == 'user':
                    user_msg_count += 1
                    if first_user_msg is None:
                        raw = recall_day.extract_text(obj.get('message', {}).get('content', ''))
                        cleaned = recall_day.clean_content(raw)
                        if cleaned and len(cleaned) >= 5:
                            first_user_msg = cleaned

                if obj.get('type') != 'assistant':
                    continue

                content = obj.get('message', {}).get('content', [])
                if not isinstance(content, list):
                    continue

                for block in content:
                    if not isinstance(block, dict) or block.get('type') != 'tool_use':
                        continue

                    tool = block.get('name', '')
                    inp = block.get('input', {})

                    if tool in ('Read', 'Edit', 'Write', 'NotebookEdit'):
                        fp = inp.get('file_path') or inp.get('notebook_path', '')
                        if fp:
                            norm = normalize_path(fp)
                            if norm:
                                files.add(norm)
                                ops[norm].add(tool.lower())

                    elif tool in ('Glob', 'Grep'):
                        fp = inp.get('path', '')
                        if fp:
                            norm = normalize_path(fp)
                            if norm:
                                files.add(norm)
                                ops[norm].add('search')

                    elif tool == 'Bash':
                        cmd = inp.get('command', '')
                        for m in FILE_PATH_RE.finditer(cmd):
                            fp = m.group(1).rstrip('.,;:')
                            norm = normalize_path(fp)
                            if norm:
                                files.add(norm)
                                ops[norm].add('bash')

    except (OSError, UnicodeDecodeError):
        return None

    if not start_time:
        return None

    # Strip noise files
    files -= NOISE_FILES

    title = "Untitled"
    if first_user_msg:
        first_line = first_user_msg.split('\n')[0].strip()
        first_line = re.sub(r'^#+\s*', '', first_line)
        # Clean up "Continue:" prefix
        m = re.match(r'Continue:\s*(.+)', first_line)
        if m:
            first_line = m.group(1).strip()
        if len(first_line) > 50:
            first_line = first_line[:47] + '...'
        if len(first_line) >= 3:
            title = first_line

    return {
        'files': files,
        'ops': dict(ops),
        'session_id': session_id,
        'start_time': start_time,
        'title': title,
        'msg_count': user_msg_count,
        'filepath': str(jsonl_path),
    }


def normalize_path(fp: str) -> str | None:
    """Normalize a file path to vault-relative, skip irrelevant paths."""
    if not fp or not fp.startswith('/'):
        return None

    for prefix in SKIP_PREFIXES:
        if fp.startswith(prefix):
            return None

    for pat in SKIP_PATTERNS:
        if pat.search(fp):
            return None

    if not fp.startswith(VAULT_PREFIX):
        return None

    rel = fp[len(VAULT_PREFIX):]
    if not rel:
        return None

    # Skip binary/media/config noise
    if rel.endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mp3', '.wav',
                     '.zip', '.tar', '.gz', '.pdf', '.excalidraw', '.json',
                     '.har', '.css', '.ico')):
        return None

    # Skip if it's just a directory path (no extension, no filename)
    if '.' not in rel.split('/')[-1]:
        return None

    return rel


def get_folder_color(path: str) -> str:
    for folder, color in FOLDER_COLORS.items():
        if path.startswith(folder):
            return color
    return "#78909C"


def get_folder_group(path: str) -> str:
    parts = path.split('/')
    if len(parts) >= 2:
        return '/'.join(parts[:2])
    return parts[0]


def recency_color(t: float) -> str:
    """Map recency 0.0 (oldest) to 1.0 (newest) to a lavender gradient hex.

    Base hue: lavender (252 deg). Saturation and lightness vary with recency.
    Oldest: dark, desaturated (HSL 252, 25%, 30%)
    Newest: saturated, bright (HSL 252, 85%, 78%)
    Returns hex color (pyvis drops non-hex color strings).
    """
    import colorsys
    h = 252 / 360.0
    s_pct = 25 + t * 60   # 25% -> 85%
    l_pct = 30 + t * 48   # 30% -> 78%
    s = s_pct / 100.0
    l = l_pct / 100.0
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def build_graph(sessions: list, min_files: int = 3) -> nx.Graph:
    """Build graph with noise reduction."""
    G = nx.Graph()

    # Count how many sessions reference each file - skip ultra-common ones
    file_freq = Counter()
    for s in sessions:
        for fp in s['files']:
            file_freq[fp] += 1

    # Files referenced by >60% of sessions are noise (like CLAUDE.md)
    noise_threshold = max(3, len(sessions) * 0.6)
    noisy_files = {fp for fp, count in file_freq.items() if count > noise_threshold}

    # Compute time range for recency gradient
    timestamps = [s['start_time'].timestamp() for s in sessions]
    t_min, t_max = min(timestamps), max(timestamps)
    t_span = t_max - t_min if t_max > t_min else 1.0

    for s in sessions:
        clean_files = s['files'] - noisy_files
        if len(clean_files) < min_files:
            continue

        sid = s['session_id'][:8]
        day = s['start_time'].weekday()
        day_name = DAY_NAMES[day]
        date_str = s['start_time'].strftime('%Y-%m-%d %H:%M')

        recency = (s['start_time'].timestamp() - t_min) / t_span
        session_color = recency_color(recency)

        short_title = s['title'][:30] + ('...' if len(s['title']) > 30 else '')
        G.add_node(
            f"s:{sid}",
            label=short_title,
            title=f"{s['title']}\n{date_str}\n{s['msg_count']} msgs, {len(clean_files)} files",
            color=session_color,
            size=max(8, min(22, 4 + s['msg_count'] // 4)),
            shape="dot",
            session_day=f"session-{day_name}",
            node_type="session",
            day=day_name,
            date=date_str,
            file_count=len(clean_files),
            short_label=s['title'],
            recency=round(recency, 3),
            font={'size': 13, 'color': '#dcddde', 'strokeWidth': 2, 'strokeColor': '#262626'},
        )

        for fp in clean_files:
            fid = f"f:{fp}"
            if fid not in G:
                short = fp.split('/')[-1].replace('.md', '')
                if len(short) > 25:
                    short = short[:22] + '...'
                folder_group = get_folder_group(fp)

                # Size by how many sessions reference this file
                ref_count = file_freq[fp]
                fsize = max(3, min(12, 2 + ref_count))

                G.add_node(
                    fid,
                    label=" ",
                    title=f"{short}\n{fp}",
                    color=get_folder_color(fp),
                    size=fsize,
                    shape="square",
                    group=folder_group,
                    node_type="file",
                    full_path=fp,
                    short_label=short,
                )

            op_types = s['ops'].get(fp, {'touch'})
            if 'write' in op_types or 'edit' in op_types:
                edge_width = 1.2
                edge_opacity = 0.5
            else:
                edge_width = 0.6
                edge_opacity = 0.35
            G.add_edge(
                f"s:{sid}", fid,
                title=', '.join(sorted(op_types)),
                color={'color': session_color, 'opacity': edge_opacity},
                width=edge_width,
            )

    return G


def render_graph(G: nx.Graph, output_path: str, date_label: str, sessions_meta: dict):
    """Render with Obsidian-style theme and interactive features."""
    net = Network(
        height="100vh",
        width="100%",
        bgcolor="#262626",
        font_color="#dcddde",
        directed=False,
        notebook=False,
        cdn_resources="remote",
    )

    net.from_nx(G)

    net.set_options("""
    {
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -5000,
                "centralGravity": 0.15,
                "springLength": 200,
                "springConstant": 0.015,
                "damping": 0.3,
                "avoidOverlap": 0.4
            },
            "solver": "barnesHut",
            "stabilization": {
                "iterations": 150,
                "fit": true
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 50,
            "multiselect": true,
            "navigationButtons": false,
            "keyboard": {
                "enabled": true
            }
        },
        "nodes": {
            "font": {
                "size": 10,
                "face": "Inter, -apple-system, sans-serif",
                "color": "#dcddde",
                "strokeWidth": 2,
                "strokeColor": "#262626"
            },
            "borderWidth": 0,
            "borderWidthSelected": 2,
            "chosen": true
        },
        "edges": {
            "smooth": {
                "type": "continuous"
            },
            "color": {
                "inherit": false,
                "opacity": 0.4
            },
            "width": 0.6,
            "selectionWidth": 2
        }
    }
    """)

    net.html = None
    net.save_graph(output_path)

    with open(output_path, 'r') as f:
        html = f.read()

    custom_code = build_custom_js(date_label, sessions_meta)
    custom_css = build_custom_css()

    html = html.replace('</head>', custom_css + '</head>')
    html = html.replace('</body>', custom_code + '</body>')

    with open(output_path, 'w') as f:
        f.write(html)


def build_custom_css() -> str:
    return """
    <style>
        body { margin: 0; overflow: hidden; font-family: Inter, -apple-system, sans-serif; }
        #mynetwork { border: none !important; }
        .vis-tooltip {
            background: #1e1e1e !important;
            color: #dcddde !important;
            border: 1px solid #444 !important;
            border-radius: 6px !important;
            padding: 8px 12px !important;
            font-family: 'SF Mono', 'Fira Code', monospace !important;
            font-size: 11px !important;
            white-space: pre-line !important;
            max-width: 400px !important;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
        }
        .legend-item { display:flex;align-items:center;gap:6px;margin:2px 0;cursor:pointer;transition:opacity 0.1s; }
        .legend-item:hover { opacity:0.8; }
        .legend-item.dimmed { opacity:0.3; }
        .dot { display:inline-block;width:10px;height:10px;border-radius:50%;flex-shrink:0; }
        .sq { display:inline-block;width:8px;height:8px;border-radius:1px;flex-shrink:0; }
        #physics-panel {
            position:fixed;top:12px;right:12px;background:#1e1e1e;color:#dcddde;
            border-radius:10px;font-size:11px;z-index:1000;
            border:1px solid #333;box-shadow:0 4px 24px rgba(0,0,0,0.6);
            user-select:none;overflow:hidden;
        }
        #physics-toggle {
            padding:10px 14px;cursor:pointer;display:flex;align-items:center;gap:6px;
            font-size:11px;color:#aaa;
        }
        #physics-toggle:hover { color:#fff; }
        #physics-body {
            display:none;padding:4px 14px 14px;border-top:1px solid #333;
        }
        #physics-body.open { display:block; }
        .phys-row {
            display:flex;align-items:center;justify-content:space-between;margin:6px 0;gap:8px;
        }
        .phys-row label { color:#888;font-size:10px;min-width:70px; }
        .phys-row input[type=range] {
            flex:1;height:3px;-webkit-appearance:none;background:#444;border-radius:2px;outline:none;
        }
        .phys-row input[type=range]::-webkit-slider-thumb {
            -webkit-appearance:none;width:12px;height:12px;border-radius:50%;
            background:#A78BFA;cursor:pointer;
        }
        .phys-row .val { color:#666;font-size:9px;min-width:40px;text-align:right;font-family:'SF Mono',monospace; }
        .phys-btn {
            background:#333;color:#aaa;border:none;border-radius:4px;
            padding:5px 10px;cursor:pointer;font-size:10px;font-family:inherit;
            transition:background 0.15s;
        }
        .phys-btn:hover { background:#444;color:#fff; }
        .phys-btn.active { background:#A78BFA;color:#fff; }
    </style>
    """


def build_custom_js(date_label: str, sessions_meta: dict) -> str:
    """Build legend, neighbor highlighting, folder/day filters, physics controls, clipboard JS."""

    # Build recency gradient legend
    recency_gradient = (
        '<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
        '<span style="color:#666;font-size:9px">older</span>'
        '<div style="flex:1;height:8px;border-radius:4px;'
        'background:linear-gradient(to right, #41395f, #aa97f6)"></div>'
        '<span style="color:#666;font-size:9px">recent</span>'
        '</div>'
    )

    # Folder filter items (clickable)
    folder_filter_items = ''.join(
        f'<div class="legend-item" data-folder="{folder}">'
        f'<span class="sq" style="background:{FOLDER_COLORS[folder]}"></span>'
        f'<span>{folder.rstrip("/").split("/")[-1]}</span></div>'
        for folder in FILTERABLE_FOLDERS
    )

    # Physics defaults for reset
    physics_defaults = {
        'gravitationalConstant': -5000,
        'centralGravity': 0.15,
        'springLength': 200,
        'springConstant': 0.015,
        'damping': 0.3,
    }

    return """
    <!-- Legend panel -->
    <div id="legend" style="position:fixed;top:12px;left:12px;background:#1e1e1e;color:#dcddde;
                padding:14px 18px;border-radius:10px;font-size:11px;z-index:1000;
                border:1px solid #333;box-shadow:0 4px 24px rgba(0,0,0,0.6);
                max-width:180px;line-height:1.5;user-select:none">
        <div style="font-size:13px;font-weight:600;margin-bottom:6px;color:#fff">Session Graph</div>
        <div style="color:#888;margin-bottom:10px;font-size:10px">""" + date_label + """</div>
        <div style="font-weight:600;margin-bottom:4px;color:#aaa;font-size:9px;text-transform:uppercase;letter-spacing:0.5px">Sessions</div>
        """ + recency_gradient + """
        <div style="font-weight:600;margin:10px 0 4px;color:#aaa;font-size:9px;text-transform:uppercase;letter-spacing:0.5px">Files</div>
        """ + folder_filter_items + """
        <div style="border-top:1px solid #333;margin-top:10px;padding-top:8px;color:#666;font-size:9px;line-height:1.6">
            Hover: highlight neighbors<br>
            Click: select node<br>
            Shift+click: multi-select<br>
            Esc: clear selection
        </div>
    </div>

    <!-- Physics controls panel -->
    <div id="physics-panel">
        <div id="physics-toggle" onclick="document.getElementById('physics-body').classList.toggle('open')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            Physics
        </div>
        <div id="physics-body">
            <div class="phys-row">
                <label>Gravity</label>
                <input type="range" id="ph-grav" min="-10000" max="0" step="100" value="-5000">
                <span class="val" id="ph-grav-v">-5000</span>
            </div>
            <div class="phys-row">
                <label>Central</label>
                <input type="range" id="ph-central" min="0" max="3" step="0.05" value="0.15">
                <span class="val" id="ph-central-v">0.15</span>
            </div>
            <div class="phys-row">
                <label>Spring Len</label>
                <input type="range" id="ph-slen" min="10" max="500" step="5" value="200">
                <span class="val" id="ph-slen-v">200</span>
            </div>
            <div class="phys-row">
                <label>Spring K</label>
                <input type="range" id="ph-sk" min="0.001" max="0.5" step="0.005" value="0.015">
                <span class="val" id="ph-sk-v">0.015</span>
            </div>
            <div class="phys-row">
                <label>Damping</label>
                <input type="range" id="ph-damp" min="0.01" max="1" step="0.01" value="0.3">
                <span class="val" id="ph-damp-v">0.30</span>
            </div>
            <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
                <button class="phys-btn" id="ph-toggle" onclick="togglePhysics()">Enable</button>
                <button class="phys-btn" onclick="restabilize()">Re-stabilize</button>
                <button class="phys-btn" onclick="resetPhysics()">Reset</button>
            </div>
        </div>
    </div>

    <!-- Selection panel -->
    <div id="selection-panel" style="position:fixed;bottom:12px;left:50%;transform:translateX(-50%);
                background:#1e1e1e;color:#dcddde;padding:10px 16px;border-radius:10px;
                font-size:11px;z-index:1000;border:1px solid #333;
                box-shadow:0 4px 24px rgba(0,0,0,0.6);display:none;
                max-width:80vw;
                font-family:'SF Mono','Fira Code',monospace">
        <div style="display:flex;align-items:center;gap:8px;white-space:nowrap">
            <span id="sel-count">0</span> selected
            <button id="btn-copy" onclick="copySelected()" style="
                background:#B4A7FA;color:white;border:none;border-radius:4px;
                padding:4px 12px;cursor:pointer;font-size:11px;
                font-family:inherit">Copy paths</button>
            <button id="btn-clear" onclick="clearSelection()" style="
                background:#333;color:#aaa;border:none;border-radius:4px;
                padding:4px 12px;cursor:pointer;font-size:11px;
                font-family:inherit">Clear</button>
            <span id="copy-toast" style="margin-left:4px;color:#7DDCB5;display:none">Copied!</span>
        </div>
        <div id="sel-paths" style="display:none;margin-top:8px;max-height:150px;overflow-y:auto;
                    border-top:1px solid #333;padding-top:8px;
                    font-size:10px;color:#aaa;white-space:pre;user-select:text;cursor:text"></div>
    </div>

    <script>
    var checkNetwork = setInterval(function() {
        if (typeof network !== 'undefined' && network !== null) {
            clearInterval(checkNetwork);
            initGraph();
        }
    }, 100);

    function initGraph() {
        var selectedNodes = new Set();
        var allNodes = network.body.data.nodes;
        var allEdges = network.body.data.edges;
        var highlightActive = false;
        var physicsOn = true;

        var shiftDown = false;
        document.addEventListener('keydown', function(e) { if (e.key === 'Shift') shiftDown = true; });
        document.addEventListener('keyup', function(e) { if (e.key === 'Shift') shiftDown = false; });

        // Pre-compute neighbor maps for O(1) lookups instead of calling network.getConnectedNodes every hover
        var neighborMap = {};  // nodeId -> Set of neighbor nodeIds
        var edgeMap = {};      // nodeId -> Set of edgeIds
        var nodeGroup = {};    // nodeId -> group string
        var nodeFolder = {};   // nodeId -> folder prefix (for file nodes)
        var shortLabels = {};
        var originalColors = {};
        var originalEdgeColors = {};
        var originalEdgeWidths = {};

        // Build lookup tables in one pass
        allNodes.forEach(function(node) {
            var c = node.color;
            originalColors[node.id] = (typeof c === 'object' && c !== null) ? JSON.parse(JSON.stringify(c)) : c;
            neighborMap[node.id] = new Set();
            edgeMap[node.id] = new Set();
            nodeGroup[node.id] = node.session_day || node.group || '';
            // short_label set by Python, fallback to first line of title
            if (node.short_label) {
                shortLabels[node.id] = node.short_label;
            } else if (node.title) {
                shortLabels[node.id] = node.title.split('\\n')[0];
            }
            if (node.full_path) {
                // Extract folder prefix for filtering
                var fp = node.full_path;
                var parts = fp.split('/');
                if (parts.length >= 2) nodeFolder[node.id] = parts.slice(0, 2).join('/') + '/';
                else nodeFolder[node.id] = parts[0] + '/';
            }
        });

        allEdges.forEach(function(edge) {
            var c = edge.color;
            originalEdgeColors[edge.id] = (typeof c === 'object' && c !== null) ? JSON.parse(JSON.stringify(c)) : c;
            originalEdgeWidths[edge.id] = edge.width || 0.6;
            // Build adjacency
            if (neighborMap[edge.from]) neighborMap[edge.from].add(edge.to);
            if (neighborMap[edge.to]) neighborMap[edge.to].add(edge.from);
            if (edgeMap[edge.from]) edgeMap[edge.from].add(edge.id);
            if (edgeMap[edge.to]) edgeMap[edge.to].add(edge.id);
        });

        // Stop physics after stabilization
        network.once('stabilizationIterationsDone', function() {
            network.setOptions({ physics: false });
            physicsOn = false;
            document.getElementById('ph-toggle').textContent = 'Enable';
            document.getElementById('ph-toggle').classList.remove('active');
        });

        // --- HOVER HIGHLIGHT (delayed focus, smooth defocus) ---
        var hoverTimer = null;
        var blurTimer = null;
        var fadeAnim = null;
        var HOVER_DELAY = 300;   // ms before focus kicks in
        var FADE_STEPS = 8;      // animation frames for defocus
        var FADE_INTERVAL = 30;  // ms between frames (~33fps)

        network.on("hoverNode", function(params) {
            if (blurTimer) { clearTimeout(blurTimer); blurTimer = null; }
            if (fadeAnim) { clearInterval(fadeAnim); fadeAnim = null; }
            if (hoverTimer) clearTimeout(hoverTimer);
            hoverTimer = setTimeout(function() {
                hoverTimer = null;
                highlightNeighbors(params.node);
            }, HOVER_DELAY);
        });

        network.on("blurNode", function() {
            if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
            if (selectedNodes.size === 0 && !activeFilter) {
                if (blurTimer) clearTimeout(blurTimer);
                blurTimer = setTimeout(function() {
                    blurTimer = null;
                    smoothResetHighlight();
                }, 120);
            }
        });

        var activeFilter = null; // tracks current filter state

        function highlightNeighbors(nodeId) {
            highlightActive = true;
            if (fadeAnim) { clearInterval(fadeAnim); fadeAnim = null; }
            var neighbors = neighborMap[nodeId] || new Set();
            var edges = edgeMap[nodeId] || new Set();

            var nodeUpdates = [];
            allNodes.forEach(function(node) {
                var isNeighbor = neighbors.has(node.id) || node.id === nodeId;
                nodeUpdates.push({
                    id: node.id,
                    color: isNeighbor ? originalColors[node.id] : '#333333',
                    label: isNeighbor ? (shortLabels[node.id] || node.label) : (shortLabels[node.id] ? ' ' : node.label),
                    opacity: isNeighbor ? 1.0 : 0.15,
                });
            });
            allNodes.update(nodeUpdates);

            var edgeUpdates = [];
            allEdges.forEach(function(edge) {
                edgeUpdates.push(edges.has(edge.id) ? {
                    id: edge.id,
                    color: Object.assign({}, originalEdgeColors[edge.id], { opacity: 0.7 }),
                    width: 2,
                } : {
                    id: edge.id,
                    color: { color: '#333', opacity: 0.03 },
                    width: 0.3,
                });
            });
            allEdges.update(edgeUpdates);
        }

        function smoothResetHighlight() {
            if (!highlightActive) return;
            var step = 0;
            fadeAnim = setInterval(function() {
                step++;
                var t = step / FADE_STEPS; // 0 -> 1
                if (t >= 1) {
                    clearInterval(fadeAnim);
                    fadeAnim = null;
                    resetHighlight();
                    return;
                }
                // Lerp opacity: dimmed (0.15) -> full (1.0)
                var nodeOpacity = 0.15 + t * 0.85;
                var edgeOpacity = 0.03 + t * 0.17; // -> ~0.2
                var nodeUpdates = [];
                allNodes.forEach(function(node) {
                    nodeUpdates.push({ id: node.id, opacity: nodeOpacity });
                });
                allNodes.update(nodeUpdates);
                var edgeUpdates = [];
                allEdges.forEach(function(edge) {
                    edgeUpdates.push({
                        id: edge.id,
                        color: { color: originalEdgeColors[edge.id].color || '#555', opacity: edgeOpacity },
                    });
                });
                allEdges.update(edgeUpdates);
            }, FADE_INTERVAL);
        }

        function resetHighlight() {
            if (!highlightActive) return;
            highlightActive = false;
            if (fadeAnim) { clearInterval(fadeAnim); fadeAnim = null; }

            var nodeUpdates = [];
            allNodes.forEach(function(node) {
                nodeUpdates.push({
                    id: node.id,
                    color: originalColors[node.id],
                    label: shortLabels[node.id] || node.label,
                    opacity: 1.0,
                });
            });
            allNodes.update(nodeUpdates);

            var edgeUpdates = [];
            allEdges.forEach(function(edge) {
                edgeUpdates.push({
                    id: edge.id,
                    color: originalEdgeColors[edge.id],
                    width: originalEdgeWidths[edge.id],
                });
            });
            allEdges.update(edgeUpdates);
        }

        // --- FILTER ENGINE (shared by day + folder filters) ---
        function applyFilter(visibleNodes) {
            var visible = visibleNodes;
            var nodeUpdates = [];
            allNodes.forEach(function(node) {
                nodeUpdates.push(visible.has(node.id) ? {
                    id: node.id,
                    color: originalColors[node.id],
                    opacity: 1.0,
                } : {
                    id: node.id,
                    color: '#2a2a2a',
                    opacity: 0.08,
                });
            });
            allNodes.update(nodeUpdates);

            var edgeUpdates = [];
            allEdges.forEach(function(edge) {
                var both = visible.has(edge.from) && visible.has(edge.to);
                edgeUpdates.push(both ? {
                    id: edge.id,
                    color: Object.assign({}, originalEdgeColors[edge.id], { opacity: 0.5 }),
                    width: 1.2,
                } : {
                    id: edge.id,
                    color: { color: '#333', opacity: 0.02 },
                    width: 0.2,
                });
            });
            allEdges.update(edgeUpdates);
        }

        function clearFilter() {
            activeFilter = null;
            resetHighlight();
            document.querySelectorAll('.legend-item[data-day],.legend-item[data-folder]').forEach(function(e) {
                e.classList.remove('dimmed');
            });
        }

        // --- DAY FILTER ---
        document.querySelectorAll('.legend-item[data-day]').forEach(function(el) {
            el.addEventListener('click', function() {
                var day = this.getAttribute('data-day');
                if (activeFilter === 'day:' + day) {
                    clearFilter();
                    return;
                }
                activeFilter = 'day:' + day;
                // Dim other legend items
                document.querySelectorAll('.legend-item[data-day]').forEach(function(e) {
                    e.classList.toggle('dimmed', e.getAttribute('data-day') !== day);
                });
                document.querySelectorAll('.legend-item[data-folder]').forEach(function(e) {
                    e.classList.remove('dimmed');
                });

                var visible = new Set();
                var nodeIds = allNodes.getIds();
                nodeIds.forEach(function(id) {
                    if (nodeGroup[id] === 'session-' + day) {
                        visible.add(id);
                        (neighborMap[id] || new Set()).forEach(function(nid) { visible.add(nid); });
                    }
                });
                applyFilter(visible);
            });
        });

        // --- FOLDER FILTER ---
        document.querySelectorAll('.legend-item[data-folder]').forEach(function(el) {
            el.addEventListener('click', function() {
                var folder = this.getAttribute('data-folder');
                if (activeFilter === 'folder:' + folder) {
                    clearFilter();
                    return;
                }
                activeFilter = 'folder:' + folder;
                document.querySelectorAll('.legend-item[data-folder]').forEach(function(e) {
                    e.classList.toggle('dimmed', e.getAttribute('data-folder') !== folder);
                });
                document.querySelectorAll('.legend-item[data-day]').forEach(function(e) {
                    e.classList.remove('dimmed');
                });

                // Find all file nodes in this folder + their connected sessions
                var visible = new Set();
                var nodeIds = allNodes.getIds();
                nodeIds.forEach(function(id) {
                    if (nodeFolder[id] === folder) {
                        visible.add(id);
                        (neighborMap[id] || new Set()).forEach(function(nid) { visible.add(nid); });
                    }
                });
                applyFilter(visible);
            });
        });

        // --- CLICK SELECTION ---
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                if (shiftDown) {
                    if (selectedNodes.has(nodeId)) selectedNodes.delete(nodeId);
                    else selectedNodes.add(nodeId);
                } else {
                    selectedNodes.clear();
                    selectedNodes.add(nodeId);
                }
                updateSelectionPanel();
            } else if (!shiftDown) {
                selectedNodes.clear();
                updateSelectionPanel();
                if (activeFilter) clearFilter();
                else resetHighlight();
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                selectedNodes.clear();
                updateSelectionPanel();
                clearFilter();
            }
            // Ctrl+C / Cmd+C to copy selected paths
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' && selectedNodes.size > 0) {
                e.preventDefault();
                copySelected();
            }
        });

        function getSelectedPaths() {
            var paths = [];
            selectedNodes.forEach(function(nodeId) {
                if (nodeId.startsWith('f:')) {
                    paths.push(nodeId.substring(2));
                } else if (nodeId.startsWith('s:')) {
                    (neighborMap[nodeId] || new Set()).forEach(function(cid) {
                        if (cid.startsWith('f:')) paths.push(cid.substring(2));
                    });
                }
            });
            return [...new Set(paths)];
        }

        function updateSelectionPanel() {
            var panel = document.getElementById('selection-panel');
            var count = document.getElementById('sel-count');
            var pathsDiv = document.getElementById('sel-paths');
            if (selectedNodes.size > 0) {
                panel.style.display = 'block';
                count.textContent = selectedNodes.size;
                var paths = getSelectedPaths();
                if (paths.length > 0) {
                    pathsDiv.style.display = 'block';
                    pathsDiv.textContent = paths.join('\\n');
                } else {
                    pathsDiv.style.display = 'none';
                }
            } else {
                panel.style.display = 'none';
                pathsDiv.style.display = 'none';
            }
        }

        // --- CLIPBOARD (always use textarea for file:// protocol) ---
        function copyToClipboard(text) {
            // file:// protocol: navigator.clipboard rejects silently, always use textarea
            if (window.location.protocol !== 'file:' && navigator.clipboard && window.isSecureContext) {
                return navigator.clipboard.writeText(text).catch(function() {
                    return textareaCopy(text);
                });
            }
            return textareaCopy(text);
        }

        function textareaCopy(text) {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            var ok = false;
            try { ok = document.execCommand('copy'); } catch(e) {}
            document.body.removeChild(ta);
            return ok ? Promise.resolve() : Promise.reject('copy failed');
        }

        window.copySelected = function() {
            var paths = getSelectedPaths();
            if (paths.length === 0) {
                console.log('[graph] copySelected: no paths from', selectedNodes.size, 'selected nodes');
                return;
            }

            var text = paths.join('\\n');
            console.log('[graph] copying', paths.length, 'paths');
            copyToClipboard(text).then(function() {
                var toast = document.getElementById('copy-toast');
                toast.style.display = 'inline';
                toast.textContent = paths.length + ' paths copied!';
                setTimeout(function() { toast.style.display = 'none'; }, 2000);
            }).catch(function(err) {
                console.error('[graph] clipboard failed:', err);
                // Paths are already visible in panel - tell user to select manually
                var toast = document.getElementById('copy-toast');
                toast.style.display = 'inline';
                toast.textContent = 'Auto-copy failed - select paths below and Cmd+C';
                toast.style.color = '#FCA5A5';
                setTimeout(function() { toast.style.display = 'none'; toast.style.color = '#7DDCB5'; }, 4000);
                // Select the paths text for easy manual copy
                var pathsDiv = document.getElementById('sel-paths');
                if (pathsDiv && window.getSelection) {
                    var range = document.createRange();
                    range.selectNodeContents(pathsDiv);
                    var sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(range);
                }
            });
        };

        window.clearSelection = function() {
            selectedNodes.clear();
            updateSelectionPanel();
            if (!activeFilter) resetHighlight();
        };

        // --- PHYSICS CONTROLS ---
        var DEFAULTS = """ + json.dumps(physics_defaults) + """;

        function setPhysicsParam(key, value) {
            var opts = { physics: { barnesHut: {} } };
            opts.physics.barnesHut[key] = value;
            opts.physics.enabled = true;
            network.setOptions(opts);
        }

        var sliders = [
            { id: 'ph-grav', key: 'gravitationalConstant', fmt: function(v) { return v; } },
            { id: 'ph-central', key: 'centralGravity', fmt: function(v) { return parseFloat(v).toFixed(2); } },
            { id: 'ph-slen', key: 'springLength', fmt: function(v) { return v; } },
            { id: 'ph-sk', key: 'springConstant', fmt: function(v) { return parseFloat(v).toFixed(3); } },
            { id: 'ph-damp', key: 'damping', fmt: function(v) { return parseFloat(v).toFixed(2); } },
        ];

        sliders.forEach(function(s) {
            var el = document.getElementById(s.id);
            var valEl = document.getElementById(s.id + '-v');
            el.addEventListener('input', function() {
                var v = parseFloat(this.value);
                valEl.textContent = s.fmt(v);
                if (!physicsOn) {
                    physicsOn = true;
                    document.getElementById('ph-toggle').textContent = 'Disable';
                    document.getElementById('ph-toggle').classList.add('active');
                }
                setPhysicsParam(s.key, v);
            });
        });

        window.togglePhysics = function() {
            physicsOn = !physicsOn;
            network.setOptions({ physics: { enabled: physicsOn } });
            var btn = document.getElementById('ph-toggle');
            btn.textContent = physicsOn ? 'Disable' : 'Enable';
            btn.classList.toggle('active', physicsOn);
        };

        window.restabilize = function() {
            // Read current slider values
            var opts = { physics: { enabled: true, barnesHut: {}, stabilization: { iterations: 150, fit: true } } };
            sliders.forEach(function(s) {
                opts.physics.barnesHut[s.key] = parseFloat(document.getElementById(s.id).value);
            });
            network.setOptions(opts);
            physicsOn = true;
            document.getElementById('ph-toggle').textContent = 'Disable';
            document.getElementById('ph-toggle').classList.add('active');
            network.stabilize(150);
            // Stop after done
            network.once('stabilizationIterationsDone', function() {
                network.setOptions({ physics: false });
                physicsOn = false;
                document.getElementById('ph-toggle').textContent = 'Enable';
                document.getElementById('ph-toggle').classList.remove('active');
            });
        };

        window.resetPhysics = function() {
            sliders.forEach(function(s) {
                var el = document.getElementById(s.id);
                el.value = DEFAULTS[s.key];
                document.getElementById(s.id + '-v').textContent = s.fmt(DEFAULTS[s.key]);
            });
            restabilize();
        };
    }
    </script>
    """


def filter_sessions_by_day(sessions: list, day_filter: str) -> list:
    """Filter sessions to a specific day within the range."""
    day_filter = day_filter.strip().lower()

    # Check if it's a day name
    if day_filter in DAY_NAME_MAP:
        target_dow = DAY_NAME_MAP[day_filter]
        return [s for s in sessions if s['start_time'].weekday() == target_dow]

    # Check if it's a date
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', day_filter)
    if m:
        target = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
        return [s for s in sessions
                if s['start_time'].date() == target.date()]

    print(f"Warning: Can't parse day filter '{day_filter}', showing all", file=sys.stderr)
    return sessions


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Temporal session graph')
    parser.add_argument('date_expr', nargs='+', help='Date expression')
    parser.add_argument('--min-msgs', type=int, default=5, help='Min user messages per session (default: 5)')
    parser.add_argument('--min-files', type=int, default=3, help='Min files touched to include session (default: 3)')
    parser.add_argument('--day', type=str, default=None, help='Filter to specific day (e.g. monday, 2026-02-20)')
    parser.add_argument('--all-projects', action='store_true')
    parser.add_argument('--no-open', action='store_true', help='Do not open browser')
    parser.add_argument('-o', '--output', default=None)

    args = parser.parse_args()
    date_expr = ' '.join(args.date_expr)

    date_start, date_end = recall_day.parse_date_expr(date_expr)

    if date_end - date_start <= timedelta(days=1):
        date_label = date_start.strftime('%Y-%m-%d (%A)')
    else:
        date_label = f"{date_start.strftime('%Y-%m-%d')} to {(date_end - timedelta(days=1)).strftime('%Y-%m-%d')}"

    print(f"Scanning sessions for {date_label}...")

    project_dirs = recall_day.get_project_dirs(None, args.all_projects)

    sessions = []
    skipped = 0

    for proj_dir in project_dirs:
        for filepath in proj_dir.glob("*.jsonl"):
            try:
                mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
                if mtime < date_start - timedelta(days=1):
                    continue
            except OSError:
                continue

            meta = recall_day.scan_session_metadata(filepath, date_start, date_end)
            if meta is None:
                continue

            if meta['user_msg_count'] < args.min_msgs:
                skipped += 1
                continue

            print(f"  Scanning {filepath.stem[:8]}...", end='\r')
            result = extract_file_paths(filepath)
            if result and result['start_time'] >= date_start and result['start_time'] < date_end:
                sessions.append(result)

    sessions.sort(key=lambda s: s['start_time'])

    if args.day:
        sessions = filter_sessions_by_day(sessions, args.day)
        date_label += f" ({args.day})"

    total_files = sum(len(s['files']) for s in sessions)
    print(f"\nFound {len(sessions)} sessions touching {total_files} file refs ({skipped} filtered)")

    if not sessions:
        print("No sessions found. Try --min-msgs 1 or --min-files 1.")
        sys.exit(0)

    sessions_meta = {s['session_id'][:8]: {
        'title': s['title'],
        'time': s['start_time'].strftime('%H:%M'),
        'msgs': s['msg_count'],
    } for s in sessions}

    G = build_graph(sessions, min_files=args.min_files)
    print(f"Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    output_path = args.output
    if output_path is None:
        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / "session-graph.html")

    render_graph(G, output_path, date_label, sessions_meta)
    print(f"Saved to {output_path}")

    if not args.no_open:
        subprocess.run(['open', output_path], check=False)


if __name__ == '__main__':
    main()
