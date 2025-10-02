# sv2svg

Convert SystemVerilog modules into readable logic-diagram SVGs with a single CLI command. sv2svg parses structural HDL, places gates left-to-right, and outputs Schemdraw-based graphics that stay aligned and symmetric.

## Highlights
- Deterministic left-to-right layout with minimal crossings
- Automatic input ordering (alphabetical, module ports, or auto)
- Optional grid snapping and symmetry controls
- **Visual enhancements**: gate fill colors, line styling, fan-out indicators, 6 style presets
- **Full expression parser**: supports complex boolean expressions with operator precedence
- **Truth table generation**: automatic verification for circuits ≤5 inputs
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

# Basic usage
sv2svg input.sv -o output.svg

# With visual enhancements
sv2svg input.sv --fill-gates --signal-styles --style vibrant -o output.svg

# Full-featured diagram with truth table
sv2svg input.sv --fill-gates --signal-styles --fanout-wires --table --style vibrant -o output.svg

# Vertical layout with dark theme
sv2svg input.sv --orientation vertical --style dark -o output.svg
```

## CLI reference
```
usage: sv2svg [-h] [-o OUTPUT] [--input-order {alpha,ports,auto}]
              [--grid-x GRID_X] [--grid-y GRID_Y] [--no-symmetry]
              [--style {classic,blueprint,midnight,mono,vibrant,dark}]
              [--orientation {horizontal,vertical}] [--table] [--no-caption]
              [--fill-gates] [--signal-styles] [--fanout-wires] [-V]
              input_file
```

### Basic Options
- `input_file` — source SystemVerilog file with the module to visualize
- `-o / --output` — target SVG file path (`-` writes SVG to stdout)
- `-V / --version` — print the sv2svg version derived from git metadata

### Layout Options
- `--input-order {alpha,ports,auto}` — sort inputs alphabetically, preserve declaration order, or auto-detect (default: `alpha`)
- `--grid-x GRID_X` — snap X coordinates to grid (default: 0.5, use 0 to disable)
- `--grid-y GRID_Y` — snap Y coordinates to grid (default: 0.5, use 0 to disable)
- `--no-symmetry` — disable mirrored placement for sibling signals around shared drivers
- `--orientation {horizontal,vertical}` — layout direction: left-to-right or top-to-bottom (default: `horizontal`)

### Style Presets
- `--style {classic,blueprint,midnight,mono,vibrant,dark}` — color/line-weight preset (default: `classic`)
  - `classic` — Dark blue-gray with subtle styling
  - `blueprint` — NASA blue for technical documentation
  - `midnight` — Cyan on dark background
  - `mono` — Grayscale for print-friendly output
  - `vibrant` — Bright gate colors (best with `--fill-gates`)
  - `dark` — Light-on-dark theme for dark mode documentation

### Visualization Enhancements
- `--fill-gates` — Add subtle fill colors to logic gates for visual distinction
- `--signal-styles` — Use line styles to distinguish signal types (solid=primary I/O, dashed=intermediate)
- `--fanout-wires` — Use thicker lines for signals driving multiple gates (visual fan-out indicator)
- `--table` — Include truth table in diagram (only for circuits with ≤5 inputs)
- `--no-caption` — Suppress "Module: modulename" caption for cleaner diagrams

## Tips for better diagrams
- Keep each module in its own file and ensure port declarations are explicit.
- The parser expects synthesizable structural constructs; unsupported statements raise errors during generation.
- Use the grid options to align gates when mixing manual annotations with generated drawings.

## Supported SystemVerilog Constructs

sv2svg is designed for **structural SystemVerilog** and supports both explicit gate instantiations and complex boolean expressions in `assign` statements.

### ✅ Fully Supported: Gate Instantiations
```verilog
module example(a, b, y);
  input logic a, b;
  output logic y;

  logic ab;
  AND u1(a, b, ab);
  NOT u2(ab, y);
endmodule
```

**Supported gate types**: AND, OR, NAND, NOR, XOR, XNOR, NOT/INV, BUF/BUFFER

### ✅ Fully Supported: Complex Assign Expressions
The **full expression parser** handles complex boolean expressions with proper operator precedence and parentheses:

```verilog
// Simple expressions
assign y = a & b;              // AND gate
assign y = a | b;              // OR gate
assign y = ~a;                 // NOT gate

// Operator precedence (NOT > AND > OR/XOR)
assign y = a | b & c;          // OR(a, AND(b,c))
assign y = ~a & b | c;         // OR(AND(NOT(a),b), c)

// Parentheses override precedence
assign y = (a | b) & c;        // AND(OR(a,b), c)
assign y = ~(a & b | c);       // NOT(OR(AND(a,b), c))

// Multi-input expressions (cascaded gates)
assign y = a & b & c;          // AND(AND(a,b), c) with auto-generated intermediate signal
assign y = a | b | c | d;      // Cascaded OR gates

// Complex nested expressions
assign y = (a & b) | (c & d);  // OR(AND(a,b), AND(c,d))
assign y = ~((a | b) & c);     // NOT(AND(OR(a,b), c))
```

The parser automatically:
- Generates intermediate signals for complex expressions (`_expr_1`, `_expr_2`, etc.)
- Applies correct operator precedence
- Handles nested parentheses
- Creates cascaded gates for multi-input operations

### ❌ Not Supported
The parser **cannot** handle:
- Ternary operators: `assign y = sel ? a : b;`
- Bit operations: `assign y = a[0] & b[1];`
- Arithmetic: `assign y = a + b;`
- Comparison operators: `assign y = a > b;`

For these constructs, use explicit gate instantiations or different HDL representations.

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
