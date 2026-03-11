"""L1 unit tests for diagram_render.freshness — pure logic, no I/O."""

from pathlib import Path
from unittest.mock import patch

from diagram_render.freshness import (
    detect_format,
    has_yaml_frontmatter,
    is_in_archive,
    is_stale,
    resolve_output_path,
)
from diagram_render.models import DiagramFile, DiagramFormat


class TestDetectFormat:
    def test_plantuml(self):
        assert detect_format(Path("foo.puml")) == DiagramFormat.PLANTUML

    def test_mermaid_mmd(self):
        assert detect_format(Path("foo.mmd")) == DiagramFormat.MERMAID

    def test_mermaid_extension(self):
        assert detect_format(Path("foo.mermaid")) == DiagramFormat.MERMAID

    def test_unknown(self):
        assert detect_format(Path("foo.txt")) is None

    def test_case_insensitive(self):
        assert detect_format(Path("foo.PUML")) == DiagramFormat.PLANTUML


class TestResolveOutputPath:
    def test_puml_to_svg(self):
        assert resolve_output_path(Path("diagrams/seq.puml")) == Path("diagrams/seq.svg")

    def test_mmd_to_svg(self):
        assert resolve_output_path(Path("flow.mmd")) == Path("flow.svg")


class TestHasYamlFrontmatter:
    def test_with_frontmatter(self):
        assert has_yaml_frontmatter("---\ntitle: foo\n---\n@startuml") is True

    def test_without_frontmatter(self):
        assert has_yaml_frontmatter("@startuml\nAlice -> Bob") is False

    def test_crlf_frontmatter(self):
        assert has_yaml_frontmatter("---\r\ntitle: foo\r\n---\r\n") is True

    def test_dashes_not_at_start(self):
        assert has_yaml_frontmatter("some text\n---\n") is False


class TestIsInArchive:
    def test_in_archive(self):
        assert is_in_archive(Path("/repo/zArchive/old/diagram.puml")) is True

    def test_not_in_archive(self):
        assert is_in_archive(Path("/repo/docs/diagram.puml")) is False

    def test_case_insensitive(self):
        assert is_in_archive(Path("/repo/ZARCHIVE/diagram.puml")) is True


class TestIsStale:
    def test_missing_output(self, tmp_path):
        source = tmp_path / "test.puml"
        source.write_text("@startuml\n@enduml")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.PLANTUML,
            output=tmp_path / "test.svg",
        )
        assert is_stale(diagram) is True

    def test_fresh_output(self, tmp_path):
        source = tmp_path / "test.puml"
        source.write_text("@startuml\n@enduml")
        output = tmp_path / "test.svg"
        output.write_text("<svg/>")
        # Make output newer than source
        import os
        import time
        future = time.time() + 10
        os.utime(output, (future, future))
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.PLANTUML,
            output=output,
        )
        assert is_stale(diagram) is False

    def test_stale_output(self, tmp_path):
        source = tmp_path / "test.puml"
        output = tmp_path / "test.svg"
        output.write_text("<svg/>")
        import os
        import time
        # Make output old
        past = time.time() - 100
        os.utime(output, (past, past))
        # Write source after
        source.write_text("@startuml\n@enduml")
        diagram = DiagramFile(
            source=source,
            format=DiagramFormat.PLANTUML,
            output=output,
        )
        assert is_stale(diagram) is True
