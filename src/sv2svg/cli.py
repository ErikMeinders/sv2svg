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
    parser.add_argument('-V', '--version', action='version', version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    out = args.output
    to_stdout = (out == '-')

    if not out:
        base = os.path.splitext(args.input_file)[0]
        out = f"{base}_schemdraw.svg"

    circ = SVCircuit()
    try:
        circ.parse_file(args.input_file)
        svg_data = circ.generate_diagram(
            out,
            input_order=args.input_order,
            grid_x=args.grid_x,
            grid_y=args.grid_y,
            symmetry=(not args.no_symmetry),
            to_stdout=to_stdout,
            style=args.style,
            orientation=args.orientation,
        )

        if to_stdout:
            # Write SVG data to stdout as text
            if svg_data is None:
                raise RuntimeError("Expected SVG data when writing to stdout")
            sys.stdout.write(svg_data)
            sys.stdout.flush()
        else:
            print(f"Circuit diagram saved to {out}", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
