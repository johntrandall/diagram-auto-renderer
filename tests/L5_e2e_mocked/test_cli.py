"""L5 E2E mocked tests for the diagram-render CLI.

Creates a real git repo in /tmp with staged diagram files, then runs the CLI
with mocked plantuml/mmdc subprocess calls.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from diagram_render.cli import app


runner = CliRunner()


@pytest.fixture
def mock_git_repo():
    """Create a temp git repo with staged .puml and .mmd files."""
    repo = Path(tempfile.mkdtemp(dir="/tmp", prefix="diagram_e2e_"))
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo, capture_output=True,
    )

    # Create diagram files
    puml = repo / "seq.puml"
    puml.write_text("@startuml\nAlice -> Bob: hello\n@enduml\n")
    mmd = repo / "flow.mmd"
    mmd.write_text("graph TD\n  A --> B\n")

    # Stage them
    subprocess.run(["git", "add", "seq.puml", "flow.mmd"], cwd=repo, capture_output=True)

    yield repo

    shutil.rmtree(repo)


class TestCliHelp:
    def test_help_exits_zero(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Detect stale diagram sources" in result.output


class TestCliCheckOnly:
    def test_check_only_with_files(self, mock_git_repo):
        """--check-only should report stale files without rendering."""
        puml = mock_git_repo / "seq.puml"
        result = runner.invoke(app, [str(puml), "--check-only", "--strict"])
        # Should report stale (no SVG exists) and exit 1 with --strict
        assert result.exit_code == 1

    def test_check_only_fresh_file(self, mock_git_repo):
        """--check-only with a fresh SVG should skip and exit 0."""
        puml = mock_git_repo / "seq.puml"
        svg = mock_git_repo / "seq.svg"
        svg.write_text("<svg/>")
        # Make SVG newer
        import time
        future = time.time() + 10
        os.utime(svg, (future, future))

        result = runner.invoke(app, [str(puml), "--check-only"])
        assert result.exit_code == 0


class TestCliPreCommit:
    def test_pre_commit_check_only(self, mock_git_repo):
        """--pre-commit --check-only should detect staged diagrams."""
        # Run from the repo dir
        original_cwd = os.getcwd()
        os.chdir(mock_git_repo)
        try:
            result = runner.invoke(app, ["--pre-commit", "--check-only", "--strict"])
            # Should find staged files and report them stale
            assert result.exit_code == 1
        finally:
            os.chdir(original_cwd)


class TestCliRepoScan:
    def test_repo_scan_check_only(self, mock_git_repo):
        """--repo should scan all diagrams in directory."""
        result = runner.invoke(
            app, ["--repo", str(mock_git_repo), "--check-only", "--strict"]
        )
        # Both files are stale (no SVGs)
        assert result.exit_code == 1


class TestCliRenderMocked:
    @patch("diagram_render.renderer.subprocess.run")
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/plantuml")
    def test_render_plantuml_mocked(self, mock_which, mock_run, mock_git_repo):
        """Render a .puml file with mocked plantuml subprocess."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"<svg>mocked</svg>"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        puml = mock_git_repo / "seq.puml"
        result = runner.invoke(app, [str(puml)])
        assert result.exit_code == 0
        # Verify plantuml was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert "plantuml" in call_args[0][0]

    @patch("diagram_render.renderer.subprocess.run")
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/mmdc")
    def test_render_mermaid_mocked(self, mock_which, mock_run, mock_git_repo):
        """Render a .mmd file with mocked mmdc subprocess."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        mmd = mock_git_repo / "flow.mmd"
        # Create the output file as mmdc would
        svg = mock_git_repo / "flow.svg"
        svg.write_text("<svg>mocked</svg>")

        result = runner.invoke(app, [str(mmd)])
        assert result.exit_code == 0

    @patch("diagram_render.renderer.subprocess.run")
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/plantuml")
    def test_render_failure_strict(self, mock_which, mock_run, mock_git_repo):
        """Failed render with --strict should exit 1."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = b""
        mock_proc.stderr = b"error: bad diagram"
        mock_run.return_value = mock_proc

        puml = mock_git_repo / "seq.puml"
        result = runner.invoke(app, [str(puml), "--strict"])
        assert result.exit_code == 1


class TestCliGitAddFailure:
    @patch("diagram_render.cli._git_add", return_value=False)
    @patch("diagram_render.renderer.subprocess.run")
    @patch("diagram_render.renderer.shutil.which", return_value="/usr/bin/plantuml")
    def test_git_add_failure_shows_error(self, mock_which, mock_run, mock_git_add, mock_git_repo):
        """Failed git add should show error message in output."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = b"<svg>mocked</svg>"
        mock_proc.stderr = b""
        mock_run.return_value = mock_proc

        puml = mock_git_repo / "seq.puml"
        result = runner.invoke(app, [str(puml), "--stage"])
        assert "Failed to git add" in result.output


class TestCliNoFiles:
    def test_no_args(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "No files specified" in result.output
