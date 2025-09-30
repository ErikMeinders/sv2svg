#!/usr/bin/env python3
"""
Test script for the new layout engine.
This tests the layout engine independently from SVCircuit to verify it works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sv2svg.layout import LayoutEngine, LayoutConfig
from sv2svg.core import SVCircuit


def test_layout_engine_with_mux2to1():
    """Test the layout engine with the mux2to1 example."""
    print("Testing Layout Engine with mux2to1 example...")

    # Parse the circuit using SVCircuit to get the gate information
    circuit = SVCircuit()
    circuit.parse_file('test_mux2to1.sv')

    print(f"Parsed circuit: {circuit.module_name}")
    print(f"Inputs: {circuit.inputs}")
    print(f"Outputs: {circuit.outputs}")
    print(f"Gates: {len(circuit.gates)}")

    for gate in circuit.gates:
        print(f"  {gate.name}: {gate.type}({', '.join(gate.inputs)}) -> {gate.output} [level {gate.level}]")

    # Create layout engine
    config = LayoutConfig()
    layout_engine = LayoutEngine(config)

    # Add gates to layout engine
    for gate in circuit.gates:
        layout_engine.add_gate(gate.name, gate.type, gate.inputs, gate.output)

    # Set connectivity
    layout_engine.set_connectivity(circuit.signal_driver, circuit.signal_sinks)

    # Run layout algorithms
    layout_engine.assign_levels()
    layout_engine.reorder_by_barycenter(circuit.inputs)

    print("\nAfter layout engine processing:")
    for layout_gate in layout_engine.gates:
        print(f"  {layout_gate.name}: level {layout_gate.level}")

    # Position gates
    sig_source_pt = layout_engine.position_gates(circuit.inputs, 'alpha', circuit.port_order)

    print("\nSignal source points:")
    for sig, pt in sig_source_pt.items():
        print(f"  {sig}: {pt}")

    print("\nLayout gate positions:")
    for layout_gate in layout_engine.gates:
        print(f"  {layout_gate.name}: ({layout_gate.x}, {layout_gate.y})")

    # Create routing plan
    signals = layout_engine.create_routing_plan(sig_source_pt, circuit.inputs, circuit.outputs)

    print("\nRouting signals:")
    for sig_name, signal in signals.items():
        print(f"  {sig_name}: source {signal.source_point} -> sinks {signal.sink_points}")

    # Generate routing commands
    routing_commands = layout_engine.generate_optimized_routing(signals)

    print(f"\nGenerated {len(routing_commands)} routing commands:")
    for i, cmd in enumerate(routing_commands[:10]):  # Show first 10 commands
        print(f"  {i+1}: {cmd}")
    if len(routing_commands) > 10:
        print(f"  ... and {len(routing_commands) - 10} more commands")

    print("\nLayout engine test completed successfully!")
    return True


if __name__ == '__main__':
    try:
        success = test_layout_engine_with_mux2to1()
        if success:
            print("✓ Layout engine test passed")
            sys.exit(0)
        else:
            print("✗ Layout engine test failed")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Layout engine test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)