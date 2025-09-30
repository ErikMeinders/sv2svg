# SystemVerilog Examples

This directory contains example SystemVerilog files to demonstrate sv2svg functionality.

## Example Files

### `basic_gates.sv`
Simple example showing basic logic gates (AND, OR, NOT) using gate instantiations.

```bash
sv2svg examples/basic_gates.sv -o basic_gates.svg
```

### `full_adder.sv`
Complete 1-bit full adder implementation using XOR, AND, and OR gates. Referenced in the main README.

```bash
sv2svg examples/full_adder.sv --style blueprint --orientation vertical -o full_adder.svg
```

### `mux2to1.sv`
2-to-1 multiplexer demonstrating conditional logic using basic gates.

```bash
sv2svg examples/mux2to1.sv --style midnight -o mux2to1.svg
```

### `complex_logic.sv`
More comprehensive example showing all supported gate types: AND, OR, NAND, NOR, XOR, XNOR, NOT, BUF.

```bash
sv2svg examples/complex_logic.sv --style mono -o complex_logic.svg
```

### `assign_statements.sv`
Demonstrates limited behavioral SystemVerilog support using simple assign statements that sv2svg can convert to gates.

```bash
sv2svg examples/assign_statements.sv --style classic -o assign_statements.svg
```

## Try Different Styles and Orientations

Each example can be rendered with different visual styles:
- `classic` - Dark blue-gray (default)
- `blueprint` - NASA blue
- `midnight` - Cyan on dark
- `mono` - Grayscale

And orientations:
- `horizontal` - Left-to-right (default)
- `vertical` - Top-to-bottom

Example with all options:
```bash
sv2svg examples/full_adder.sv --style blueprint --orientation vertical --grid-x 10 --grid-y 10 --no-symmetry -o full_adder_custom.svg
```