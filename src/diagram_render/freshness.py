"""Freshness checking for diagram source -> SVG output pairs."""

from __future__ import annotations

from pathlib import Path

from .models import DiagramFile, DiagramFormat, EXTENSION_FORMAT_MAP

# Filesystem timestamp granularity threshold (seconds).
# Some filesystems have coarse mtime granularity; 2s covers the worst common case.
FRESHNESS_THRESHOLD_SECONDS = 2.0


def resolve_output_path(source: Path) -> Path:
    """Compute the expected SVG output path for a diagram source file.

    Convention: same directory, same stem, .svg extension.
    Example: diagrams/seq-core-loop.puml -> diagrams/seq-core-loop.svg
    """
    return source.with_suffix(".svg")


def detect_format(source: Path) -> DiagramFormat | None:
    """Detect diagram format from file extension. Returns None if unsupported."""
    return EXTENSION_FORMAT_MAP.get(source.suffix.lower())


def has_yaml_frontmatter(content: str) -> bool:
    """Check if content starts with YAML frontmatter (--- delimited block)."""
    return content.startswith("---\n") or content.startswith("---\r\n")


def build_diagram_file(source: Path) -> DiagramFile | None:
    """Build a DiagramFile from a source path. Returns None if format unknown."""
    fmt = detect_format(source)
    if fmt is None:
        return None

    output = resolve_output_path(source)

    frontmatter = False
    if fmt == DiagramFormat.PLANTUML:
        try:
            content = source.read_text(encoding="utf-8")
            frontmatter = has_yaml_frontmatter(content)
        except (OSError, UnicodeDecodeError):
            pass

    return DiagramFile(
        source=source,
        format=fmt,
        output=output,
        has_frontmatter=frontmatter,
    )


def is_stale(diagram: DiagramFile) -> bool:
    """Check whether the SVG output is stale (source newer) or missing.

    Returns True if:
    - SVG file does not exist
    - Source file mtime > SVG file mtime + threshold
    """
    if not diagram.output.exists():
        return True

    try:
        source_mtime = diagram.source.stat().st_mtime
        output_mtime = diagram.output.stat().st_mtime
    except OSError:
        return True

    return source_mtime > (output_mtime + FRESHNESS_THRESHOLD_SECONDS)


def is_in_archive(source: Path) -> bool:
    """Check whether the source file is inside a zArchive directory."""
    return any(part.lower() == "zarchive" for part in source.parts)


def collect_diagram_sources(
    repo_root: Path,
    include_archive: bool = False,
) -> list[DiagramFile]:
    """Scan a repo for all diagram source files.

    Excludes: .git, .venv, node_modules, __pycache__, and zArchive (by default).
    """
    exclude_dirs = {".git", ".venv", "node_modules", "__pycache__"}
    diagrams: list[DiagramFile] = []

    for ext in EXTENSION_FORMAT_MAP:
        for source in repo_root.rglob(f"*{ext}"):
            # Skip excluded directories
            if any(part in exclude_dirs for part in source.parts):
                continue
            if not include_archive and is_in_archive(source):
                continue

            diagram = build_diagram_file(source)
            if diagram is not None:
                diagrams.append(diagram)

    return sorted(diagrams, key=lambda d: str(d.source))
