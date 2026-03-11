"""Diagram rendering: PlantUML and Mermaid CLI subprocess wrappers."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

from .models import (
    DiagramFile,
    DiagramFormat,
    RenderResult,
    RenderStatus,
    Severity,
)

# Per-diagram render timeout (seconds)
RENDER_TIMEOUT = 30


def _tool_available(name: str) -> bool:
    """Check if a tool is available on PATH."""
    return shutil.which(name) is not None


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (--- delimited block) from diagram source.

    Many .puml files in this project have YAML frontmatter that PlantUML
    cannot parse. The frontmatter is between the first '---' and the next '---'.
    """
    if not (content.startswith("---\n") or content.startswith("---\r\n")):
        return content

    # Find the closing --- after the opening one
    match = re.search(r"\n---\s*\n", content[3:])
    if match is None:
        return content  # Malformed frontmatter, return as-is

    end_pos = 3 + match.end()
    return content[end_pos:].lstrip("\n")


def render_plantuml(diagram: DiagramFile) -> RenderResult:
    """Render a PlantUML diagram to SVG using pipe mode.

    Uses pipe mode (stdin -> stdout) so we can strip frontmatter
    before passing content to plantuml.
    """
    if not _tool_available("plantuml"):
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.TOOL_MISSING,
            severity=Severity.ERROR,
            message="plantuml not found on PATH. Install: brew install plantuml",
        )

    try:
        content = diagram.source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"Cannot read source: {exc}",
        )

    if diagram.has_frontmatter:
        content = _strip_frontmatter(content)

    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["plantuml", "-tsvg", "-pipe"],
            input=content.encode("utf-8"),
            capture_output=True,
            timeout=RENDER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.monotonic() - start) * 1000
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"Render timed out after {RENDER_TIMEOUT}s",
            elapsed_ms=elapsed,
        )

    elapsed = (time.monotonic() - start) * 1000

    if proc.returncode != 0:
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"plantuml exited {proc.returncode}",
            elapsed_ms=elapsed,
            stderr_output=proc.stderr.decode("utf-8", errors="replace")[:500],
        )

    try:
        diagram.output.write_bytes(proc.stdout)
    except OSError as exc:
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"Cannot write SVG: {exc}",
            elapsed_ms=elapsed,
        )

    return RenderResult(
        diagram=diagram,
        status=RenderStatus.RENDERED,
        severity=Severity.INFO,
        message=f"Rendered {diagram.output.name}",
        elapsed_ms=elapsed,
    )


def render_mermaid(diagram: DiagramFile) -> RenderResult:
    """Render a Mermaid diagram to SVG using mmdc."""
    if not _tool_available("mmdc"):
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.TOOL_MISSING,
            severity=Severity.ERROR,
            message="mmdc not found on PATH. Install: npm install -g @mermaid-js/mermaid-cli",
        )

    start = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "mmdc",
                "-i",
                str(diagram.source),
                "-o",
                str(diagram.output),
                "-e",
                "svg",
                "-q",
            ],
            capture_output=True,
            timeout=RENDER_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        elapsed = (time.monotonic() - start) * 1000
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"Render timed out after {RENDER_TIMEOUT}s",
            elapsed_ms=elapsed,
        )

    elapsed = (time.monotonic() - start) * 1000

    if proc.returncode != 0:
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"mmdc exited {proc.returncode}",
            elapsed_ms=elapsed,
            stderr_output=proc.stderr.decode("utf-8", errors="replace")[:500],
        )

    return RenderResult(
        diagram=diagram,
        status=RenderStatus.RENDERED,
        severity=Severity.INFO,
        message=f"Rendered {diagram.output.name}",
        elapsed_ms=elapsed,
    )


# Dispatch table: format -> renderer function
RENDERERS: dict[DiagramFormat, Callable[[DiagramFile], RenderResult]] = {
    DiagramFormat.PLANTUML: render_plantuml,
    DiagramFormat.MERMAID: render_mermaid,
}


def render_diagram(diagram: DiagramFile) -> RenderResult:
    """Render a diagram using the appropriate tool."""
    renderer = RENDERERS.get(diagram.format)
    if renderer is None:
        return RenderResult(
            diagram=diagram,
            status=RenderStatus.FAILED,
            severity=Severity.ERROR,
            message=f"No renderer for format: {diagram.format.value}",
        )
    return renderer(diagram)
