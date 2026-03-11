"""L1 unit tests for diagram_render.models — enum values and dataclass construction."""

from pathlib import Path

from diagram_render.models import (
    DiagramFile,
    DiagramFormat,
    EXTENSION_FORMAT_MAP,
    RenderResult,
    RenderStatus,
    Severity,
)


class TestEnumValues:
    def test_diagram_format_values(self):
        assert DiagramFormat.PLANTUML.value == "plantuml"
        assert DiagramFormat.MERMAID.value == "mermaid"

    def test_render_status_values(self):
        assert RenderStatus.RENDERED.value == "rendered"
        assert RenderStatus.SKIPPED_FRESH.value == "fresh"
        assert RenderStatus.SKIPPED_ARCHIVE.value == "archive"
        assert RenderStatus.FAILED.value == "failed"
        assert RenderStatus.TOOL_MISSING.value == "tool_missing"

    def test_severity_values(self):
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"


class TestExtensionMap:
    def test_puml_maps_to_plantuml(self):
        assert EXTENSION_FORMAT_MAP[".puml"] == DiagramFormat.PLANTUML

    def test_mmd_maps_to_mermaid(self):
        assert EXTENSION_FORMAT_MAP[".mmd"] == DiagramFormat.MERMAID

    def test_mermaid_maps_to_mermaid(self):
        assert EXTENSION_FORMAT_MAP[".mermaid"] == DiagramFormat.MERMAID


class TestDiagramFile:
    def test_construction(self):
        d = DiagramFile(
            source=Path("test.puml"),
            format=DiagramFormat.PLANTUML,
            output=Path("test.svg"),
        )
        assert d.has_frontmatter is False

    def test_with_frontmatter(self):
        d = DiagramFile(
            source=Path("test.puml"),
            format=DiagramFormat.PLANTUML,
            output=Path("test.svg"),
            has_frontmatter=True,
        )
        assert d.has_frontmatter is True


class TestRenderResult:
    def test_defaults(self):
        d = DiagramFile(
            source=Path("t.puml"),
            format=DiagramFormat.PLANTUML,
            output=Path("t.svg"),
        )
        r = RenderResult(
            diagram=d,
            status=RenderStatus.RENDERED,
            severity=Severity.INFO,
            message="ok",
        )
        assert r.elapsed_ms == 0.0
        assert r.stderr_output == ""
