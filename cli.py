# Copyright (c) 2015 Matthew Earl
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
#     The above copyright notice and this permission notice shall be included
#     in all copies or substantial portions of the Software.
# 
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#     OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#     MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
#     NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#     OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
#     USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Command line interface for solving a placement problem.

"""

__all__ = (
    'main',
)

import argparse
import sys

import placer
import solver
import svg

def main(board, components, nets, args=None):
    sys.setrecursionlimit(100000)

    parser = argparse.ArgumentParser( description='Find circuit placements.')
    parser.add_argument('--first-only', action='store_true',
                        help="Only output the first solution")
    parser.add_argument('--allow-drilled', action='store_true',
                        help="Allow holes to be drilled out")
    parser.add_argument('--max-jumper-length', nargs='?', type=int, default=0,
                        help="Maximum jumper length")
    parser.add_argument('--svg', nargs='?', const=True,
                        help="Output SVG for the solutions")
    parser.add_argument('--solver', nargs='?', type=str, default=None,
                        help="Solver to use. Options are: {}.".format(
                            ", ".join(str(x) for x in solver.solvers.keys())))

    parsed_args = parser.parse_args(args if args is not None else sys.argv[1:])

    if parsed_args.solver:
        slvr = solver.solvers[parsed_args.solver]
    else:
        slvr = None

    placement_iter = placer.place(
                          board, components, nets,
                          allow_drilled=parsed_args.allow_drilled,
                          max_jumper_length=parsed_args.max_jumper_length,
                          slvr=slvr)

    if parsed_args.first_only:
        placement_iter = [next(placement_iter)]

    if not parsed_args.svg:
        count = 0
        for placement in placement_iter:
            placement.print_solution()
            print()
            count += 1
        print("{} solutions".format(count))
    else:
        if isinstance(parsed_args.svg, str):
            with open(parsed_args.svg, "w") as f:
                svg.print_svg(placement_iter, file=f)
        else:
            svg.print_svg(placement_iter, file=sys.stdout)

    
