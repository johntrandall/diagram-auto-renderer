"""Shared data models for the diagram auto-renderer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class DiagramFormat(Enum):
    """Supported diagram source formats."""

    PLANTUML = "plantuml"  # .puml
    MERMAID = "mermaid"  # .mmd, .mermaid


class Severity(Enum):
    """Result severity level."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RenderStatus(Enum):
    """Outcome of a single render operation."""

    RENDERED = "rendered"
    SKIPPED_FRESH = "fresh"
    SKIPPED_ARCHIVE = "archive"
    FAILED = "failed"
    TOOL_MISSING = "tool_missing"


@dataclass
class DiagramFile:
    """A diagram source file with its metadata."""

    source: Path
    format: DiagramFormat
    output: Path  # Expected SVG output path (same dir, same stem + .svg)
    has_frontmatter: bool = False


@dataclass
class RenderResult:
    """Outcome of rendering a single diagram."""

    diagram: DiagramFile
    status: RenderStatus
    severity: Severity
    message: str
    elapsed_ms: float = 0.0
    stderr_output: str = ""


# Extension-to-format mapping
EXTENSION_FORMAT_MAP: dict[str, DiagramFormat] = {
    ".puml": DiagramFormat.PLANTUML,
    ".mmd": DiagramFormat.MERMAID,
    ".mermaid": DiagramFormat.MERMAID,
}
