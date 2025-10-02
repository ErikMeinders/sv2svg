# Testing Guide

## Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=sv2svg --cov-report=html
```

## Test Structure

### Test Files

- **`tests/test_parser.py`** - Unit tests for expression tokenization, parsing, and AST to gates conversion
- **`tests/test_circuit.py`** - Integration tests for SVCircuit parsing, level assignment, and diagram generation
- **`tests/test_cli.py`** - CLI interface tests covering all command-line options

### Test Fixtures

Test fixtures are located in `tests/fixtures/`:

- `simple_and.sv` - Single AND gate
- `multiple_gates.sv` - Connected gates (AND, OR, NOT)
- `assign_and.sv`, `assign_or.sv`, `assign_not.sv` - Assign statement tests
- `all_gate_types.sv` - All supported gate types
- `empty_module.sv` - Empty module for error testing

## Test Coverage

**70 tests** covering:

### Parser Tests (22 tests)
- Expression tokenization (8 tests)
- Expression parsing with operator precedence (9 tests)
- AST to gates conversion (10 tests)

### Circuit Tests (21 tests)
- Module parsing (8 tests)
- Level assignment (2 tests)
- Signal connectivity (2 tests)
- Diagram generation (6 tests)
- Layout options (2 tests)
- Input ordering (2 tests)

### CLI Tests (27 tests)
- Basic CLI functionality (4 tests)
- File operations (4 tests)
- CLI options (8 tests)
- Complex circuits (3 tests)
- Option combinations (2 tests)

## CI Integration

Tests run automatically on:
- Push to `main` branch
- Pull requests

See `.github/workflows/ci.yml` for CI configuration.

## Adding New Tests

1. Create test fixtures in `tests/fixtures/` if needed
2. Add test functions following the pattern:
   - Use descriptive test names: `test_<feature>_<scenario>`
   - Group related tests in classes: `TestFeatureName`
   - Use pytest fixtures for common setup
3. Run tests locally before committing
