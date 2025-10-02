"""Unit tests for SystemVerilog parser components."""

import pytest
from sv2svg.core import (
    ExpressionTokenizer,
    ExpressionParser,
    ASTtoGatesConverter,
    TokenType,
    IdentifierNode,
    UnaryOpNode,
    BinaryOpNode,
    Gate,
)


class TestExpressionTokenizer:
    """Test the expression tokenizer."""

    def test_simple_and(self):
        tokenizer = ExpressionTokenizer("a & b")
        tokens = tokenizer.tokenize()
        # Tokenizer adds EOF at end
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "a"
        assert tokens[1].type == TokenType.AND
        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "b"
        assert tokens[-1].type == TokenType.EOF

    def test_simple_or(self):
        tokenizer = ExpressionTokenizer("a | b")
        tokens = tokenizer.tokenize()
        assert tokens[1].type == TokenType.OR
        assert tokens[-1].type == TokenType.EOF

    def test_simple_xor(self):
        tokenizer = ExpressionTokenizer("a ^ b")
        tokens = tokenizer.tokenize()
        assert tokens[1].type == TokenType.XOR
        assert tokens[-1].type == TokenType.EOF

    def test_not_operation(self):
        tokenizer = ExpressionTokenizer("~a")
        tokens = tokenizer.tokenize()
        assert tokens[0].type == TokenType.NOT
        assert tokens[1].type == TokenType.IDENTIFIER
        assert tokens[-1].type == TokenType.EOF

    def test_parentheses(self):
        tokenizer = ExpressionTokenizer("(a & b)")
        tokens = tokenizer.tokenize()
        assert tokens[0].type == TokenType.LPAREN
        assert tokens[4].type == TokenType.RPAREN
        assert tokens[-1].type == TokenType.EOF

    def test_complex_expression(self):
        tokenizer = ExpressionTokenizer("a & b | c")
        tokens = tokenizer.tokenize()
        # Should have: a, &, b, |, c, EOF
        assert tokens[0].value == "a"
        assert tokens[1].type == TokenType.AND
        assert tokens[2].value == "b"
        assert tokens[3].type == TokenType.OR
        assert tokens[4].value == "c"
        assert tokens[-1].type == TokenType.EOF

    def test_whitespace_handling(self):
        tokenizer = ExpressionTokenizer("  a  &  b  ")
        tokens = tokenizer.tokenize()
        # Should have: a, &, b, EOF
        assert tokens[0].value == "a"
        assert tokens[1].type == TokenType.AND
        assert tokens[2].value == "b"
        assert tokens[-1].type == TokenType.EOF

    def test_nested_parentheses(self):
        tokenizer = ExpressionTokenizer("(a & (b | c))")
        tokens = tokenizer.tokenize()
        assert tokens[0].type == TokenType.LPAREN
        # tokens: (, a, &, (, b, |, c, ), ), EOF
        # Find second LPAREN
        lparen_count = 0
        for i, tok in enumerate(tokens):
            if tok.type == TokenType.LPAREN:
                lparen_count += 1
                if lparen_count == 2:
                    assert i == 3  # Second LPAREN is at index 3
                    break


class TestExpressionParser:
    """Test the expression parser."""

    def test_simple_identifier(self):
        tokenizer = ExpressionTokenizer("a")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, IdentifierNode)
        assert ast.name == "a"

    def test_simple_and(self):
        tokenizer = ExpressionTokenizer("a & b")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == "&"
        assert isinstance(ast.left, IdentifierNode)
        assert isinstance(ast.right, IdentifierNode)

    def test_simple_or(self):
        tokenizer = ExpressionTokenizer("a | b")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == "|"

    def test_simple_not(self):
        tokenizer = ExpressionTokenizer("~a")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, UnaryOpNode)
        assert ast.op == "~"
        assert isinstance(ast.operand, IdentifierNode)

    def test_nand_pattern(self):
        """Test ~(a & b) which should be recognized as NAND pattern."""
        tokenizer = ExpressionTokenizer("~(a & b)")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, UnaryOpNode)
        assert isinstance(ast.operand, BinaryOpNode)
        assert ast.operand.op == "&"

    def test_nor_pattern(self):
        """Test ~(a | b) which should be recognized as NOR pattern."""
        tokenizer = ExpressionTokenizer("~(a | b)")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        assert isinstance(ast, UnaryOpNode)
        assert isinstance(ast.operand, BinaryOpNode)
        assert ast.operand.op == "|"

    def test_operator_precedence(self):
        """Test that AND has higher precedence than OR."""
        tokenizer = ExpressionTokenizer("a | b & c")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        # Should parse as: a | (b & c)
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == "|"
        assert isinstance(ast.left, IdentifierNode)
        assert isinstance(ast.right, BinaryOpNode)
        assert ast.right.op == "&"

    def test_parentheses_override_precedence(self):
        """Test that parentheses override precedence."""
        tokenizer = ExpressionTokenizer("(a | b) & c")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        # Should parse as: (a | b) & c
        assert isinstance(ast, BinaryOpNode)
        assert ast.op == "&"
        assert isinstance(ast.left, BinaryOpNode)
        assert ast.left.op == "|"

    def test_multi_input_and(self):
        """Test a & b & c (multiple ANDs)."""
        tokenizer = ExpressionTokenizer("a & b & c")
        tokens = tokenizer.tokenize()
        parser = ExpressionParser(tokens)
        ast = parser.parse()
        # Should create nested binary nodes
        assert isinstance(ast, BinaryOpNode)


