# sv2svg

Convert SystemVerilog modules into readable logic-diagram SVGs with a single CLI command. sv2svg parses structural HDL, places gates left-to-right, and outputs Schemdraw-based graphics that stay aligned and symmetric.

## Highlights
- Deterministic left-to-right layout with minimal crossings
- Automatic input ordering (alphabetical, module ports, or auto)
- Optional grid snapping and symmetry controls
- CLI-first workflow with `--help`, `--version`, `--style`, and `--orientation` discovery
- Semantic-release driven SemVer tagging and automated PyPI publishing

## Installation
Choose one of the following approaches:

- **uvx (no install):**
  ```sh
  uvx sv2svg --help
  ```
- **uv run:**
  ```sh
  uv run sv2svg --help
  ```
- **Virtual environment:**
  ```sh
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install sv2svg
  ```
- **Editable checkout:**
  ```sh
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -e .
  ```

## Quickstart
```sh
sv2svg --help
sv2svg --version
sv2svg examples/full_adder.sv --style blueprint --orientation vertical -o full_adder.svg
```
The last command renders `examples/full_adder.sv` into an SVG file in the working directory (falls back to `full_adder_schemdraw.svg` when `-o` is omitted) using the "blueprint" color preset and a vertical layout.

## CLI reference
```
usage: sv2svg [-h] [-o OUTPUT] [--input-order {alpha,ports,auto}] [--grid-x GRID_X]
              [--grid-y GRID_Y] [--no-symmetry]
              [--style {classic,blueprint,midnight,mono}]
              [--orientation {horizontal,vertical}] [-V]
              input_file
```
- `input_file` — source SystemVerilog file with the module to visualize
- `-o / --output` — target SVG file path (`-` writes SVG to stdout)
- `--input-order` — sort inputs alphabetically, preserve declaration order, or auto-detect
- `--grid-x`, `--grid-y` — snap coordinates to half-grid (0 disables snapping)
- `--no-symmetry` — disable mirrored placement for sibling signals
- `--style` — select a color/line-weight preset for the output (`classic`, `blueprint`, `midnight`, `mono`)
- `--orientation` — choose `horizontal` (default left-to-right) or `vertical` (top-to-bottom) layout; vertical mode currently produces rotated SVG output only
- `-V / --version` — print the sv2svg version derived from git metadata

## Tips for better diagrams
- Keep each module in its own file and ensure port declarations are explicit.
- The parser expects synthesizable structural constructs; unsupported statements raise errors during generation.
- Use the grid options to align gates when mixing manual annotations with generated drawings.

## Development workflow
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
python -m sv2svg.cli --version
```
Run the CLI against fixtures or your own modules; any Python exception surfaces with a clear message.

## Testing
The CI workflow (`.github/workflows/ci.yml`) installs the package in editable mode and performs an import smoke test. Extend it with richer checks as the project grows.

## Release automation
- Commits merged to `main` must follow [Conventional Commits](https://www.conventionalcommits.org) so semantic-release can infer version bumps.
- On qualifying commits, the **Release** workflow updates `CHANGELOG.md`, tags the release, publishes GitHub release notes, and uploads the built artifacts to PyPI using trusted publishing.
- Local builds without git metadata fall back to version `0.0.0`; regular development builds look like `0.2.1.dev0+g8733005aa.d20250922` courtesy of hatch-vcs.

## Contributing
Issues and pull requests are welcome. Please include reproduction snippets for parser bugs and respect the release automation by using Conventional Commit messages.

## License
MIT
