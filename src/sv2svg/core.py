# Ported from project sv2schemdraw.py (single-file) to reusable module
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import schemdraw
import schemdraw.elements as elm
import schemdraw.logic as logic

from .layout import LayoutEngine, LayoutConfig


@dataclass
class Gate:
    name: str
    type: str
    inputs: List[str]
    output: str
    level: int = 0


# Expression Parser for complex assign statements
class TokenType(Enum):
    """Token types for expression parsing."""
    IDENTIFIER = 'IDENTIFIER'
    AND = 'AND'
    OR = 'OR'
    XOR = 'XOR'
    NOT = 'NOT'
    LPAREN = 'LPAREN'
    RPAREN = 'RPAREN'
    EOF = 'EOF'


@dataclass
class Token:
    """Token for expression parsing."""
    type: TokenType
    value: str


class ExprNode:
    """Base class for expression AST nodes."""
    pass


@dataclass
class IdentifierNode(ExprNode):
    """Leaf node representing a signal identifier."""
    name: str


@dataclass
class UnaryOpNode(ExprNode):
    """Unary operation node (NOT)."""
    op: str  # '~'
    operand: ExprNode


@dataclass
class BinaryOpNode(ExprNode):
    """Binary operation node (AND, OR, XOR)."""
    op: str  # '&', '|', '^'
    left: ExprNode
    right: ExprNode


class ExpressionTokenizer:
    """Tokenizer for SystemVerilog expressions."""

    def __init__(self, expr: str):
        self.expr = expr.strip()
        self.pos = 0

    def tokenize(self) -> List[Token]:
        """Tokenize the expression."""
        tokens = []
        while self.pos < len(self.expr):
            ch = self.expr[self.pos]

            # Skip whitespace
            if ch.isspace():
                self.pos += 1
                continue

            # Operators and parentheses
            if ch == '&':
                tokens.append(Token(TokenType.AND, '&'))
                self.pos += 1
            elif ch == '|':
                tokens.append(Token(TokenType.OR, '|'))
                self.pos += 1
            elif ch == '^':
                tokens.append(Token(TokenType.XOR, '^'))
                self.pos += 1
            elif ch == '~':
                tokens.append(Token(TokenType.NOT, '~'))
                self.pos += 1
            elif ch == '(':
                tokens.append(Token(TokenType.LPAREN, '('))
                self.pos += 1
            elif ch == ')':
                tokens.append(Token(TokenType.RPAREN, ')'))
                self.pos += 1
            # Identifiers
            elif ch.isalpha() or ch == '_':
                start = self.pos
                while self.pos < len(self.expr) and (self.expr[self.pos].isalnum() or self.expr[self.pos] == '_'):
                    self.pos += 1
                tokens.append(Token(TokenType.IDENTIFIER, self.expr[start:self.pos]))
            else:
                # Unknown character - skip it
                self.pos += 1

        tokens.append(Token(TokenType.EOF, ''))
        return tokens


class ExpressionParser:
    """Recursive descent parser for SystemVerilog expressions.

    Grammar (with precedence):
        expr     -> xor_expr
        xor_expr -> or_expr ('^' or_expr)*
        or_expr  -> and_expr ('|' and_expr)*
        and_expr -> unary ('&' unary)*
        unary    -> '~' unary | primary
        primary  -> IDENTIFIER | '(' expr ')'

    Precedence (highest to lowest):
        1. Parentheses ()
        2. NOT (~)
        3. AND (&)
        4. OR (|), XOR (^)
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        """Get current token."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TokenType.EOF, '')

    def advance(self):
        """Move to next token."""
        if self.pos < len(self.tokens):
            self.pos += 1

    def parse(self) -> ExprNode:
        """Parse the expression."""
        return self.expr()

    def expr(self) -> ExprNode:
        """Parse expression: xor_expr"""
        return self.xor_expr()

    def xor_expr(self) -> ExprNode:
        """Parse XOR expression: or_expr ('^' or_expr)*"""
        left = self.or_expr()
        while self.current_token().type == TokenType.XOR:
            self.advance()
            right = self.or_expr()
            left = BinaryOpNode('^', left, right)
        return left

    def or_expr(self) -> ExprNode:
        """Parse OR expression: and_expr ('|' and_expr)*"""
        left = self.and_expr()
        while self.current_token().type == TokenType.OR:
            self.advance()
            right = self.and_expr()
            left = BinaryOpNode('|', left, right)
        return left

    def and_expr(self) -> ExprNode:
        """Parse AND expression: unary ('&' unary)*"""
        left = self.unary()
        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.unary()
            left = BinaryOpNode('&', left, right)
        return left

    def unary(self) -> ExprNode:
        """Parse unary expression: '~' unary | primary"""
        if self.current_token().type == TokenType.NOT:
            self.advance()
            operand = self.unary()
            return UnaryOpNode('~', operand)
        return self.primary()

    def primary(self) -> ExprNode:
        """Parse primary expression: IDENTIFIER | '(' expr ')'"""
        token = self.current_token()

        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return IdentifierNode(token.value)

        if token.type == TokenType.LPAREN:
            self.advance()
            node = self.expr()
            if self.current_token().type == TokenType.RPAREN:
                self.advance()
            return node

        # Error case - return dummy identifier
        return IdentifierNode('error')