class TestASTtoGatesConverter:
    """Test AST to gates conversion."""

    def test_simple_identifier(self):
        """Test that a simple identifier doesn't create gates."""
        ast = IdentifierNode("a")
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert output_sig == "a"
        assert len(converter.gates) == 0

    def test_simple_and(self):
        """Test simple AND gate creation."""
        ast = BinaryOpNode("&", IdentifierNode("a"), IdentifierNode("b"))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert output_sig == "y"
        assert len(converter.gates) == 1
        gate = converter.gates[0]
        assert gate.type == "AND"
        assert gate.inputs == ["a", "b"]
        assert gate.output == "y"

    def test_simple_or(self):
        """Test simple OR gate creation."""
        ast = BinaryOpNode("|", IdentifierNode("a"), IdentifierNode("b"))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert len(converter.gates) == 1
        assert converter.gates[0].type == "OR"

    def test_simple_not(self):
        """Test simple NOT gate creation."""
        ast = UnaryOpNode("~", IdentifierNode("a"))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert len(converter.gates) == 1
        gate = converter.gates[0]
        assert gate.type == "NOT"
        assert gate.inputs == ["a"]
        assert gate.output == "y"

    def test_nand_pattern(self):
        """Test NAND pattern: ~(a & b)."""
        ast = UnaryOpNode("~", BinaryOpNode("&", IdentifierNode("a"), IdentifierNode("b")))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert len(converter.gates) == 1
        gate = converter.gates[0]
        assert gate.type == "NAND"
        assert gate.inputs == ["a", "b"]
        assert gate.output == "y"

    def test_nor_pattern(self):
        """Test NOR pattern: ~(a | b)."""
        ast = UnaryOpNode("~", BinaryOpNode("|", IdentifierNode("a"), IdentifierNode("b")))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert len(converter.gates) == 1
        assert converter.gates[0].type == "NOR"

    def test_xnor_pattern(self):
        """Test XNOR pattern: ~(a ^ b)."""
        ast = UnaryOpNode("~", BinaryOpNode("^", IdentifierNode("a"), IdentifierNode("b")))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        assert len(converter.gates) == 1
        assert converter.gates[0].type == "XNOR"

    def test_complex_expression(self):
        """Test complex expression: a & b & c creates intermediate signals."""
        # a & b & c parses as (a & b) & c
        inner_and = BinaryOpNode("&", IdentifierNode("a"), IdentifierNode("b"))
        ast = BinaryOpNode("&", inner_and, IdentifierNode("c"))
        converter = ASTtoGatesConverter("y", [])
        output_sig = converter.convert(ast)
        # Should create 2 AND gates with intermediate signal
        assert len(converter.gates) == 2
        assert all(g.type == "AND" for g in converter.gates)
        # Second gate should output to y
        assert converter.gates[1].output == "y"

    def test_gate_naming(self):
        """Test unique gate name generation."""
        existing_gates = [Gate("g1", "AND", ["a", "b"], "x", 0)]
        ast = BinaryOpNode("&", IdentifierNode("c"), IdentifierNode("d"))
        converter = ASTtoGatesConverter("y", existing_gates)
        converter.convert(ast)
        # Should generate auto_and_2 (since there's already 1 AND gate)
        assert "and" in converter.gates[0].name.lower()

    def test_intermediate_signal_naming(self):
        """Test intermediate signal name generation."""
        inner_and = BinaryOpNode("&", IdentifierNode("a"), IdentifierNode("b"))
        ast = BinaryOpNode("&", inner_and, IdentifierNode("c"))
        converter = ASTtoGatesConverter("y", [])
        converter.convert(ast)
        # First gate should output to intermediate signal
        first_output = converter.gates[0].output
        assert first_output.startswith("_expr_")
        assert first_output in converter.internal_signals
