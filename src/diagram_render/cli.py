"""CLI entry point for the diagram auto-renderer."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .freshness import (
    build_diagram_file,
    collect_diagram_sources,
    is_in_archive,
    is_stale,
)
from .models import (
    RenderResult,
    RenderStatus,
    Severity,
)
from .renderer import render_diagram

app = typer.Typer(help="Diagram auto-renderer: detect stale diagrams and re-render SVGs")
console = Console()


def _get_staged_diagram_files() -> list[Path]:
    """Get staged diagram files from git (ACM = added, copied, modified)."""
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACM",
                "--",
                "*.puml",
                "*.mmd",
                "*.mermaid",
                "*.d2",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return [Path(f) for f in result.stdout.strip().splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def _git_add(paths: list[Path]) -> bool:
    """Stage files with git add. Returns True on success."""
    if not paths:
        return True
    try:
        subprocess.run(
            ["git", "add", "--"] + [str(p) for p in paths],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _display_results(results: list[RenderResult]) -> bool:
    """Display results using rich. Returns True if any errors found."""
    if not results:
        console.print("[dim]No diagrams to process.[/dim]")
        return False

    has_errors = False
    rendered_count = sum(1 for r in results if r.status == RenderStatus.RENDERED)
    fresh_count = sum(1 for r in results if r.status == RenderStatus.SKIPPED_FRESH)
    failed_count = sum(
        1 for r in results if r.status in (RenderStatus.FAILED, RenderStatus.TOOL_MISSING)
    )

    # Only show table for interesting results (not skipped-fresh)
    interesting = [
        r for r in results if r.status not in (RenderStatus.SKIPPED_FRESH, RenderStatus.SKIPPED_ARCHIVE)
    ]

    if interesting:
        table = Table(title="Diagram Render Results", show_lines=True)
        table.add_column("Status", style="bold", width=12)
        table.add_column("File", max_width=60)
        table.add_column("Message")
        table.add_column("Time", width=8)

        for r in interesting:
            status_style = {
                RenderStatus.RENDERED: "green",
                RenderStatus.FAILED: "red",
                RenderStatus.TOOL_MISSING: "red",
            }.get(r.status, "dim")

            if r.status in (RenderStatus.FAILED, RenderStatus.TOOL_MISSING):
                has_errors = True

            time_str = f"{r.elapsed_ms:.0f}ms" if r.elapsed_ms > 0 else ""
            table.add_row(
                f"[{status_style}]{r.status.value}[/{status_style}]",
                str(r.diagram.source),
                r.message,
                time_str,
            )

        console.print(table)

    # Summary line
    parts = []
    if rendered_count:
        parts.append(f"[green]{rendered_count} rendered[/green]")
    if fresh_count:
        parts.append(f"[dim]{fresh_count} fresh[/dim]")
    if failed_count:
        parts.append(f"[red]{failed_count} failed[/red]")

    if parts:
        console.print("\n" + ", ".join(parts))

    return has_errors


@app.command()
def run(
    files: Optional[list[Path]] = typer.Argument(None, help="Diagram source files to render"),
    pre_commit: bool = typer.Option(False, "--pre-commit", help="Detect staged diagrams, render stale, auto-stage"),
    repo: Optional[Path] = typer.Option(None, "--repo", "-r", help="Scan all diagrams in repo"),
    check_only: bool = typer.Option(False, "--check-only", help="Report staleness without rendering"),
    strict: bool = typer.Option(False, "--strict", "-s", help="Exit 1 if any renders fail"),
    stage: bool = typer.Option(False, "--stage", help="Git add rendered SVGs (implied by --pre-commit)"),
    include_archive: bool = typer.Option(False, "--include-archive", help="Include files in zArchive/"),
) -> None:
    """Detect stale diagram sources and render fresh SVGs."""
    from .models import DiagramFile

    # Collect target diagrams
    targets: list[DiagramFile] = []

    if files:
        for f in files:
            resolved = f.resolve() if f.is_absolute() else (Path.cwd() / f).resolve()
            diagram = build_diagram_file(resolved)
            if diagram is None:
                console.print(f"[yellow]Skipping unsupported file: {f}[/yellow]")
                continue
            targets.append(diagram)

    elif pre_commit:
        staged = _get_staged_diagram_files()
        for f in staged:
            resolved = f.resolve() if f.is_absolute() else (Path.cwd() / f).resolve()
            diagram = build_diagram_file(resolved)
            if diagram is None:
                continue
            if not include_archive and is_in_archive(resolved):
                continue
            targets.append(diagram)
        stage = True  # --pre-commit implies --stage

    elif repo is not None:
        repo_path = repo.resolve() if repo != Path(".") else Path.cwd()
        targets = collect_diagram_sources(repo_path, include_archive=include_archive)

    else:
        console.print("[yellow]No files specified. Use positional files, --pre-commit, or --repo.[/yellow]")
        raise typer.Exit(0)

    if not targets:
        console.print("[dim]No diagram files to process.[/dim]")
        raise typer.Exit(0)

    # Process each diagram
    results: list[RenderResult] = []
    staged_svgs: list[Path] = []

    for diagram in targets:
        if not is_stale(diagram):
            results.append(
                RenderResult(
                    diagram=diagram,
                    status=RenderStatus.SKIPPED_FRESH,
                    severity=Severity.INFO,
                    message="SVG is up-to-date",
                )
            )
            continue

        if check_only:
            results.append(
                RenderResult(
                    diagram=diagram,
                    status=RenderStatus.FAILED,
                    severity=Severity.WARNING,
                    message=f"Stale: {diagram.source.name} needs re-rendering",
                )
            )
            continue

        result = render_diagram(diagram)
        results.append(result)

        if result.status == RenderStatus.RENDERED and stage:
            staged_svgs.append(diagram.output)

    # Auto-stage rendered SVGs
    if staged_svgs:
        if not _git_add(staged_svgs):
            console.print("[red]Failed to git add rendered SVGs[/red]")

    has_errors = _display_results(results)

    if strict and has_errors:
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the diagram-render CLI."""
    app()