class ASTtoGatesConverter:
    """Converts expression AST to Gate objects with intermediate signals."""

    def __init__(self, output_signal: str, existing_gates: List[Gate]):
        self.output_signal = output_signal
        self.existing_gates = existing_gates
        self.gates: List[Gate] = []
        self.signal_counter = 0
        self.internal_signals: Set[str] = set()

    def _get_unique_signal_name(self, prefix: str) -> str:
        """Generate a unique intermediate signal name."""
        self.signal_counter += 1
        name = f"_expr_{prefix}_{self.signal_counter}"
        self.internal_signals.add(name)
        return name

    def _get_gate_name(self, gate_type: str) -> str:
        """Generate a unique gate name."""
        existing_count = len([g for g in self.existing_gates + self.gates if g.type == gate_type])
        return f"auto_{gate_type.lower()}_{existing_count + 1}"

    def convert(self, node: ExprNode, is_root: bool = True) -> str:
        """Convert AST node to gates, returning the output signal name.

        Args:
            node: The AST node to convert
            is_root: True if this is the root node (output should use target signal)

        Returns:
            The signal name that holds the result of this node
        """
        if isinstance(node, IdentifierNode):
            return node.name

        elif isinstance(node, UnaryOpNode):
            # Check for NAND, NOR, XNOR patterns: ~(a op b)
            if isinstance(node.operand, BinaryOpNode):
                # This is a pattern like ~(a & b) -> NAND
                binary_node = node.operand
                left_sig = self.convert(binary_node.left, is_root=False)
                right_sig = self.convert(binary_node.right, is_root=False)
                output_sig = self.output_signal if is_root else self._get_unique_signal_name('n' + binary_node.op.replace('&', 'and').replace('|', 'or').replace('^', 'xor'))

                # Map operator to negated gate type
                gate_type_map = {'&': 'NAND', '|': 'NOR', '^': 'XNOR'}
                gate_type = gate_type_map.get(binary_node.op, 'NAND')

                gate = Gate(
                    name=self._get_gate_name(gate_type),
                    type=gate_type,
                    inputs=[left_sig, right_sig],
                    output=output_sig
                )
                self.gates.append(gate)
                return output_sig
            else:
                # Regular NOT operation
                input_sig = self.convert(node.operand, is_root=False)
                output_sig = self.output_signal if is_root else self._get_unique_signal_name('not')
                gate = Gate(
                    name=self._get_gate_name('NOT'),
                    type='NOT',
                    inputs=[input_sig],
                    output=output_sig
                )
                self.gates.append(gate)
                return output_sig

        elif isinstance(node, BinaryOpNode):
            # Binary operation (AND, OR, XOR)
            left_sig = self.convert(node.left, is_root=False)
            right_sig = self.convert(node.right, is_root=False)
            output_sig = self.output_signal if is_root else self._get_unique_signal_name(node.op.replace('&', 'and').replace('|', 'or').replace('^', 'xor'))

            # Map operator to gate type
            gate_type_map = {'&': 'AND', '|': 'OR', '^': 'XOR'}
            gate_type = gate_type_map.get(node.op, 'AND')

            gate = Gate(
                name=self._get_gate_name(gate_type),
                type=gate_type,
                inputs=[left_sig, right_sig],
                output=output_sig
            )
            self.gates.append(gate)
            return output_sig

        return 'error'


STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "classic": {
        "config": {"color": "#2c3e50", "lw": 1.1, "fontsize": 10},
        "module_label_color": "#1f618d",
        "gate_label_fontsize": 9,
    },
    "blueprint": {
        "config": {"color": "#0b3d91", "lw": 1.25, "fontsize": 10},
        "module_label_color": "#0b3d91",
        "gate_label_fontsize": 9,
    },
    "midnight": {
        "config": {"color": "#00bcd4", "lw": 1.2, "fontsize": 10},
        "module_label_color": "#00bcd4",
        "gate_label_fontsize": 9,
    },
    "mono": {
        "config": {"color": "#2d3436", "lw": 1.0, "fontsize": 10},
        "module_label_color": "#2d3436",
        "gate_label_fontsize": 9,
    },
    "vibrant": {
        "config": {"color": "#34495e", "lw": 1.2, "fontsize": 10},
        "module_label_color": "#2980b9",
        "gate_label_fontsize": 9,
        "gate_fills": {
            "AND": "#e74c3c",
            "NAND": "#e74c3c",
            "OR": "#3498db",
            "NOR": "#3498db",
            "XOR": "#f39c12",
            "XNOR": "#f39c12",
            "NOT": "#9b59b6",
            "BUF": "#1abc9c",
        },
    },
    "dark": {
        "config": {"color": "#ecf0f1", "lw": 1.2, "fontsize": 10},
        "module_label_color": "#3498db",
        "gate_label_fontsize": 9,
        "background": "#2c3e50",
    },
}


def available_styles() -> List[str]:
    """List of supported color/style presets."""
    return list(STYLE_PRESETS.keys())


def _parse_length(value: Optional[str], fallback: float) -> Tuple[float, str]:
    if value is None:
        return fallback, ''
    s = value.strip()
    units = ['pt', 'px', 'cm', 'mm', 'in']
    for unit in units:
        if s.endswith(unit):
            try:
                return float(s[:-len(unit)]), unit
            except ValueError:
                break
    try:
        return float(s), ''
    except ValueError:
        return fallback, ''


