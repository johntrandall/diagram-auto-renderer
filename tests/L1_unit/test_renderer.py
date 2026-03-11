"""L1 unit tests for diagram_render.renderer — strip_frontmatter and tool checks."""

from unittest.mock import patch

from diagram_render.renderer import _strip_frontmatter, _tool_available


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
