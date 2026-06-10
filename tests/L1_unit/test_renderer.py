"""L1 unit tests for diagram_render.renderer — strip_frontmatter, tool checks, render paths."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from diagram_render.models import DiagramFile, DiagramFormat, RenderStatus
from diagram_render.renderer import (
    _normalize_mermaid_newlines,
    _strip_frontmatter,
    _tool_available,
    render_plantuml,
    render_mermaid,
    render_d2,
)


class TestStripFrontmatter:
    def test_strips_yaml_frontmatter(self):
        content = "---\ntitle: Test\nauthor: Me\n---\n@startuml\nAlice -> Bob\n@enduml"
        result = _strip_frontmatter(content)
        assert result.startswith("@startuml")
        assert "title:" not in result

    def test_no_frontmatter_passthrough(self):
        content = "@startuml\nAlice -> Bob\n@enduml"
        assert _strip_frontmatter(content) == content

    def test_malformed_frontmatter(self):
        # Only opening --- with no closing
        content = "---\ntitle: Test\n@startuml\n@enduml"
        assert _strip_frontmatter(content) == content

    def test_crlf_frontmatter(self):
        content = "---\r\ntitle: Test\r\n---\r\n@startuml"
        result = _strip_frontmatter(content)
        assert result.startswith("@startuml")

    def test_empty_frontmatter(self):
        content = "---\n---\n@startuml"
        result = _strip_frontmatter(content)
        assert result.startswith("@startuml")


class TestNormalizeMermaidNewlines:
    def test_quoted_label_with_newline(self):
        src = 'A["foo\\nbar"] --> B'
        out = _normalize_mermaid_newlines(src)
        assert out == 'A["foo<br/>bar"] --> B'

    def test_multiple_newlines_in_one_label(self):
        src = 'A{"line1\\nline2\\nline3"}'
        out = _normalize_mermaid_newlines(src)
        assert out == 'A{"line1<br/>line2<br/>line3"}'

    def test_unquoted_text_untouched(self):
        # Bare \n outside quotes (e.g. in a comment or classDef) must stay literal.
        src = 'classDef foo fill:#fff\n%% comment with \\n in it\nA[B]'
        out = _normalize_mermaid_newlines(src)
        assert out == src

    def test_passthrough_when_no_newlines(self):
        src = 'A["plain label"] --> B["other"]'
        assert _normalize_mermaid_newlines(src) == src

    def test_escaped_quote_inside_label_preserved(self):
        # \" inside a label must not terminate the regex match prematurely.
        src = 'A["he said \\"hi\\"\\nthen left"]'
        out = _normalize_mermaid_newlines(src)
        assert out == 'A["he said \\"hi\\"<br/>then left"]'

    def test_edge_label_normalized(self):
        src = 'A -->|"line one\\nline two"| B'
        out = _normalize_mermaid_newlines(src)
        assert out == 'A -->|"line one<br/>line two"| B'


class TestToolAvailable:
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/plantuml")
    def test_available(self, mock_which):
        assert _tool_available("plantuml") is True
        mock_which.assert_called_once_with("plantuml")

    @patch("diagram_render.renderer.shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        assert _tool_available("plantuml") is False


class TestRenderPlantumlToolMissing:
    @patch("diagram_render.renderer.shutil.which", return_value=None)
    def test_tool_missing(self, mock_which, tmp_path):
        source = tmp_path / "test.puml"
        source.write_text("@startuml\n@enduml")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.PLANTUML,
            output=tmp_path / "test.svg",
        )
        result = render_plantuml(diagram)
        assert result.status == RenderStatus.TOOL_MISSING
        assert "plantuml" in result.message.lower()


class TestRenderMermaidToolMissing:
    @patch("diagram_render.renderer.shutil.which", return_value=None)
    def test_tool_missing(self, mock_which, tmp_path):
        source = tmp_path / "test.mmd"
        source.write_text("graph TD\n  A-->B")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.MERMAID,
            output=tmp_path / "test.svg",
        )
        result = render_mermaid(diagram)
        assert result.status == RenderStatus.TOOL_MISSING
        assert "mmdc" in result.message.lower()


class TestRenderD2ToolMissing:
    @patch("diagram_render.renderer.shutil.which", return_value=None)
    def test_tool_missing(self, mock_which, tmp_path):
        source = tmp_path / "test.d2"
        source.write_text("a -> b")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.D2,
            output=tmp_path / "test.svg",
        )
        result = render_d2(diagram)
        assert result.status == RenderStatus.TOOL_MISSING
        assert "d2" in result.message.lower()


class TestRenderD2Timeout:
    @patch("diagram_render.renderer.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="d2", timeout=30))
    @patch("diagram_render.renderer.shutil.which", return_value="/opt/homebrew/bin/d2")
    def test_timeout_returns_failed(self, mock_which, mock_run, tmp_path):
        source = tmp_path / "test.d2"
        source.write_text("a -> b")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.D2,
            output=tmp_path / "test.svg",
        )
        result = render_d2(diagram)
        assert result.status == RenderStatus.FAILED
        assert "timed out" in result.message.lower()


class TestRenderPlantumlTimeout:
    @patch("diagram_render.renderer.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="plantuml", timeout=30))
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/plantuml")
    def test_timeout_returns_failed(self, mock_which, mock_run, tmp_path):
        source = tmp_path / "test.puml"
        source.write_text("@startuml\n@enduml")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.PLANTUML,
            output=tmp_path / "test.svg",
        )
        result = render_plantuml(diagram)
        assert result.status == RenderStatus.FAILED
        assert "timed out" in result.message.lower()
