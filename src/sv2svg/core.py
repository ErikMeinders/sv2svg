# Ported from project sv2schemdraw.py (single-file) to reusable module
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import schemdraw
import schemdraw.elements as elm
import schemdraw.logic as logic


@dataclass
class Gate:
    name: str
    type: str
    inputs: List[str]
    output: str
    level: int = 0


STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "classic": {
        "config": {"color": "#2c3e50", "lw": 1.1, "fontsize": 12},
        "module_label_color": "#1f618d",
    },
    "blueprint": {
        "config": {"color": "#0b3d91", "lw": 1.25, "fontsize": 12},
        "module_label_color": "#0b3d91",
    },
    "midnight": {
        "config": {"color": "#00bcd4", "lw": 1.2, "fontsize": 12},
        "module_label_color": "#00bcd4",
    },
    "mono": {
        "config": {"color": "#2d3436", "lw": 1.0, "fontsize": 12},
        "module_label_color": "#2d3436",
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

        # Parse assign statements for simple two-input gate patterns
        # NOTE: This only supports basic two-input gate operations. Complex expressions
        # like "y = a & b | c" or multi-input operations "y = a & b & c" are NOT supported.
        # For complex logic, use explicit gate instantiations (e.g., AND u1(a, b, y);)
        
        # NAND: y = ~(a & b)
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*~\s*\(\s*(\w+)\s*&\s*(\w+)\s*\)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_nand_{len([g for g in self.gates if g.type=='NAND'])+1}"
                self.gates.append(Gate(name=auto_name, type="NAND", inputs=[a, b], output=y))
        
        # AND: y = a & b
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*(\w+)\s*&\s*(\w+)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_and_{len([g for g in self.gates if g.type=='AND'])+1}"
                self.gates.append(Gate(name=auto_name, type="AND", inputs=[a, b], output=y))
        
        # NOR: y = ~(a | b)
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*~\s*\(\s*(\w+)\s*\|\s*(\w+)\s*\)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_nor_{len([g for g in self.gates if g.type=='NOR'])+1}"
                self.gates.append(Gate(name=auto_name, type="NOR", inputs=[a, b], output=y))
        
        # OR: y = a | b
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*(\w+)\s*\|\s*(\w+)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_or_{len([g for g in self.gates if g.type=='OR'])+1}"
                self.gates.append(Gate(name=auto_name, type="OR", inputs=[a, b], output=y))
        
        # XNOR: y = ~(a ^ b)
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*~\s*\(\s*(\w+)\s*\^\s*(\w+)\s*\)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_xnor_{len([g for g in self.gates if g.type=='XNOR'])+1}"
                self.gates.append(Gate(name=auto_name, type="XNOR", inputs=[a, b], output=y))
        
        # XOR: y = a ^ b
        for y, a, b in re.findall(r"assign\s+(\w+)\s*=\s*(\w+)\s*\^\s*(\w+)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_xor_{len([g for g in self.gates if g.type=='XOR'])+1}"
                self.gates.append(Gate(name=auto_name, type="XOR", inputs=[a, b], output=y))
        
        # NOT/INV: y = ~a
        for y, a in re.findall(r"assign\s+(\w+)\s*=\s*~\s*(\w+)\s*;", content):
            if not any(g.output == y for g in self.gates):
                auto_name = f"auto_not_{len([g for g in self.gates if g.type=='NOT'])+1}"
                self.gates.append(Gate(name=auto_name, type="NOT", inputs=[a], output=y))

        self._build_connectivity()
        self._assign_levels()

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

    def _assign_levels(self) -> None:
        level_cache: Dict[str, int] = {}

        def signal_level(sig: str) -> int:
            drv = self.signal_driver.get(sig)
            if drv is None:
                return 0
            if drv.startswith("IN:"):
                return 0
            g = next((gg for gg in self.gates if gg.name == drv), None)
            if g is None:
                return 0
            return gate_level(g)

        def gate_level(g: Gate) -> int:
            if g.name in level_cache:
                return level_cache[g.name]
            if not g.inputs:
                level_cache[g.name] = 1
                return 1
            lvl = 1 + max(signal_level(s) for s in g.inputs)
            level_cache[g.name] = lvl
            return lvl

        for g in self.gates:
            g.level = gate_level(g)

    def _reorder_levels_by_barycenter(self) -> Dict[int, List[Gate]]:
        levels: Dict[int, List[Gate]] = {}
        for g in self.gates:
            levels.setdefault(g.level, []).append(g)
        if not levels:
            return {}
        max_level = max(levels)
        for lvl in levels:
            levels[lvl] = sorted(levels[lvl], key=lambda gg: gg.name)
        prev_positions: Dict[str, int] = {f"IN:{name}": idx for idx, name in enumerate(sorted(self.inputs))}

        def preds(g: Gate) -> List[str]:
            ids = []
            for s in g.inputs:
                drv = self.signal_driver.get(s)
                if not drv:
                    continue
                if isinstance(drv, str) and drv.startswith('IN:'):
                    ids.append(drv)
                else:
                    ids.append(f"G:{drv}")
            return ids

        for _ in range(3):
            for lvl in range(1, max_level + 1):
                glist = levels.get(lvl, [])
                if not glist:
                    continue
                scores = []
                for g in glist:
                    p = preds(g)
                    if p:
                        vals = [prev_positions.get(pid, 0) for pid in p]
                        bc = sum(vals) / len(vals)
                    else:
                        bc = 0.0
                    scores.append((bc, g))
                levels[lvl] = [g for _, g in sorted(scores, key=lambda t: (t[0], t[1].name))]
                prev_positions = {f"G:{g.name}": i for i, g in enumerate(levels[lvl])}
            prev_positions = {f"IN:{name}": idx for idx, name in enumerate(sorted(self.inputs))}
        return levels

    def generate_diagram(
        self,
        output_filename: str,
        input_order: str = 'alpha',
        grid_x: float = 0.5,
        grid_y: float = 0.5,
        symmetry: bool = True,
        to_stdout: bool = False,
        style: str = 'classic',
        orientation: str = 'horizontal',
    ) -> Optional[str]:
        d = schemdraw.Drawing(unit=1.2)
        style_settings = STYLE_PRESETS.get(style, STYLE_PRESETS['classic'])
        config_kwargs = dict(style_settings.get('config', {}))
        if 'fontsize' not in config_kwargs:
            config_kwargs['fontsize'] = 12
        d.config(**config_kwargs)
        module_label_color = style_settings.get('module_label_color', '#1f618d')
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
            d.add(elm.Line().at((left_margin, y)).to((left_margin + 0.8, y)).label(name, 'left'))
            src = (left_margin + 0.8, y)
            d.add(elm.Dot().at(src))
            sig_source_pt[name] = src

        levels: Dict[int, List[Gate]] = self._reorder_levels_by_barycenter()
        max_level = max(levels) if levels else 0
        gate_elems: Dict[str, any] = {}
        level_y_bases: Dict[int, float] = {}

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
                x = left_margin + x_step * float(lvl)
                elem = self._add_gate(d, g, x, y)
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
            d.add(elm.Line().at((out_x - 0.8, y)).to((out_x, y)).label(name, 'right'))
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
            detour_x = left_x if (left_x > left_margin + 0.2) else right_x
            hline_avoid((x, y1), (detour_x, y1), target_x=detour_x)
            d.add(elm.Line().at((detour_x, y1)).to((detour_x, y2)))
            hline_avoid((detour_x, y2), (x, y2), target_x=x)

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
            if is_primary_input:
                min_dx = min(x for x, _ in dst_points)
                bus_y = src_pt[1]
                src_stub = (src_pt[0] + 0.25, bus_y)
                d.add(elm.Line().at(src_pt).to(src_stub))
                gate_anchors = [(x, y) for (x, y) in dst_points if (x, y) not in output_anchor.values()]
                if len(gate_anchors) == 1:
                    dx, dy = gate_anchors[0]
                    pre = (snap(dx - 0.6, grid_x), bus_y)
                    hline_avoid(src_stub, pre, target_x=dx)
                    if abs(dy - bus_y) > 1e-3:
                        vline_avoid(pre, (pre[0], dy))
                    d.add(elm.Line().at((pre[0], dy)).to((dx, dy)))
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
                    hline_avoid(src_stub, (tap_x, bus_y), target_x=tap_x)
                    for (dx, dy) in sorted(dst_points, key=lambda p: p[1]):
                        if abs(dy - bus_y) > 1e-3:
                            d.add(elm.Dot().at((tap_x, bus_y)))
                            vline_avoid((tap_x, bus_y), (tap_x, dy))
                        pre = (dx - 0.6, dy)
                        hline_avoid((tap_x, dy), pre, target_x=dx)
                        d.add(elm.Line().at(pre).to((dx, dy)))
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
                d.add(elm.Line().at(src_pt).to(src_stub))
                hline_avoid(src_stub, (midx, src_stub[1]), target_x=midx)
                d.add(elm.Dot().at((midx, src_stub[1])))
                ys = [y for _, y in dst_points] + [src_stub[1]]
                y_lo, y_hi = (min(ys), max(ys))
                if y_hi - y_lo > 0.01:
                    vline_avoid((midx, y_lo), (midx, y_hi))
                for (dx, dy) in sorted(dst_points, key=lambda p: p[1]):
                    d.add(elm.Dot().at((midx, dy)))
                    pre = (dx - 0.6, dy)
                    hline_avoid((midx, dy), pre, target_x=dx)
                    d.add(elm.Line().at(pre).to((dx, dy)))

        bbox = d.get_bbox()
        svg_bytes = d.get_imagedata('svg')
        svg_text = svg_bytes.decode('utf-8')
        if rotate_svg:
            svg_text = _rotate_svg_clockwise(svg_text, bbox)

        if to_stdout:
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

    def _add_gate(self, d, g: Gate, x: float, y: float):
        t = g.type.upper()
        label = g.name
        if t == 'NAND':
            return d.add(logic.Nand().at((x, y)).anchor('in1').label(label, 'center'))
        if t == 'AND':
            return d.add(logic.And().at((x, y)).anchor('in1').label(label, 'center'))
        if t == 'OR':
            return d.add(logic.Or().at((x, y)).anchor('in1').label(label, 'center'))
        if t == 'NOR':
            return d.add(logic.Nor().at((x, y)).anchor('in1').label(label, 'center'))
        if t == 'XOR':
            return d.add(logic.Xor().at((x, y)).anchor('in1').label(label, 'center'))
        if t == 'XNOR':
            return d.add(logic.Xnor().at((x, y)).anchor('in1').label(label, 'center'))
        if t in ('NOT', 'INV'):
            elem = logic.Not().at((x, y)).anchor('in1')
            return d.add(elem.label(label, 'center'))
        if t in ('BUF', 'BUFFER'):
            try:
                return d.add(logic.Buffer().at((x, y)).anchor('in1').label(label, 'center'))
            except Exception:
                return d.add(elm.Box().at((x, y)).anchor('W').label(f"BUF:{label}", 'center'))
        return d.add(elm.Box().at((x, y)).anchor('W').label(f"{t}:{label}", 'center'))
