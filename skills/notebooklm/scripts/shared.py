"""Shared utilities for NotebookLM skill scripts.

Provides input validation, filename sanitization, and injection escaping
used across extract_passages.py, import_sources.py, and resolve_citations.py.
"""
import re
import sys


# --- Slug validation ---

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_SLUG_MAX = 80


def validate_slug(slug: str) -> None:
    """Validate that slug is kebab-case: [a-z0-9-], max 80 chars.

    Exits with an error message if invalid. Call immediately after argparse.

    >>> validate_slug("my-notebook")
    >>> validate_slug("a")
    >>> import subprocess, sys
    >>> r = subprocess.run([sys.executable, "-c",
    ...     "from shared import validate_slug; validate_slug('../../etc')"],
    ...     capture_output=True, text=True, cwd=__import__('pathlib').Path(__file__).parent)
    >>> r.returncode != 0
    True
    """
    if not slug or len(slug) > _SLUG_MAX or not _SLUG_RE.match(slug):
        print(
            f"ERROR: invalid slug {slug!r} — must be kebab-case "
            f"([a-z0-9-], max {_SLUG_MAX} chars, no leading/trailing dash)",
            file=sys.stderr,
        )
        sys.exit(1)


# --- Filename sanitization ---

_UNSAFE_CHARS_RE = re.compile(r'[/:*?"<>|\\]')
_DOTDOT_RE = re.compile(r"\.\.")
_WHITESPACE_RE = re.compile(r"\s+")
_LEADING_DOTS_DASHES_RE = re.compile(r"^[.\-]+")
_MAX_FILENAME = 120


def safe_filename(title: str) -> str:
    """Make title safe for filesystem use.

    - Strips unsafe characters (including backslash)
    - Collapses '..' to '_'
    - Strips leading dots and dashes
    - Collapses whitespace
    - Truncates to 120 chars
    - Falls back to 'untitled' if empty after sanitization

    >>> safe_filename('../../etc/passwd')
    '_-_-etc-passwd'
    >>> safe_filename('foo\\\\bar')
    'foo-bar'
    >>> safe_filename('...')
    '_.'
    >>> safe_filename('')
    'untitled'
    >>> safe_filename('  ')
    'untitled'
    >>> safe_filename('---')
    'untitled'
    >>> safe_filename('normal title')
    'normal title'
    >>> safe_filename('a' * 200)[:120] == 'a' * 120
    True
    """
    title = _UNSAFE_CHARS_RE.sub("-", title)
    title = _DOTDOT_RE.sub("_", title)
    title = _WHITESPACE_RE.sub(" ", title).strip()
    title = _LEADING_DOTS_DASHES_RE.sub("", title)
    if len(title) > _MAX_FILENAME:
        title = title[:_MAX_FILENAME].rstrip(" -")
    if not title:
        title = "untitled"
    return title


# --- YAML / Markdown injection escaping ---


def yaml_escape(val: str) -> str:
    """Escape a string for use in YAML double-quoted values.

    Handles backslashes, double quotes, and newlines.

    >>> yaml_escape('normal')
    'normal'
    >>> yaml_escape('has "quotes"')
    'has \\\\"quotes\\\\"'
    >>> yaml_escape('line1\\nline2')
    'line1\\\\nline2'
    >>> yaml_escape('back\\\\slash')
    'back\\\\\\\\slash'
    """
    val = val.replace("\\", "\\\\")
    val = val.replace('"', '\\"')
    val = val.replace("\n", "\\n")
    val = val.replace("\r", "\\r")
    return val


def markdown_heading_safe(title: str) -> str:
    """Strip characters that could break or inject into Markdown headings.

    Removes newlines and carriage returns to prevent heading injection.

    >>> markdown_heading_safe('Normal Title')
    'Normal Title'
    >>> markdown_heading_safe('Title\\n## Injected Heading')
    'Title ## Injected Heading'
    >>> markdown_heading_safe('Title\\r\\nInjected')
    'Title Injected'
    """
    return title.replace("\r", "").replace("\n", " ")


def wikilink_safe(text: str) -> str:
    """Strip characters that could break or inject into Obsidian [[wikilinks]].

    Removes ]], [[, and | to prevent wikilink injection.

    >>> wikilink_safe('Normal Topic')
    'Normal Topic'
    >>> wikilink_safe('Topic [[injected]]')
    'Topic injected'
    >>> wikilink_safe('Topic|alias')
    'Topicalias'
    """
    text = text.replace("]]", "")
    text = text.replace("[[", "")
    text = text.replace("|", "")
    return text


if __name__ == "__main__":
    import doctest

    results = doctest.testmod(verbose=True)
    sys.exit(0 if results.failed == 0 else 1)
