# sv2svg

SystemVerilog (.sv) to SVG visualizer using Schemdraw logic gates.

- Left-to-right flow
- Grid-aligned verticals, minimal bends
- Symmetric sibling placement around shared drivers
- CLI: `sv2svg file.sv [-o out.svg] [--input-order ...] [--grid-x ...] [--grid-y ...] [--no-symmetry] [--version]`

## Install

With uvx (no install):

```sh
uvx sv2svg --help
```

With uv (local run):

```sh
uv run sv2svg --help
```

From source (editable):

```sh
pip install -e .
```

## Usage

```sh
sv2svg --version
sv2svg --help
sv2svg mymodule.sv -o mymodule.svg --input-order ports --grid-x 0.5 --grid-y 0.5
```

## Versioning & releases (SemVer)

This project follows Semantic Versioning. Versions are derived from git tags using hatch-vcs.

Release flow:

- Commits to `main` are analyzed with [semantic-release](https://semantic-release.gitbook.io). Use [Conventional Commits](https://www.conventionalcommits.org) to drive version bumps.
- When semantic-release detects a new version, it updates `CHANGELOG.md`, creates a Git tag (e.g. `v0.1.0`), and publishes a GitHub release.
- The tag push triggers the existing PyPI publish workflow, which builds the package and uploads it via trusted publishing.

Notes:

- Pre-releases use SemVer pre-release identifiers produced by semantic-release (e.g. `v0.2.0-rc.1`).
- Local builds without git metadata use a fallback version `0.0.0` from `hatch-vcs`.
