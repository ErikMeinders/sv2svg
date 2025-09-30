from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
import schemdraw.elements as elm


@dataclass
class LayoutGate:
    """Gate data for layout processing."""
    name: str
    type: str
    inputs: List[str]
    output: str
    level: int = 0
    x: float = 0.0
    y: float = 0.0
    element: Any = None


@dataclass
class LayoutSignal:
    """Signal routing information."""
    name: str
    source_point: Tuple[float, float]
    sink_points: List[Tuple[float, float]]
    is_input: bool = False
    is_output: bool = False


@dataclass
class LayoutConfig:
    """Layout configuration parameters."""
    x_step: float = 4.0
    y_step: float = 2.2
    left_margin: float = 0.5
    grid_x: float = 0.5
    grid_y: float = 0.5
    symmetry: bool = True
    trunk_stride: float = 0.45
    min_gap: float = 0.35


class LayoutEngine:
    """Dedicated layout engine for SystemVerilog circuit diagrams."""

    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()
        self.gates: List[LayoutGate] = []
        self.signals: Dict[str, LayoutSignal] = {}
        self.signal_driver: Dict[str, str] = {}
        self.signal_sinks: Dict[str, List[str]] = {}
        self.levels: Dict[int, List[LayoutGate]] = {}
        self.bboxes: List[Dict[str, float]] = []
        self.used_verticals: List[Tuple[float, float, float]] = []

    def add_gate(self, name: str, gate_type: str, inputs: List[str], output: str) -> None:
        """Add a gate to the layout."""
        gate = LayoutGate(name=name, type=gate_type, inputs=inputs, output=output)
        self.gates.append(gate)

    def set_connectivity(self, signal_driver: Dict[str, str], signal_sinks: Dict[str, List[str]]) -> None:
        """Set signal connectivity information."""
        self.signal_driver = signal_driver
        self.signal_sinks = signal_sinks

    def assign_levels(self) -> None:
        """Assign level to each gate using topological sorting."""
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

        def gate_level(g: LayoutGate) -> int:
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

    def reorder_by_barycenter(self, inputs: List[str]) -> None:
        """Reorder gates within each level using barycenter algorithm."""
        # Group gates by level
        self.levels = {}
        for g in self.gates:
            self.levels.setdefault(g.level, []).append(g)

        if not self.levels:
            return

        max_level = max(self.levels)

        # Sort gates within each level initially by name
        for lvl in self.levels:
            self.levels[lvl] = sorted(self.levels[lvl], key=lambda gg: gg.name)

        # Initialize positions for primary inputs
        prev_positions: Dict[str, int] = {f"IN:{name}": idx for idx, name in enumerate(sorted(inputs))}

        def get_predecessors(g: LayoutGate) -> List[str]:
            """Get predecessor IDs for a gate."""
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

        # Iteratively refine positions using barycenter method
        for _ in range(3):
            for lvl in range(1, max_level + 1):
                glist = self.levels.get(lvl, [])
                if not glist:
                    continue

                scores = []
                for g in glist:
                    predecessors = get_predecessors(g)
                    if predecessors:
                        vals = [prev_positions.get(pid, 0) for pid in predecessors]
                        barycenter = sum(vals) / len(vals)
                    else:
                        barycenter = 0.0
                    scores.append((barycenter, g))

                # Sort by barycenter, then by name for stable ordering
                self.levels[lvl] = [g for _, g in sorted(scores, key=lambda t: (t[0], t[1].name))]

                # Update positions for next level
                prev_positions = {f"G:{g.name}": i for i, g in enumerate(self.levels[lvl])}

            # Reset input positions for next iteration
            prev_positions = {f"IN:{name}": idx for idx, name in enumerate(sorted(inputs))}

    def position_gates(self, inputs: List[str], input_order: str = 'alpha',
                      port_order: List[str] = None) -> Dict[str, Tuple[float, float]]:
        """Position gates on the grid and return signal source points."""
        sig_source_pt: Dict[str, Tuple[float, float]] = {}

        # Order inputs according to the specified strategy
        ordered_inputs = self._order_inputs(inputs, input_order, port_order or [])

        # Position primary inputs
        input_y0 = 0.0
        n_inputs = len(ordered_inputs)
        for idx, name in enumerate(ordered_inputs):
            y = input_y0 + (n_inputs - 1 - idx) * self.config.y_step
            x = self.config.left_margin + 0.8
            sig_source_pt[name] = (x, y)

        # Position gates level by level
        if not self.levels:
            return sig_source_pt

        max_level = max(self.levels)

        for lvl in sorted(self.levels.keys()):
            gates_at_level = self.levels[lvl]

            # Calculate target Y positions based on input positions
            y_targets = []
            for g in gates_at_level:
                if g.inputs and all(s in sig_source_pt for s in g.inputs):
                    y = sum(sig_source_pt[s][1] for s in g.inputs) / len(g.inputs)
                else:
                    y = 0.0
                y_targets.append((g, y))

            # Apply symmetry optimization if enabled
            if self.config.symmetry and gates_at_level:
                y_targets = self._apply_symmetry_optimization(y_targets, gates_at_level, sig_source_pt)

            # Sort and place gates with proper spacing
            y_targets.sort(key=lambda t: (t[1], t[0].name))
            placed = []
            last_y = None

            for g, target_y in y_targets:
                y = target_y if last_y is None else max(target_y, last_y + self.config.y_step)
                y = self._snap(y, self.config.grid_y)
                last_y = y

                x = self.config.left_margin + self.config.x_step * float(lvl)
                x = self._snap(x, self.config.grid_x)

                g.x, g.y = x, y
                # Assume gate output is at (x + 1.5, y) - this will be refined when gate elements are created
                sig_source_pt[g.output] = (x + 1.5, y)

        return sig_source_pt

    def _order_inputs(self, inputs: List[str], input_order: str, port_order: List[str]) -> List[str]:
        """Order inputs according to the specified strategy."""
        if input_order == 'ports':
            ordered_inputs = [p for p in port_order if p in inputs]
            ordered_inputs += [s for s in sorted(inputs) if s not in ordered_inputs]
        elif input_order == 'auto':
            if port_order:
                ordered_inputs = [p for p in port_order if p in inputs]
                ordered_inputs += [s for s in sorted(inputs) if s not in ordered_inputs]
            else:
                ordered_inputs = sorted(inputs)
        else:
            ordered_inputs = sorted(inputs)
        return ordered_inputs

    def _apply_symmetry_optimization(self, y_targets: List[Tuple[LayoutGate, float]],
                                   gates_at_level: List[LayoutGate],
                                   sig_source_pt: Dict[str, Tuple[float, float]]) -> List[Tuple[LayoutGate, float]]:
        """Apply symmetry optimization to gate positioning."""
        # Group gates by shared signal sources
        source_to_gates: Dict[str, List[LayoutGate]] = {}
        for g in gates_at_level:
            for s in g.inputs:
                if s in sig_source_pt:
                    source_to_gates.setdefault(s, []).append(g)

        # Find groups with multiple gates (symmetry candidates)
        candidate_groups = {s: gl for s, gl in source_to_gates.items() if len(gl) >= 2}

        if not candidate_groups:
            return y_targets

        # Assign gates to their primary symmetry group
        g_assigned: Dict[str, str] = {}
        for s, gl in sorted(candidate_groups.items(), key=lambda kv: -len(kv[1])):
            for g in gl:
                if g.name not in g_assigned:
                    g_assigned[g.name] = s

        # Calculate symmetry overrides
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

            # Sort members by current Y position
            members_sorted = sorted(members, key=lambda gg: current_map.get(gg.name, 0.0))
            m = len(members_sorted)

            # Position symmetrically around center
            for i, gg in enumerate(members_sorted):
                offset = (i - (m - 1) / 2.0) * self.config.y_step
                overrides[gg.name] = center_y + offset

        # Apply overrides
        y_targets = [
            (g, overrides.get(g.name, ty))
            for (g, ty) in y_targets
        ]
        y_targets.sort(key=lambda t: (t[1], t[0].name))

        return y_targets

    def create_routing_plan(self, sig_source_pt: Dict[str, Tuple[float, float]],
                          inputs: List[str], outputs: List[str]) -> Dict[str, LayoutSignal]:
        """Create routing plan for all signals."""
        signals = {}

        # Prepare gate anchor information for input pin assignment
        gate_anchor_order: Dict[str, List[Tuple[float, float]]] = {}
        for g in self.gates:
            # For now, assume standard gate input positions
            # This would be refined when actual gate elements are available
            anchors = []
            for i in range(len(g.inputs)):
                # Estimate input positions based on gate position
                anchor_y = g.y + (i - (len(g.inputs) - 1) / 2.0) * 0.4
                anchors.append((g.x - 0.5, anchor_y))
            gate_anchor_order[g.name] = anchors

        # Create signal routing information
        for signal_name, source_pt in sig_source_pt.items():
            sink_points = []

            # Add gate input sinks
            for g in self.gates:
                if signal_name in g.inputs:
                    anchors = gate_anchor_order.get(g.name, [])
                    input_idx = g.inputs.index(signal_name) if signal_name in g.inputs else 0
                    if input_idx < len(anchors):
                        sink_points.append(anchors[input_idx])

            # Add output sinks
            if signal_name in outputs:
                # Estimate output position
                max_level = max(self.levels) if self.levels else 0
                out_x = self.config.left_margin + self.config.x_step * (max_level + 1.1) - 0.8
                out_y = source_pt[1]  # Use same Y as source for now
                sink_points.append((out_x, out_y))

            if sink_points:
                signals[signal_name] = LayoutSignal(
                    name=signal_name,
                    source_point=source_pt,
                    sink_points=sink_points,
                    is_input=(signal_name in inputs),
                    is_output=(signal_name in outputs)
                )

        return signals

    def generate_optimized_routing(self, signals: Dict[str, LayoutSignal]) -> List[Dict[str, Any]]:
        """Generate optimized routing commands with reduced dots and direction changes."""
        routing_commands = []

        # Reset vertical usage tracking
        self.used_verticals = []

        # Sort signals by Y position for consistent processing
        ordered_signals = sorted(signals.items(), key=lambda kv: kv[1].source_point[1])

        for signal_name, signal in ordered_signals:
            commands = self._route_signal_optimized(signal)
            routing_commands.extend(commands)

        return routing_commands

    def _route_signal_optimized(self, signal: LayoutSignal) -> List[Dict[str, Any]]:
        """Generate optimized routing for a single signal."""
        commands = []
        src_pt = signal.source_point
        dst_points = signal.sink_points

        if not dst_points:
            return commands

        # Add source stub
        src_stub = (src_pt[0] + 0.25, src_pt[1])
        commands.append({
            'type': 'line',
            'from': src_pt,
            'to': src_stub
        })

        if signal.is_input:
            commands.extend(self._route_primary_input_optimized(signal, src_stub))
        else:
            commands.extend(self._route_internal_signal_optimized(signal, src_stub))

        return commands

    def _route_primary_input_optimized(self, signal: LayoutSignal, src_stub: Tuple[float, float]) -> List[Dict[str, Any]]:
        """Route primary input with optimized path planning."""
        commands = []
        dst_points = signal.sink_points

        # Filter out output destinations for separate handling
        gate_anchors = [(x, y) for (x, y) in dst_points if not self._is_output_anchor(x, y)]
        output_anchors = [(x, y) for (x, y) in dst_points if self._is_output_anchor(x, y)]

        if len(gate_anchors) == 1 and not output_anchors:
            # Single destination - direct routing
            dx, dy = gate_anchors[0]
            bus_y = src_stub[1]

            # Route directly if Y positions align, otherwise use minimal segments
            if abs(dy - bus_y) < 1e-3:
                commands.append({
                    'type': 'line',
                    'from': src_stub,
                    'to': (dx, dy)
                })
            else:
                pre = (dx - 0.6, bus_y)
                commands.append({
                    'type': 'line_avoid_h',
                    'from': src_stub,
                    'to': pre,
                    'target_x': dx
                })
                commands.append({
                    'type': 'line',
                    'from': pre,
                    'to': (pre[0], dy)
                })
                commands.append({
                    'type': 'line',
                    'from': (pre[0], dy),
                    'to': (dx, dy)
                })
        else:
            # Multiple destinations - use trunk routing
            commands.extend(self._create_trunk_routing(signal, src_stub, dst_points))

        return commands

    def _route_internal_signal_optimized(self, signal: LayoutSignal, src_stub: Tuple[float, float]) -> List[Dict[str, Any]]:
        """Route internal signal with optimized midpoint routing."""
        commands = []
        dst_points = signal.sink_points

        if len(dst_points) == 1:
            # Single destination - direct routing
            dx, dy = dst_points[0]

            # Check if we can route directly
            if abs(dy - src_stub[1]) < 1e-3:
                # Same Y level - direct horizontal line
                commands.append({
                    'type': 'line',
                    'from': src_stub,
                    'to': (dx, dy)
                })
            else:
                # Different Y levels - use L-shaped routing
                midx = (src_stub[0] + dx) / 2.0
                midx = self._snap(midx, self.config.grid_x)

                commands.append({
                    'type': 'line_avoid_h',
                    'from': src_stub,
                    'to': (midx, src_stub[1]),
                    'target_x': midx
                })
                commands.append({
                    'type': 'line',
                    'from': (midx, src_stub[1]),
                    'to': (midx, dy)
                })
                commands.append({
                    'type': 'line',
                    'from': (midx, dy),
                    'to': (dx, dy)
                })
        else:
            # Multiple destinations - use midpoint trunk
            commands.extend(self._create_midpoint_routing(signal, src_stub, dst_points))

        return commands

    def _create_trunk_routing(self, signal: LayoutSignal, src_stub: Tuple[float, float],
                            dst_points: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Create trunk-style routing for signals with multiple destinations."""
        commands = []

        min_dx = min(x for x, _ in dst_points)
        bus_y = src_stub[1]

        # Calculate trunk position
        trunk_x = max(src_stub[0] + 0.6, self._snap(min_dx - 1.2, self.config.grid_x))

        # Find available vertical space
        all_ys = [y for _, y in dst_points] + [bus_y]
        y_lo, y_hi = min(all_ys), max(all_ys)

        # Check for conflicts and adjust if necessary
        trunk_x = self._find_available_vertical(trunk_x, y_lo, y_hi)

        # Route to trunk
        commands.append({
            'type': 'line_avoid_h',
            'from': src_stub,
            'to': (trunk_x, bus_y),
            'target_x': trunk_x
        })

        # Add dots only where branches occur
        need_dots = len([y for _, y in dst_points if abs(y - bus_y) > 1e-3]) > 0

        # Route from trunk to each destination
        for dx, dy in sorted(dst_points, key=lambda p: p[1]):
            if abs(dy - bus_y) > 1e-3 and need_dots:
                # Vertical segment needed
                commands.append({
                    'type': 'dot',
                    'at': (trunk_x, bus_y)
                })
                commands.append({
                    'type': 'line_avoid_v',
                    'from': (trunk_x, bus_y),
                    'to': (trunk_x, dy)
                })
                need_dots = False  # Only add dot once per trunk

            # Horizontal segment to destination
            pre = (dx - 0.6, dy)
            commands.append({
                'type': 'line_avoid_h',
                'from': (trunk_x, dy),
                'to': pre,
                'target_x': dx
            })
            commands.append({
                'type': 'line',
                'from': pre,
                'to': (dx, dy)
            })

        return commands

    def _create_midpoint_routing(self, signal: LayoutSignal, src_stub: Tuple[float, float],
                               dst_points: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Create midpoint routing for internal signals."""
        commands = []

        # Calculate optimal midpoint
        min_dst_x = min(x for x, _ in dst_points)
        base_midx = (src_stub[0] + min_dst_x) / 2.0
        midx = self._snap(base_midx, self.config.grid_x)
        midx = min(midx, min_dst_x - 0.6)
        midx = max(midx, src_stub[0] + 0.6)

        # Check for vertical conflicts
        all_ys = [y for _, y in dst_points] + [src_stub[1]]
        y_lo, y_hi = min(all_ys), max(all_ys)
        midx = self._find_available_vertical(midx, y_lo, y_hi)

        # Route to midpoint
        commands.append({
            'type': 'line_avoid_h',
            'from': src_stub,
            'to': (midx, src_stub[1]),
            'target_x': midx
        })

        # Add junction dot
        commands.append({
            'type': 'dot',
            'at': (midx, src_stub[1])
        })

        # Create vertical trunk if needed
        if y_hi - y_lo > 0.01:
            commands.append({
                'type': 'line_avoid_v',
                'from': (midx, y_lo),
                'to': (midx, y_hi)
            })

        # Route to each destination
        for dx, dy in sorted(dst_points, key=lambda p: p[1]):
            if abs(dy - src_stub[1]) > 1e-3:
                commands.append({
                    'type': 'dot',
                    'at': (midx, dy)
                })

            pre = (dx - 0.6, dy)
            commands.append({
                'type': 'line_avoid_h',
                'from': (midx, dy),
                'to': pre,
                'target_x': dx
            })
            commands.append({
                'type': 'line',
                'from': pre,
                'to': (dx, dy)
            })

        return commands

    def _find_available_vertical(self, preferred_x: float, y_lo: float, y_hi: float) -> float:
        """Find available vertical position avoiding conflicts."""
        def has_conflict(x):
            for ux, uy0, uy1 in self.used_verticals:
                if abs(x - ux) < self.config.min_gap and not (y_hi < uy0 or y_lo > uy1):
                    return True
            return False

        x = preferred_x
        if has_conflict(x):
            delta = self.config.trunk_stride
            for tries in range(10):
                x = preferred_x + ((-1)**tries) * delta * (tries // 2 + 1)
                x = self._snap(x, self.config.grid_x)
                if not has_conflict(x):
                    break

        # Register this vertical usage
        self.used_verticals.append((x, y_lo, y_hi))
        return x

    def _is_output_anchor(self, x: float, y: float) -> bool:
        """Check if coordinates represent an output anchor."""
        # This is a heuristic - output anchors are typically at the right side
        if not self.levels:
            return False
        max_level = max(self.levels)
        out_x_threshold = self.config.left_margin + self.config.x_step * (max_level + 1.0)
        return x >= out_x_threshold

    def _snap(self, val: float, step: float) -> float:
        """Snap value to grid."""
        if step and step > 0:
            return round(val / step) * step
        return val

    def update_bboxes(self, gate_elements: Dict[str, Any]) -> None:
        """Update bounding box information for collision avoidance."""
        self.bboxes = []
        for gate_name, elem in gate_elements.items():
            try:
                # Extract input pin positions
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

                self.bboxes.append({
                    'name': gate_name,
                    'left': left,
                    'right': right,
                    'top': top,
                    'bottom': bottom
                })
            except Exception:
                continue