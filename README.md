# sv2svg

SystemVerilog (.sv) to SVG visualizer using Schemdraw logic gates.

- Left-to-right flow
- Grid-aligned verticals, minimal bends
- Symmetric sibling placement around shared drivers
- CLI: `sv2svg file.sv [-o out.svg] [--input-order ...] [--grid-x ...] [--grid-y ...] [--no-symmetry]`

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

## Versioning & releases (SemVer)

This project follows Semantic Versioning. Versions are derived from git tags using hatch-vcs.

Release flow:

- Update code and commit to main
- Tag a release, e.g. `v0.1.0`
- Push the tag; GitHub Actions will build and publish to PyPI (trusted publishing)

Notes:

- Pre-releases use SemVer pre-release identifiers, e.g. `v0.2.0-rc.1`
- Local builds without git metadata use a fallback version `0.0.0`

```sh
sv2svg mymodule.sv -o mymodule.svg --input-order ports --grid-x 0.5 --grid-y 0.5
```