def _rotate_svg_clockwise(svg_text: str, bbox) -> str:
    svg_ns = 'http://www.w3.org/2000/svg'
    xlink_ns = 'http://www.w3.org/1999/xlink'
    ET.register_namespace('', svg_ns)
    ET.register_namespace('xlink', xlink_ns)

    root = ET.fromstring(svg_text)

    width_val, width_unit = _parse_length(root.get('width'), bbox.xmax - bbox.xmin)
    height_val, height_unit = _parse_length(root.get('height'), bbox.ymax - bbox.ymin)

    vb_attr = root.get('viewBox')
    if vb_attr:
        try:
            min_x, min_y, vb_width, vb_height = [float(part) for part in vb_attr.strip().split()[:4]]
        except ValueError:
            min_x = bbox.xmin
            min_y = bbox.ymin
            vb_width = bbox.xmax - bbox.xmin
            vb_height = bbox.ymax - bbox.ymin
    else:
        min_x = bbox.xmin
        min_y = bbox.ymin
        vb_width = bbox.xmax - bbox.xmin
        vb_height = bbox.ymax - bbox.ymin

    children = list(root)
    for child in children:
        root.remove(child)

    transform = (
        f"translate(0 {vb_width}) "
        f"rotate(-90) "
        f"translate({-min_x} {-min_y})"
    )

    group = ET.Element(f'{{{svg_ns}}}g', {'transform': transform})
    for child in children:
        group.append(child)
    root.append(group)

    if height_val is not None:
        unit = height_unit
        root.set('width', f"{height_val}{unit}" if unit else f"{height_val}")
    if width_val is not None:
        unit = width_unit
        root.set('height', f"{width_val}{unit}" if unit else f"{width_val}")

    root.set('viewBox', f"0 0 {vb_height} {vb_width}")

    return ET.tostring(root, encoding='unicode')


