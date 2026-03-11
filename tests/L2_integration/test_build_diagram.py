"""L2 integration tests for build_diagram_file and collect_diagram_sources.

Uses real temp files in /tmp to test module-level wiring.
"""

import os
import tempfile
from pathlib import Path

from diagram_render.freshness import build_diagram_file, collect_diagram_sources
from diagram_render.models import DiagramFormat


class TestBuildDiagramFile:
    def test_plantuml_without_frontmatter(self):
        with tempfile.NamedTemporaryFile(
            suffix=".puml", dir="/tmp", mode="w", delete=False
        ) as f:
            f.write("@startuml\nAlice -> Bob\n@enduml\n")
            f.flush()
            path = Path(f.name)

        try:
            diagram = build_diagram_file(path)
            assert diagram is not None
            assert diagram.format == DiagramFormat.PLANTUML
            assert diagram.output == path.with_suffix(".svg")
            assert diagram.has_frontmatter is False
        finally:
            path.unlink()

    def test_plantuml_with_frontmatter(self):
        with tempfile.NamedTemporaryFile(
            suffix=".puml", dir="/tmp", mode="w", delete=False
        ) as f:
            f.write("---\ntitle: Test\n---\n@startuml\n@enduml\n")
            f.flush()
            path = Path(f.name)

        try:
            diagram = build_diagram_file(path)
            assert diagram is not None
            assert diagram.has_frontmatter is True
        finally:
            path.unlink()

    def test_mermaid_file(self):
        with tempfile.NamedTemporaryFile(
            suffix=".mmd", dir="/tmp", mode="w", delete=False
        ) as f:
            f.write("graph TD\n  A --> B\n")
            f.flush()
            path = Path(f.name)

        try:
            diagram = build_diagram_file(path)
            assert diagram is not None
            assert diagram.format == DiagramFormat.MERMAID
            # Mermaid doesn't check frontmatter
            assert diagram.has_frontmatter is False
        finally:
            path.unlink()

    def test_unsupported_extension(self):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", dir="/tmp", mode="w", delete=False
        ) as f:
            f.write("not a diagram\n")
            path = Path(f.name)

        try:
            assert build_diagram_file(path) is None
        finally:
            path.unlink()


class TestCollectDiagramSources:
    def test_finds_diagrams_in_tree(self):
        base = Path(tempfile.mkdtemp(dir="/tmp", prefix="diagram_test_"))
        try:
            # Create diagram files
            (base / "docs").mkdir()
            (base / "docs" / "seq.puml").write_text("@startuml\n@enduml")
            (base / "docs" / "flow.mmd").write_text("graph TD\n  A-->B")
            (base / "docs" / "readme.md").write_text("# Docs")
            # Create archive that should be excluded
            (base / "zArchive").mkdir()
            (base / "zArchive" / "old.puml").write_text("@startuml\n@enduml")

            results = collect_diagram_sources(base, include_archive=False)
            names = [d.source.name for d in results]
            assert "seq.puml" in names
            assert "flow.mmd" in names
            assert "old.puml" not in names
            assert "readme.md" not in names
        finally:
            import shutil
            shutil.rmtree(base)

    def test_include_archive(self):
        base = Path(tempfile.mkdtemp(dir="/tmp", prefix="diagram_test_"))
        try:
            (base / "zArchive").mkdir()
            (base / "zArchive" / "old.puml").write_text("@startuml\n@enduml")

            results = collect_diagram_sources(base, include_archive=True)
            names = [d.source.name for d in results]
            assert "old.puml" in names
        finally:
            import shutil
            shutil.rmtree(base)

    def test_excludes_venv_and_node_modules(self):
        base = Path(tempfile.mkdtemp(dir="/tmp", prefix="diagram_test_"))
        try:
            (base / ".venv" / "lib").mkdir(parents=True)
            (base / ".venv" / "lib" / "dep.puml").write_text("@startuml\n@enduml")
            (base / "node_modules" / "pkg").mkdir(parents=True)
            (base / "node_modules" / "pkg" / "dep.mmd").write_text("graph TD")

            results = collect_diagram_sources(base)
            assert len(results) == 0
        finally:
            import shutil
            shutil.rmtree(base)
