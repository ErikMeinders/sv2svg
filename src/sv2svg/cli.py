import os
import sys
import argparse

from . import __version__
from .core import SVCircuit, available_styles

def main(argv=None):
    parser = argparse.ArgumentParser(description='SystemVerilog -> Schemdraw SVG')
    parser.add_argument('input_file', help='SystemVerilog input file (.sv)')
    parser.add_argument('-o', '--output', help='Output image file (SVG recommended, use "-" for stdout)')
    parser.add_argument('--input-order', choices=['alpha', 'ports', 'auto'], default='alpha',
                        help="Order primary inputs top-to-bottom: 'alpha' (a..z), 'ports' (module header order), or 'auto' (ports if available else alpha). Default: alpha")
    parser.add_argument('--grid-x', type=float, default=0.5, help='Snap X coordinates to this grid step (0 to disable).')
    parser.add_argument('--grid-y', type=float, default=0.5, help='Snap Y coordinates to this grid step (0 to disable).')
    parser.add_argument('--no-symmetry', action='store_true', help='Disable symmetric sibling placement around shared driver centerlines.')
    parser.add_argument('--style', choices=available_styles(), default='classic',
                        help='Color/line weight preset for the generated diagram.')
    parser.add_argument('--orientation', choices=['horizontal', 'vertical'], default='horizontal',
                        help='Rotate diagram layout: horizontal (left-to-right) or vertical (top-to-bottom).')
    parser.add_argument('--table', action='store_true',
                        help='Include truth table in the diagram.')
    parser.add_argument('--no-caption', action='store_true',
                        help='Suppress the "Module: modulename" caption.')
    parser.add_argument('--fill-gates', action='store_true',
                        help='Enable subtle fill colors for logic gates.')
    parser.add_argument('--signal-styles', action='store_true',
                        help='Use different line styles for signal types (solid=primary, dashed=intermediate).')
    parser.add_argument('--fanout-wires', action='store_true',
                        help='Use thicker wires for signals with higher fan-out.')
    parser.add_argument('--no-internal-labels', action='store_true',
                        help='Suppress labels on auto-generated elements (auto_*, _expr_*).')
    parser.add_argument('--no-labels', action='store_true',
                        help='Suppress ALL labels except inputs and outputs.')
    parser.add_argument('-V', '--version', action='version', version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    out = args.output
    to_stdout = (out and out.strip() == '-')

    if not out:
        base = os.path.splitext(args.input_file)[0]
        out = f"{base}_schemdraw.svg"

    circ = SVCircuit()
    try:
        circ.parse_file(args.input_file)

        if to_stdout:
            # No output file needed for stdout
            svg_data = circ.generate_diagram(
                output_filename=None,
                input_order=args.input_order,
                grid_x=args.grid_x,
                grid_y=args.grid_y,
                symmetry=(not args.no_symmetry),
                to_stdout=True,
                style=args.style,
                orientation=args.orientation,
                show_table=args.table,
                show_caption=(not args.no_caption),
                fill_gates=args.fill_gates,
                signal_styles=args.signal_styles,
                fanout_wires=args.fanout_wires,
                show_internal_labels=(not args.no_internal_labels),
                show_all_labels=(not args.no_labels),
            )
            if svg_data is None:
                raise RuntimeError("Expected SVG data when writing to stdout")
            sys.stdout.write(svg_data)
            sys.stdout.flush()
        else:
            circ.generate_diagram(
                output_filename=out,
                input_order=args.input_order,
                grid_x=args.grid_x,
                grid_y=args.grid_y,
                symmetry=(not args.no_symmetry),
                style=args.style,
                orientation=args.orientation,
                show_table=args.table,
                show_caption=(not args.no_caption),
                fill_gates=args.fill_gates,
                signal_styles=args.signal_styles,
                fanout_wires=args.fanout_wires,
                show_internal_labels=(not args.no_internal_labels),
                show_all_labels=(not args.no_labels),
            )
            print(f"Circuit diagram saved to {out}", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
