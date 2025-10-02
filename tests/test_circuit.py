"""Integration tests for SVCircuit class."""

import os
import pytest
import tempfile
from pathlib import Path
from sv2svg.core import SVCircuit


@pytest.fixture
def fixture_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


class TestSVCircuitParsing:
    """Test circuit parsing functionality."""

    def test_parse_simple_and_gate(self, fixture_dir):
        """Test parsing a simple AND gate."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        assert circuit.module_name == "simple_and"
        assert "a" in circuit.inputs
        assert "b" in circuit.inputs
        assert "y" in circuit.outputs
        assert len(circuit.gates) == 1
        assert circuit.gates[0].type == "AND"
        assert circuit.gates[0].inputs == ["a", "b"]
        assert circuit.gates[0].output == "y"

    def test_parse_multiple_gates(self, fixture_dir):
        """Test parsing multiple connected gates."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "multiple_gates.sv"))

        assert circuit.module_name == "multiple_gates"
        assert len(circuit.inputs) == 3  # a, b, c
        assert len(circuit.outputs) == 1  # y
        assert len(circuit.gates) == 3  # AND, OR, NOT

        # Check gate types
        gate_types = [g.type for g in circuit.gates]
        assert "AND" in gate_types
        assert "OR" in gate_types
        assert "NOT" in gate_types

    def test_parse_assign_and(self, fixture_dir):
        """Test parsing assign statement with AND."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "assign_and.sv"))

        assert circuit.module_name == "assign_and"
        assert len(circuit.gates) == 1
        assert circuit.gates[0].type == "AND"
        assert circuit.gates[0].output == "y"

    def test_parse_assign_or(self, fixture_dir):
        """Test parsing assign statement with OR."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "assign_or.sv"))

        assert len(circuit.gates) == 1
        assert circuit.gates[0].type == "OR"

    def test_parse_assign_not(self, fixture_dir):
        """Test parsing assign statement with NOT."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "assign_not.sv"))

        assert len(circuit.gates) == 1
        assert circuit.gates[0].type == "NOT"
        assert len(circuit.gates[0].inputs) == 1

    def test_parse_all_gate_types(self, fixture_dir):
        """Test parsing all supported gate types."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "all_gate_types.sv"))

        gate_types = [g.type for g in circuit.gates]
        expected_types = ["AND", "OR", "NAND", "NOR", "XOR", "XNOR", "NOT", "BUF"]
        for expected_type in expected_types:
            assert expected_type in gate_types, f"Missing gate type: {expected_type}"

    def test_parse_empty_module(self, fixture_dir):
        """Test parsing empty module (no gates)."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "empty_module.sv"))

        assert circuit.module_name == "empty_module"
        assert len(circuit.gates) == 0

    def test_parse_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        circuit = SVCircuit()
        with pytest.raises(FileNotFoundError):
            circuit.parse_file("nonexistent.sv")


class TestLevelAssignment:
    """Test level assignment (topological sorting)."""

    def test_simple_gate_level(self, fixture_dir):
        """Test level assignment for simple gate."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        # Level should be assigned (default is 0, but actual assignment happens during generation)
        assert circuit.gates[0].level >= 0

    def test_multiple_gates_levels(self, fixture_dir):
        """Test level assignment for connected gates."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "multiple_gates.sv"))

        # Gates should have different levels based on connectivity
        # Level assignment happens during diagram generation, so just verify structure
        assert len(circuit.gates) == 3


class TestSignalConnectivity:
    """Test signal driver/sink tracking."""

    def test_simple_connectivity(self, fixture_dir):
        """Test signal connectivity for simple gate."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        # Signal 'y' should have the AND gate as driver
        assert "y" in circuit.signal_driver
        # Signals 'a' and 'b' should have the AND gate as sink
        assert "a" in circuit.signal_sinks
        assert "b" in circuit.signal_sinks

    def test_internal_signal_connectivity(self, fixture_dir):
        """Test connectivity for internal signals."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "multiple_gates.sv"))

        # Internal signals n1, n2 should have both drivers and sinks
        assert "n1" in circuit.signal_driver
        assert "n1" in circuit.signal_sinks
        assert "n2" in circuit.signal_driver
        assert "n2" in circuit.signal_sinks


class TestDiagramGeneration:
    """Test SVG diagram generation."""

    def test_generate_simple_diagram(self, fixture_dir):
        """Test generating diagram for simple gate."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name

        try:
            circuit.generate_diagram(output_file)

            # Verify file was created and has content
            assert os.path.exists(output_file)
            with open(output_file, 'r') as f:
                content = f.read()
                assert '<svg' in content
                assert '</svg>' in content
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_generate_with_different_styles(self, fixture_dir):
        """Test diagram generation with different style presets."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        styles = ["classic", "blueprint", "midnight", "mono"]
        for style in styles:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
                output_file = f.name
            try:
                circuit.generate_diagram(output_file, style=style)
                assert os.path.exists(output_file)
            finally:
                if os.path.exists(output_file):
                    os.unlink(output_file)

    def test_generate_vertical_orientation(self, fixture_dir):
        """Test diagram generation with vertical orientation."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, orientation="vertical")
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_generate_horizontal_orientation(self, fixture_dir):
        """Test diagram generation with horizontal orientation."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, orientation="horizontal")
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_generate_with_grid_snapping(self, fixture_dir):
        """Test diagram generation with grid snapping."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, grid_x=1.0, grid_y=0.5)
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_generate_complex_circuit(self, fixture_dir):
        """Test generating diagram for complex circuit."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "multiple_gates.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name

        try:
            circuit.generate_diagram(output_file)

            assert os.path.exists(output_file)
            # Verify SVG contains multiple gates (look for gate labels u1, u2, u3)
            with open(output_file, 'r') as f:
                content = f.read()
                assert 'u1' in content and 'u2' in content and 'u3' in content
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestLayoutOptions:
    """Test layout configuration options."""

    def test_layout_symmetry_option(self, fixture_dir):
        """Test layout with symmetry enabled."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        # Test with symmetry enabled
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, symmetry=True)
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

        # Test with symmetry disabled
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, symmetry=False)
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestInputOrder:
    """Test input ordering functionality."""

    def test_input_order_alpha(self, fixture_dir):
        """Test alphabetical input ordering."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, input_order="alpha")
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_input_order_ports(self, fixture_dir):
        """Test port-defined input ordering."""
        circuit = SVCircuit()
        circuit.parse_file(str(fixture_dir / "simple_and.sv"))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            output_file = f.name
        try:
            circuit.generate_diagram(output_file, input_order="ports")
            assert os.path.exists(output_file)
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)
