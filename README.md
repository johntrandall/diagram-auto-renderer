# diagram-auto-renderer

`diagram-render` keeps rendered diagrams in step with their sources. It finds diagram source
files whose `.svg` is missing or older than the source, and renders them:

| Source | Renderer it calls |
|---|---|
| `.mermaid`, `.mmd` | `mmdc` ([mermaid-cli](https://github.com/mermaid-js/mermaid-cli)) |
| `.puml` | `plantuml` |
| `.d2` | `d2` ([D2](https://d2lang.com)) |

Install only the renderers for the formats you use. A missing renderer is reported as
`tool_missing`, not as a broken diagram.

## Install

```bash
brew tap johntrandall/tap
brew install diagram-render
```

Without Homebrew: `uv tool install git+https://github.com/johntrandall/diagram-auto-renderer`
(or the same with `pipx install`). Python 3.10 or later.

## Use

```
diagram-render docs/flow.mermaid            # render one file (writes docs/flow.svg)
diagram-render --repo .                     # render every stale diagram in a repo
diagram-render --repo . --check-only        # report stale diagrams, render nothing
diagram-render --strict docs/flow.mermaid   # exit 1 if any render fails
diagram-render --pre-commit                 # render staged diagrams and stage the SVGs
```

Files under a `zArchive/` folder are skipped unless you pass `--include-archive`.

As a git pre-commit hook, `diagram-render --pre-commit` re-renders the diagrams you staged and
adds the fresh SVGs to the same commit. The
[mermaid Claude Code plugin](https://github.com/johntrandall/claude-plugin-mermaid) uses
`diagram-render --strict` to check every Mermaid file Claude writes.

## Develop

```
uv sync
uv run pytest
```

## Licence

MIT, see [LICENSE](LICENSE).
