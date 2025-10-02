"""Tests for CLI interface."""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from sv2svg.cli import main


@pytest.fixture
def fixture_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_output():
    """Create a temporary output file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
        output_file = f.name
    yield output_file
    # Cleanup
    if os.path.exists(output_file):
        os.unlink(output_file)


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_flag(self, capsys):
        """Test --version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(['--version'])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        # Version output contains the version number
        assert '0.' in captured.out or '1.' in captured.out

    def test_help_flag(self, capsys):
        """Test --help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(['--help'])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert 'SystemVerilog' in captured.out or 'Schemdraw' in captured.out

    def test_no_arguments(self):
        """Test CLI with no arguments (should fail)."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code != 0

    def test_nonexistent_input_file(self, temp_output):
        """Test with nonexistent input file."""
        result = main(['nonexistent.sv', '-o', temp_output])
        assert result == 1  # Should return error code


class TestCLIFileOperations:
    """Test file input/output operations."""

    def test_simple_conversion(self, fixture_dir, temp_output):
        """Test simple file conversion."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output])

        assert result == 0
        assert os.path.exists(temp_output)
        with open(temp_output, 'r') as f:
            content = f.read()
            assert '<svg' in content
            assert '</svg>' in content

    def test_default_output_filename(self, fixture_dir):
        """Test default output filename generation."""
        input_file = str(fixture_dir / "simple_and.sv")
        expected_output = str(fixture_dir / "simple_and_schemdraw.svg")

        try:
            result = main([input_file])
            assert result == 0
            assert os.path.exists(expected_output)
        finally:
            if os.path.exists(expected_output):
                os.unlink(expected_output)

    def test_stdout_output(self, fixture_dir, capsys):
        """Test output to stdout."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', '-'])

        assert result == 0
        captured = capsys.readouterr()
        assert '<svg' in captured.out
        assert '</svg>' in captured.out

    def test_stdout_no_file_created(self, fixture_dir, capsys):
        """Test that -o - does not create a file named '-'."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = str(fixture_dir / "simple_and.sv")
            # Run from temp directory to check if any file is created
            original_dir = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = main([input_file, '-o', '-'])
                assert result == 0
                # Verify no '-' file was created
                assert not os.path.exists('-')
                assert not os.path.exists(' -')
            finally:
                os.chdir(original_dir)


class TestCLIOptions:
    """Test CLI option handling."""

    def test_style_option(self, fixture_dir, temp_output):
        """Test --style option."""
        input_file = str(fixture_dir / "simple_and.sv")

        for style in ['classic', 'blueprint', 'midnight', 'mono']:
            result = main([input_file, '-o', temp_output, '--style', style])
            assert result == 0
            assert os.path.exists(temp_output)

    def test_orientation_horizontal(self, fixture_dir, temp_output):
        """Test horizontal orientation."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--orientation', 'horizontal'])
        assert result == 0

    def test_orientation_vertical(self, fixture_dir, temp_output):
        """Test vertical orientation."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--orientation', 'vertical'])
        assert result == 0

    def test_grid_options(self, fixture_dir, temp_output):
        """Test grid snapping options."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([
            input_file,
            '-o', temp_output,
            '--grid-x', '1.0',
            '--grid-y', '0.5'
        ])
        assert result == 0

    def test_no_grid_snapping(self, fixture_dir, temp_output):
        """Test disabling grid snapping."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([
            input_file,
            '-o', temp_output,
            '--grid-x', '0',
            '--grid-y', '0'
        ])
        assert result == 0

    def test_input_order_alpha(self, fixture_dir, temp_output):
        """Test alphabetical input ordering."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--input-order', 'alpha'])
        assert result == 0

    def test_input_order_ports(self, fixture_dir, temp_output):
        """Test port-defined input ordering."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--input-order', 'ports'])
        assert result == 0

    def test_input_order_auto(self, fixture_dir, temp_output):
        """Test auto input ordering."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--input-order', 'auto'])
        assert result == 0

    def test_no_symmetry_flag(self, fixture_dir, temp_output):
        """Test --no-symmetry flag."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([input_file, '-o', temp_output, '--no-symmetry'])
        assert result == 0


class TestCLIComplexCircuits:
    """Test CLI with more complex circuits."""

    def test_multiple_gates_circuit(self, fixture_dir, temp_output):
        """Test conversion of circuit with multiple gates."""
        input_file = str(fixture_dir / "multiple_gates.sv")
        result = main([input_file, '-o', temp_output])
        assert result == 0
        assert os.path.exists(temp_output)

    def test_all_gate_types_circuit(self, fixture_dir, temp_output):
        """Test conversion of circuit with all gate types."""
        input_file = str(fixture_dir / "all_gate_types.sv")
        result = main([input_file, '-o', temp_output])
        assert result == 0

    def test_assign_statements(self, fixture_dir, temp_output):
        """Test conversion of circuits with assign statements."""
        for fixture in ['assign_and.sv', 'assign_or.sv', 'assign_not.sv']:
            input_file = str(fixture_dir / fixture)
            result = main([input_file, '-o', temp_output])
            assert result == 0


class TestCLIOptionCombinations:
    """Test combinations of CLI options."""

    def test_style_and_orientation(self, fixture_dir, temp_output):
        """Test style and orientation together."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([
            input_file,
            '-o', temp_output,
            '--style', 'blueprint',
            '--orientation', 'vertical'
        ])
        assert result == 0

    def test_all_options_combined(self, fixture_dir, temp_output):
        """Test multiple options together."""
        input_file = str(fixture_dir / "simple_and.sv")
        result = main([
            input_file,
            '-o', temp_output,
            '--style', 'mono',
            '--orientation', 'horizontal',
            '--grid-x', '1.0',
            '--grid-y', '1.0',
            '--input-order', 'alpha',
            '--no-symmetry'
        ])
        assert result == 0