class SVCircuit:
    def __init__(self):
        self.module_name: str = ""
        self.port_order: List[str] = []
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.internal_signals: Set[str] = set()
        self.gates: List[Gate] = []
        self.signal_driver: Dict[str, str] = {}
        self.signal_sinks: Dict[str, List[str]] = {}
        self.layout_engine: Optional[LayoutEngine] = None

    def parse_file(self, filename: str) -> None:
        with open(filename, 'r') as f:
            content = f.read()

        content = re.sub(r"//.*", "", content)
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        m = re.search(r"module\s+(\w+)\s*\((.*?)\)\s*;", content, re.DOTALL)
        if not m:
            raise ValueError("Could not find module definition")
        self.module_name = m.group(1)
        raw_ports = m.group(2)
        self.port_order = [p.strip() for p in raw_ports.split(',') if p.strip()]

        for decl, target in (("input", self.inputs), ("output", self.outputs)):
            for match in re.findall(rf"{decl}\s+(?:wire|logic)?\s*([^;]+);", content):
                names = [x.strip() for x in match.split(',') if x.strip()]
                target.extend(names)

        for match in re.findall(r"logic\s+([^;]+);", content):
            names = [x.strip() for x in match.split(',') if x.strip()]
            self.internal_signals.update(names)

        for gate_type, gate_name, ports in re.findall(r"(\w+)\s+(\w+)\s*\(([^)]*)\)\s*;", content):
            if gate_type == "module":
                continue
            conns = [p.strip() for p in ports.split(',') if p.strip()]
            if len(conns) < 1:
                continue
            inputs = conns[:-1]
            output = conns[-1]
            self.gates.append(Gate(name=gate_name, type=gate_type.upper(), inputs=inputs, output=output))

        # Parse assign statements using expression parser
        # This supports complex expressions with operator precedence and parentheses:
        # - Simple: y = a & b
        # - Complex: y = a | b & c (AND has higher precedence)
        # - Parentheses: y = (a | b) & c
        # - Multi-operator: y = a & b | c & d
        # - Negation: y = ~(a & b | c)

        for match in re.findall(r"assign\s+(\w+)\s*=\s*([^;]+);", content):
            output_sig = match[0].strip()
            expr_str = match[1].strip()

            # Skip if this output is already driven by an explicit gate
            if any(g.output == output_sig for g in self.gates):
                continue

            try:
                # Tokenize and parse the expression
                tokenizer = ExpressionTokenizer(expr_str)
                tokens = tokenizer.tokenize()
                parser = ExpressionParser(tokens)
                ast = parser.parse()

                # Convert AST to gates
                converter = ASTtoGatesConverter(output_sig, self.gates)
                converter.convert(ast, is_root=True)

                # Add generated gates and internal signals
                self.gates.extend(converter.gates)
                self.internal_signals.update(converter.internal_signals)
            except Exception:
                # If parsing fails, skip this assign statement
                # (could be an unsupported construct)
                pass

        self._build_connectivity()
        self._setup_layout_engine()

    def _build_connectivity(self) -> None:
        self.signal_driver = {}
        self.signal_sinks = {}
        for s in self.inputs:
            self.signal_driver[s] = f"IN:{s}"
        for g in self.gates:
            self.signal_driver[g.output] = g.name
            for s in g.inputs:
                self.signal_sinks.setdefault(s, []).append(g.name)
        for s in self.outputs:
            self.signal_sinks.setdefault(s, [])

    def _setup_layout_engine(self) -> None:
        """Setup the layout engine with current circuit data."""
        config = LayoutConfig()
        self.layout_engine = LayoutEngine(config)

        # Add gates to layout engine
        for g in self.gates:
            self.layout_engine.add_gate(g.name, g.type, g.inputs, g.output)

        # Set connectivity
        self.layout_engine.set_connectivity(self.signal_driver, self.signal_sinks)

        # Assign levels and reorder
        self.layout_engine.assign_levels()
        self.layout_engine.reorder_by_barycenter(self.inputs)

        # Update original gates with level information
        for layout_gate in self.layout_engine.gates:
            original_gate = next((g for g in self.gates if g.name == layout_gate.name), None)
            if original_gate:
                original_gate.level = layout_gate.level

    def _get_levels(self) -> Dict[int, List[Gate]]:
        """Get gates organized by level using layout engine results."""
        if not self.layout_engine:
            return {}

        levels: Dict[int, List[Gate]] = {}
        for layout_gate in self.layout_engine.gates:
            original_gate = next((g for g in self.gates if g.name == layout_gate.name), None)
            if original_gate:
                levels.setdefault(original_gate.level, []).append(original_gate)

        return levels

    def _simulate_circuit(self, input_values: Dict[str, bool]) -> Dict[str, bool]:
        """Simulate circuit for given input values."""
        signal_values = dict(input_values)  # Start with input values

        # Gate logic functions
        gate_ops = {
            'AND': lambda inputs: all(inputs),
            'OR': lambda inputs: any(inputs),
            'NAND': lambda inputs: not all(inputs),
            'NOR': lambda inputs: not any(inputs),
            'XOR': lambda inputs: len([i for i in inputs if i]) % 2 == 1,
            'XNOR': lambda inputs: len([i for i in inputs if i]) % 2 == 0,
            'NOT': lambda inputs: not inputs[0],
            'INV': lambda inputs: not inputs[0],
            'BUF': lambda inputs: inputs[0],
            'BUFFER': lambda inputs: inputs[0],
        }

        # Evaluate gates in level order
        levels = self._get_levels()
        for level_num in sorted(levels.keys()):
            for gate in levels[level_num]:
                # Get input values for this gate
                input_vals = []
                for inp in gate.inputs:
                    if inp in signal_values:
                        input_vals.append(signal_values[inp])
                    else:
                        # Input not yet evaluated, skip for now
                        continue

                if len(input_vals) == len(gate.inputs):
                    # All inputs available, evaluate gate
                    gate_type = gate.type.upper()
                    if gate_type in gate_ops:
                        signal_values[gate.output] = gate_ops[gate_type](input_vals)

        return signal_values

    def _generate_truth_table(self) -> List[Dict[str, bool]]:
        """Generate truth table for the circuit."""
        if not self.inputs or not self.outputs:
            return []

        # Limit to 5 inputs max for reasonable table size
        if len(self.inputs) > 5:
            return []

        truth_table = []
        num_rows = 2 ** len(self.inputs)
        sorted_inputs = sorted(self.inputs)

        for i in range(num_rows):
            # Generate input combination
            input_values = {}
            for j, inp in enumerate(sorted_inputs):
                # Binary digit for this input
                input_values[inp] = bool((i >> (len(sorted_inputs) - 1 - j)) & 1)

            # Simulate circuit
            signal_values = self._simulate_circuit(input_values)

            # Create row with inputs and outputs
            row = {}
            for inp in sorted_inputs:
                row[inp] = input_values[inp]
            for out in sorted(self.outputs):
                row[out] = signal_values.get(out, False)

            truth_table.append(row)

        return truth_table

    def _execute_routing_commands(self, d: schemdraw.Drawing, commands: List[Dict[str, Any]],
                                bboxes: List[Dict[str, float]]) -> None:
        """Execute routing commands generated by the layout engine."""

        def hline_avoid(p1: Tuple[float, float], p2: Tuple[float, float], target_x: float):
            x1, y = p1
            x2, _ = p2
            if x2 < x1:
                x1, x2 = x2, x1
            collided = None
            for b in bboxes:
                if abs(b.get('right', 1e9) - target_x) < 0.3:
                    continue
                if b['left'] <= x2 and b['right'] >= x1:
                    if b['top'] <= y <= b['bottom']:
                        collided = b
                        break
            if not collided:
                d.add(elm.Line().at((x1, y)).to((x2, y)))
                return
            midy = (collided['top'] + collided['bottom']) / 2.0
            detour_y = collided['top'] - 0.4 if y <= midy else collided['bottom'] + 0.4
            d.add(elm.Line().at((x1, y)).to((x1, detour_y)))
            d.add(elm.Line().at((x1, detour_y)).to((x2, detour_y)))
            d.add(elm.Line().at((x2, detour_y)).to((x2, y)))

        def vline_avoid(p1: Tuple[float, float], p2: Tuple[float, float]):
            x, y1 = p1
            x2, y2 = p2
            if abs(x2 - x) > 1e-6:
                d.add(elm.Line().at(p1).to(p2))
                return
            if y2 < y1:
                y1, y2 = y2, y1
            collided = None
            for b in bboxes:
                if b['left'] <= x <= b['right'] and not (y2 < b['top'] or y1 > b['bottom']):
                    collided = b
                    break
            if not collided:
                d.add(elm.Line().at((x, y1)).to((x, y2)))
                return
            left_x = collided['left'] - 0.4
            right_x = collided['right'] + 0.4
            detour_x = left_x if (left_x > 0.2) else right_x
            hline_avoid((x, y1), (detour_x, y1), target_x=detour_x)
            d.add(elm.Line().at((detour_x, y1)).to((detour_x, y2)))
            hline_avoid((detour_x, y2), (x, y2), target_x=x)

        for cmd in commands:
            cmd_type = cmd.get('type')
            if cmd_type == 'line':
                d.add(elm.Line().at(cmd['from']).to(cmd['to']))
            elif cmd_type == 'line_avoid_h':
                hline_avoid(cmd['from'], cmd['to'], cmd.get('target_x', cmd['to'][0]))
            elif cmd_type == 'line_avoid_v':
                vline_avoid(cmd['from'], cmd['to'])
            elif cmd_type == 'dot':
                d.add(elm.Dot().at(cmd['at']))

    def generate_diagram(
        self,
        output_filename: Optional[str] = None,
        input_order: str = 'alpha',
        grid_x: float = 0.5,
        grid_y: float = 0.5,
        symmetry: bool = True,
        to_stdout: bool = False,
        style: str = 'classic',
        orientation: str = 'horizontal',
        show_table: bool = False,
        show_caption: bool = True,
        fill_gates: bool = False,
        signal_styles: bool = False,
        fanout_wires: bool = False,
        show_internal_labels: bool = True,
        show_all_labels: bool = True,
    ) -> Optional[str]:
        d = schemdraw.Drawing(unit=1.2)
        style_settings = STYLE_PRESETS.get(style, STYLE_PRESETS['classic'])
        config_kwargs = dict(style_settings.get('config', {}))
        if 'fontsize' not in config_kwargs:
            config_kwargs['fontsize'] = 10
        d.config(**config_kwargs)
        module_label_color = style_settings.get('module_label_color', '#1f618d')
        gate_label_fontsize = style_settings.get('gate_label_fontsize', 9)
        if show_caption:
            d.add(
                elm.Label()
                .label(f"Module: {self.module_name}")
                .at((0, -1))
                .color(module_label_color)
            )
        if orientation not in {'horizontal', 'vertical'}:
            orientation = 'horizontal'
        rotate_svg = (orientation == 'vertical')
        x_step = 4.0
        y_step = 2.2
        left_margin = 0.5

        def snap(val: float, step: float) -> float:
            if step and step > 0:
                return round(val / step) * step
            return val

        # Calculate signal fan-out (number of gates each signal drives)
        signal_fanout: Dict[str, int] = {}
        for g in self.gates:
            for input_sig in g.inputs:
                signal_fanout[input_sig] = signal_fanout.get(input_sig, 0) + 1

        # Determine if a signal is intermediate (declared as logic/wire)
        intermediate_signals = set()
        for g in self.gates:
            out_sig = g.output
            if out_sig not in self.inputs and out_sig not in self.outputs:
                intermediate_signals.add(out_sig)

        # Helper functions for line styling
        def get_line_style(signal: str) -> str:
            """Get line style based on signal type when signal_styles enabled"""
            if not signal_styles:
                return '-'  # solid (default)
            if signal in self.inputs or signal in self.outputs:
                return '-'  # solid for primary I/O
            elif signal in intermediate_signals:
                return '--'  # dashed for intermediate signals
            return '-'

        def get_line_width(signal: str) -> float:
            """Get line width based on fan-out when fanout_wires enabled"""
            if not fanout_wires:
                return None  # use default from style
            fanout = signal_fanout.get(signal, 0)
            if fanout == 0:
                return None  # use default
            elif fanout == 1:
                return 1.0  # thin for single load
            elif fanout == 2:
                return 1.3  # medium for dual load
            elif fanout <= 4:
                return 1.6  # thicker for moderate fan-out
            else:
                return 2.0  # thick for high fan-out

        input_y0 = 0.0
        sig_source_pt: Dict[str, Tuple[float, float]] = {}
        in_sink_info: Dict[str, List[Tuple[int, int, str]]] = {s: [] for s in self.inputs}
        for g in self.gates:
            for i, s in enumerate(g.inputs, start=1):
                if s in in_sink_info:
                    in_sink_info[s].append((g.level, i, g.name))

        ordered_inputs: List[str] = []
        if input_order == 'ports':
            ordered_inputs = [p for p in self.port_order if p in self.inputs]
            ordered_inputs += [s for s in sorted(self.inputs) if s not in ordered_inputs]
        elif input_order == 'auto':
            if self.port_order:
                ordered_inputs = [p for p in self.port_order if p in self.inputs]
                ordered_inputs += [s for s in sorted(self.inputs) if s not in ordered_inputs]
            else:
                ordered_inputs = sorted(self.inputs)
        else:
            ordered_inputs = sorted(self.inputs)

        n_inputs = len(ordered_inputs)
        for idx, name in enumerate(ordered_inputs):
            y = input_y0 + (n_inputs - 1 - idx) * y_step
            # Apply styling for input signal
            input_line_kwargs = {}
            input_ls = get_line_style(name)
            input_lw = get_line_width(name)
            if input_ls != '-':
                input_line_kwargs['ls'] = input_ls
            if input_lw is not None:
                input_line_kwargs['lw'] = input_lw
            d.add(elm.Line(**input_line_kwargs).at((left_margin, y)).to((left_margin + 0.8, y)).label(name, 'left'))
            src = (left_margin + 0.8, y)
            d.add(elm.Dot().at(src))
            sig_source_pt[name] = src

        max_level = max(g.level for g in self.gates) if self.gates else 0
        gate_elems: Dict[str, any] = {}
        level_y_bases: Dict[int, float] = {}
        min_y = input_y0  # Track minimum Y coordinate (most negative = bottom) for truth table positioning

        # Temporarily use existing gate layout until full integration is complete
        levels = self._get_levels()
        for lvl in sorted(levels.keys()):
            gates_at_level = levels[lvl]
            level_y_bases[lvl] = 0.0
            y_targets = []
            for g in gates_at_level:
                if g.inputs and all(s in sig_source_pt for s in g.inputs):
                    y = sum(sig_source_pt[s][1] for s in g.inputs) / len(g.inputs)
                else:
                    y = 0.0
                y_targets.append((g, y))

            if symmetry and gates_at_level:
                source_to_gates: Dict[str, List[Gate]] = {}
                for g in gates_at_level:
                    for s in g.inputs:
                        if s in sig_source_pt:
                            source_to_gates.setdefault(s, []).append(g)
                candidate_groups = {s: gl for s, gl in source_to_gates.items() if len(gl) >= 2}
                if candidate_groups:
                    g_assigned: Dict[str, str] = {}
                    for s, gl in sorted(candidate_groups.items(), key=lambda kv: -len(kv[1])):
                        for g in gl:
                            if g.name not in g_assigned:
                                g_assigned[g.name] = s
                    current_map: Dict[str, float] = {g.name: ty for (g, ty) in y_targets}
                    overrides: Dict[str, float] = {}
                    for s, gl in candidate_groups.items():
                        members = [g for g in gl if g_assigned.get(g.name) == s]
                        if len(members) < 2:
                            continue
                        try:
                            center_y = sig_source_pt[s][1]
                        except Exception:
                            continue
                        members_sorted = sorted(members, key=lambda gg: current_map.get(gg.name, 0.0))
                        m = len(members_sorted)
                        for i, gg in enumerate(members_sorted):
                            offset = (i - (m - 1) / 2.0) * y_step
                            overrides[gg.name] = center_y + offset
                    y_targets = [
                        (g, overrides.get(g.name, ty))
                        for (g, ty) in y_targets
                    ]
                    y_targets.sort(key=lambda t: (t[1], t[0].name))

            y_targets.sort(key=lambda t: (t[1], t[0].name))
            placed = []
            last_y = None
            for g, ty in y_targets:
                y = ty if last_y is None else max(ty, last_y + y_step)
                y = snap(y, grid_y)
                last_y = y
                min_y = min(min_y, y)  # Track minimum Y coordinate (most negative = bottom)
                x = left_margin + x_step * float(lvl)
                elem = self._add_gate(d, g, x, y, gate_label_fontsize, fill_gates, style_settings, show_internal_labels, show_all_labels)
                if hasattr(elem, 'out'):
                    out_pt = elem.out
                else:
                    out_pt = (x + 1.5, y)
                gate_elems[g.name] = elem
                sig_source_pt[g.output] = out_pt

        out_x = left_margin + x_step * (max_level + 1.1)
        output_anchor: Dict[str, Tuple[float, float]] = {}
        for idx, name in enumerate(sorted(self.outputs)):
            src = sig_source_pt.get(name)
            y = src[1] if src else (idx * y_step)
            min_y = min(min_y, y)  # Track minimum Y coordinate (most negative = bottom)
            # Apply styling for output signal
            output_line_kwargs = {}
            output_ls = get_line_style(name)
            output_lw = get_line_width(name)
            if output_ls != '-':
                output_line_kwargs['ls'] = output_ls
            if output_lw is not None:
                output_line_kwargs['lw'] = output_lw
            d.add(elm.Line(**output_line_kwargs).at((out_x - 0.8, y)).to((out_x, y)).label(name, 'right'))
            d.add(elm.Dot().at((out_x - 0.8, y)))
            output_anchor[name] = (out_x - 0.8, y)

        bboxes: List[Dict[str, float]] = []
        for gname, elem in gate_elems.items():
            try:
                ins = []
                for pin in ('in1', 'in2', 'in3', 'in4', 'in'):
                    if hasattr(elem, pin):
                        ins.append(getattr(elem, pin))
                if not ins:
                    continue
                xs = [pt[0] for pt in ins]
                ys = [pt[1] for pt in ins]
                left = min(xs) - 0.2
                top = min(ys) - 0.6
                bottom = max(ys) + 0.6
                right = getattr(elem, 'out', (min(xs) + 1.2, 0.0))[0] + 0.2
                bboxes.append({'name': gname, 'left': left, 'right': right, 'top': top, 'bottom': bottom})
            except Exception:
                continue

        def hline_avoid(p1: Tuple[float, float], p2: Tuple[float, float], target_x: float, signal: str = None):
            x1, y = p1
            x2, _ = p2
            if x2 < x1:
                x1, x2 = x2, x1
            collided = None
            for b in bboxes:
                if abs(b.get('right', 1e9) - target_x) < 0.3:
                    continue
                if b['left'] <= x2 and b['right'] >= x1:
                    if b['top'] <= y <= b['bottom']:
                        collided = b
                        break
            # Apply line styling based on signal
            line_kwargs = {}
            if signal:
                ls = get_line_style(signal)
                lw = get_line_width(signal)
                if ls != '-':
                    line_kwargs['ls'] = ls
                if lw is not None:
                    line_kwargs['lw'] = lw
            if not collided:
                d.add(elm.Line(**line_kwargs).at((x1, y)).to((x2, y)))
                return
            midy = (collided['top'] + collided['bottom']) / 2.0
            detour_y = collided['top'] - 0.4 if y <= midy else collided['bottom'] + 0.4
            d.add(elm.Line(**line_kwargs).at((x1, y)).to((x1, detour_y)))
            d.add(elm.Line(**line_kwargs).at((x1, detour_y)).to((x2, detour_y)))
            d.add(elm.Line(**line_kwargs).at((x2, detour_y)).to((x2, y)))

        def vline_avoid(p1: Tuple[float, float], p2: Tuple[float, float], signal: str = None):
            x, y1 = p1
            x2, y2 = p2
            # Apply line styling based on signal
            line_kwargs = {}
            if signal:
                ls = get_line_style(signal)
                lw = get_line_width(signal)
                if ls != '-':
                    line_kwargs['ls'] = ls
                if lw is not None:
                    line_kwargs['lw'] = lw
            if abs(x2 - x) > 1e-6:
                d.add(elm.Line(**line_kwargs).at(p1).to(p2))
                return
            if y2 < y1:
                y1, y2 = y2, y1
            collided = None
            for b in bboxes:
                if b['left'] <= x <= b['right'] and not (y2 < b['top'] or y1 > b['bottom']):
                    collided = b
                    break
            if not collided:
                d.add(elm.Line(**line_kwargs).at((x, y1)).to((x, y2)))
                return
            left_x = collided['left'] - 0.4
            right_x = collided['right'] + 0.4
            detour_x = left_x if (left_x > left_margin + 0.2) else right_x
            hline_avoid((x, y1), (detour_x, y1), target_x=detour_x, signal=signal)
            d.add(elm.Line(**line_kwargs).at((detour_x, y1)).to((detour_x, y2)))
            hline_avoid((detour_x, y2), (x, y2), target_x=x, signal=signal)

        def is_commutative(t: str) -> bool:
            t = t.upper()
            return t in {"AND", "OR", "NAND", "NOR", "XOR", "XNOR"}

        gate_anchor_order: Dict[str, List[Tuple[float, float]]] = {}
        for gname, elem in gate_elems.items():
            anchors = []
            for pin in ('in1', 'in2', 'in3', 'in4', 'in'):
                if hasattr(elem, pin):
                    anchors.append(getattr(elem, pin))
            if anchors:
                anchors.sort(key=lambda p: p[1])
                gate_anchor_order[gname] = anchors

        sinks: Dict[str, List[Tuple[str, Tuple[float, float]]]] = {}
        for g in self.gates:
            inputs_for_pinning = list(g.inputs)
            if is_commutative(g.type) and len(inputs_for_pinning) >= 2:
                try:
                    inputs_for_pinning.sort(key=lambda s: sig_source_pt.get(s, (0.0, 0.0))[1])
                except Exception:
                    pass
            anchors = gate_anchor_order.get(g.name, [])
            for s, anchor in zip(inputs_for_pinning, anchors):
                sinks.setdefault(s, []).append((g.name, anchor))

        ordered_signals = sorted(sig_source_pt.items(), key=lambda kv: kv[1][1])
        inputs_sorted = sorted(self.inputs)
        input_index_map = {name: idx for idx, name in enumerate(inputs_sorted)}

        trunk_stride = max(0.45, grid_x or 0.45)
        min_gap = 0.35
        used_verticals: List[Tuple[float, float, float]] = []

        for order_idx, (sig, src_pt) in enumerate(ordered_signals):
            dst_points: List[Tuple[float, float]] = []
            for (gname, anchor) in sinks.get(sig, []):
                if anchor is not None:
                    dst_points.append((anchor[0], anchor[1]))
            if sig in output_anchor:
                dst_points.append(output_anchor[sig])
            if not dst_points:
                continue
            is_primary_input = sig in self.inputs
            # Get line styling for this signal
            sig_line_kwargs = {}
            sig_ls = get_line_style(sig)
            sig_lw = get_line_width(sig)
            if sig_ls != '-':
                sig_line_kwargs['ls'] = sig_ls
            if sig_lw is not None:
                sig_line_kwargs['lw'] = sig_lw

            if is_primary_input:
                min_dx = min(x for x, _ in dst_points)
                bus_y = src_pt[1]
                src_stub = (src_pt[0] + 0.25, bus_y)
                d.add(elm.Line(**sig_line_kwargs).at(src_pt).to(src_stub))
                gate_anchors = [(x, y) for (x, y) in dst_points if (x, y) not in output_anchor.values()]
                if len(gate_anchors) == 1:
                    dx, dy = gate_anchors[0]
                    pre = (snap(dx - 0.6, grid_x), bus_y)
                    hline_avoid(src_stub, pre, target_x=dx, signal=sig)
                    if abs(dy - bus_y) > 1e-3:
                        vline_avoid(pre, (pre[0], dy), signal=sig)
                    d.add(elm.Line(**sig_line_kwargs).at((pre[0], dy)).to((dx, dy)))
                else:
                    preferred = snap(min_dx - 1.2, grid_x)
                    tap_x = max(src_stub[0] + 0.6, preferred)
                    taps_ys = [y for (_, y) in dst_points] + [bus_y]
                    t_lo, t_hi = (min(taps_ys), max(taps_ys))
                    def v_conflict(x):
                        for ux, y0, y1 in used_verticals:
                            if abs(x - ux) < min_gap and not (t_hi < y0 or t_lo > y1):
                                return True
                        return False
                    if v_conflict(tap_x):
                        delta = trunk_stride
                        tries = 0
                        while v_conflict(tap_x) and tries < 6:
                            tap_x += ((-1)**tries) * delta
                            tap_x = snap(tap_x, grid_x)
                            tries += 1
                    used_verticals.append((tap_x, t_lo, t_hi))
                    hline_avoid(src_stub, (tap_x, bus_y), target_x=tap_x, signal=sig)
                    for (dx, dy) in sorted(dst_points, key=lambda p: p[1]):
                        if abs(dy - bus_y) > 1e-3:
                            d.add(elm.Dot().at((tap_x, bus_y)))
                            vline_avoid((tap_x, bus_y), (tap_x, dy), signal=sig)
                        pre = (dx - 0.6, dy)
                        hline_avoid((tap_x, dy), pre, target_x=dx, signal=sig)
                        d.add(elm.Line(**sig_line_kwargs).at(pre).to((dx, dy)))
            else:
                min_dst_x = min(x for x, _ in dst_points)
                base_midx = (src_pt[0] + min_dst_x) / 2.0
                candidate = snap(base_midx, grid_x)
                candidate = min(candidate, min_dst_x - 0.6)
                candidate = max(candidate, src_pt[0] + 0.6)
                ys = [y for _, y in dst_points] + [src_pt[1]]
                y_lo, y_hi = (min(ys), max(ys))
                midx = candidate
                def v_conflict2(x):
                    for ux, y0, y1 in used_verticals:
                        if abs(x - ux) < min_gap and not (y_hi < y0 or y_lo > y1):
                            return True
                    return False
                if v_conflict2(midx):
                    shift = trunk_stride
                    tries = 0
                    while v_conflict2(midx) and tries < 10:
                        midx += ((-1)**tries) * shift
                        midx = snap(midx, grid_x)
                        tries += 1
                used_verticals.append((midx, y_lo, y_hi))
                src_stub = (src_pt[0] + 0.25, src_pt[1])

                # Label signals based on options
                should_label = False
                if show_all_labels:
                    # Show all labels except auto-generated if --no-internal-labels
                    if show_internal_labels:
                        should_label = sig in self.internal_signals
                    else:
                        # Skip auto-generated labels
                        should_label = sig in self.internal_signals and not (sig.startswith('auto_') or sig.startswith('_expr_'))
                else:
                    # Only show inputs/outputs
                    should_label = sig in self.inputs or sig in self.outputs

                if should_label:
                    label_x = (src_stub[0] + midx) / 2.0
                    d.add(elm.Line(**sig_line_kwargs).at(src_pt).to(src_stub).label(sig, 'top', ofst=0.1, fontsize=8))
                else:
                    d.add(elm.Line(**sig_line_kwargs).at(src_pt).to(src_stub))

                hline_avoid(src_stub, (midx, src_stub[1]), target_x=midx, signal=sig)
                d.add(elm.Dot().at((midx, src_stub[1])))
                ys = [y for _, y in dst_points] + [src_stub[1]]
                y_lo, y_hi = (min(ys), max(ys))
                if y_hi - y_lo > 0.01:
                    vline_avoid((midx, y_lo), (midx, y_hi), signal=sig)
                for (dx, dy) in sorted(dst_points, key=lambda p: p[1]):
                    d.add(elm.Dot().at((midx, dy)))
                    pre = (dx - 0.6, dy)
                    hline_avoid((midx, dy), pre, target_x=dx, signal=sig)
                    d.add(elm.Line(**sig_line_kwargs).at(pre).to((dx, dy)))

        # Add truth table if requested
        if show_table:
            truth_table = self._generate_truth_table()
            if truth_table:
                # Position table below the circuit, left aligned
                # In Schemdraw, negative Y is down, so subtract to go lower
                table_x = left_margin
                col_width = 1.2
                row_height = 0.6
                header_y = min_y - 3.0  # Subtract to position below (more negative)

                sorted_inputs = sorted(self.inputs)
                sorted_outputs = sorted(self.outputs)
                headers = sorted_inputs + sorted_outputs

                # Draw table headers
                for i, header in enumerate(headers):
                    x = table_x + i * col_width
                    d.add(elm.Label().label(header, fontsize=9).at((x, header_y)))

                # Draw table rows (going downward from header - subtract to go more negative)
                for row_idx, row in enumerate(truth_table):
                    row_y = header_y - (row_idx + 1) * row_height  # Subtract for downward in Schemdraw
                    for col_idx, header in enumerate(headers):
                        x = table_x + col_idx * col_width
                        value = '1' if row[header] else '0'
                        d.add(elm.Label().label(value, fontsize=8).at((x, row_y)))

        bbox = d.get_bbox()
        svg_bytes = d.get_imagedata('svg')
        svg_text = svg_bytes.decode('utf-8')
        if rotate_svg:
            svg_text = _rotate_svg_clockwise(svg_text, bbox)

        # Return SVG data if no output file specified or stdout requested
        if to_stdout or output_filename is None:
            return svg_text

        ext = os.path.splitext(output_filename)[1].lower()
        if rotate_svg and ext not in ('.svg', ''):
            raise ValueError("Vertical orientation is only supported for SVG outputs.")

        if not rotate_svg and ext not in ('.svg', ''):
            d.save(output_filename)
            return None

        with open(output_filename, 'w', encoding='utf-8') as fh:
            fh.write(svg_text)
        return None

    def _add_gate(self, d, g: Gate, x: float, y: float, fontsize: int = 9, fill_gates: bool = False, style_settings: dict = None, show_internal_labels: bool = True, show_all_labels: bool = True):
        t = g.type.upper()
        label = g.name

        # Determine if this gate should be labeled
        should_show_label = True
        if not show_all_labels:
            # Only show if output is in self.outputs
            should_show_label = g.output in self.outputs
        elif not show_internal_labels:
            # Skip auto-generated labels
            should_show_label = not (label.startswith('auto_') or label.startswith('_expr_'))

        # Clear label if it shouldn't be shown
        if not should_show_label:
            label = ''

        # Determine fill color if enabled
        fill_color = None
        if fill_gates and style_settings:
            gate_fills = style_settings.get('gate_fills', {})
            if gate_fills:
                fill_color = gate_fills.get(t)
            elif fill_gates:
                # Default subtle fills when --fill-gates used without vibrant style
                default_fills = {
                    'AND': '#e8f4f8', 'NAND': '#e8f4f8',
                    'OR': '#f0f8ff', 'NOR': '#f0f8ff',
                    'XOR': '#fffacd', 'XNOR': '#fffacd',
                    'NOT': '#f5e6ff', 'BUF': '#e0f2f1',
                }
                fill_color = default_fills.get(t)

        # Helper to add fill if available
        def maybe_fill(elem):
            if fill_color:
                return elem.fill(fill_color)
            return elem

        if t == 'NAND':
            return d.add(maybe_fill(logic.Nand().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t == 'AND':
            return d.add(maybe_fill(logic.And().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t == 'OR':
            return d.add(maybe_fill(logic.Or().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t == 'NOR':
            return d.add(maybe_fill(logic.Nor().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t == 'XOR':
            return d.add(maybe_fill(logic.Xor().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t == 'XNOR':
            return d.add(maybe_fill(logic.Xnor().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
        if t in ('NOT', 'INV'):
            elem = maybe_fill(logic.Not().at((x, y)).anchor('in1'))
            return d.add(elem.label(label, 'bottom', fontsize=fontsize))
        if t in ('BUF', 'BUFFER'):
            try:
                return d.add(maybe_fill(logic.Buffer().at((x, y)).anchor('in1')).label(label, 'bottom', fontsize=fontsize))
            except Exception:
                return d.add(maybe_fill(elm.Rect(w=1, h=1).at((x, y))).label(f"BUF:{label}", 'bottom', fontsize=fontsize))
        return d.add(maybe_fill(elm.Rect(w=1, h=1).at((x, y))).label(f"{t}:{label}", 'bottom', fontsize=fontsize))
