#!/usr/bin/env python3
"""Test script to verify inline port type specification fix"""

from src.sv2svg.core import SVCircuit

# Test 1: Inline port declarations
print("Test 1: Inline port type specifications")
print("=" * 60)
circuit = SVCircuit()
circuit.parse_file('tests/fixtures/inline_ports.sv')

print(f"Module name: {circuit.module_name}")
print(f"Port order: {circuit.port_order}")
print(f"Inputs: {circuit.inputs}")
print(f"Outputs: {circuit.outputs}")

assert circuit.module_name == "func", f"Expected 'func', got '{circuit.module_name}'"
assert circuit.port_order == ['a', 'b', 'c', 'y'], f"Expected ['a', 'b', 'c', 'y'], got {circuit.port_order}"
assert set(circuit.inputs) == {'a', 'b', 'c'}, f"Expected {{a, b, c}}, got {set(circuit.inputs)}"
assert set(circuit.outputs) == {'y'}, f"Expected {{y}}, got {set(circuit.outputs)}"

print("✓ Test 1 PASSED\n")

# Test 2: Standalone port declarations (backward compatibility)
print("Test 2: Standalone port declarations (backward compatibility)")
print("=" * 60)
circuit2 = SVCircuit()
circuit2.parse_file('examples/basic_gates.sv')

print(f"Module name: {circuit2.module_name}")
print(f"Port order: {circuit2.port_order}")
print(f"Inputs: {circuit2.inputs}")
print(f"Outputs: {circuit2.outputs}")

assert circuit2.module_name == "basic_gates", f"Expected 'basic_gates', got '{circuit2.module_name}'"
assert set(circuit2.inputs) == {'a', 'b'}, f"Expected {{a, b}}, got {set(circuit2.inputs)}"
assert 'y_and' in circuit2.outputs and 'y_or' in circuit2.outputs, f"Expected outputs with y_and and y_or, got {circuit2.outputs}"

print("✓ Test 2 PASSED\n")

# Test 3: Full adder (backward compatibility)
print("Test 3: Full adder (backward compatibility)")
print("=" * 60)
circuit3 = SVCircuit()
circuit3.parse_file('examples/full_adder.sv')

print(f"Module name: {circuit3.module_name}")
print(f"Port order: {circuit3.port_order}")
print(f"Inputs: {circuit3.inputs}")
print(f"Outputs: {circuit3.outputs}")

assert circuit3.module_name == "full_adder", f"Expected 'full_adder', got '{circuit3.module_name}'"
assert set(circuit3.inputs) == {'a', 'b', 'cin'}, f"Expected {{a, b, cin}}, got {set(circuit3.inputs)}"
assert set(circuit3.outputs) == {'sum', 'cout'}, f"Expected {{sum, cout}}, got {set(circuit3.outputs)}"

print("✓ Test 3 PASSED\n")

print("=" * 60)
print("All tests PASSED! ✓")
print("=" * 60)
