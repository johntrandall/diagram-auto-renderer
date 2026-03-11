"""L1 unit tests for diagram_render.renderer — strip_frontmatter, tool checks, render paths."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from diagram_render.models import DiagramFile, DiagramFormat, RenderStatus
from diagram_render.renderer import (
    _strip_frontmatter,
    _tool_available,
    render_plantuml,
    render_mermaid,
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
