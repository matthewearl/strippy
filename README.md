Strippy
=======

Strippy is an automated
[*Strip*board](https://en.wikipedia.org/wiki/Stripboard)
[placement](https://en.wikipedia.org/wiki/Placement_(EDA)) tool, implemented in
*Py*thon.

Strippy is a work-in-progress, and highly experimental. Currently only a few
component types are supported, and it can solve very small problems in a
reasonable time frame.

Usage
-----

Currently netlists, board parameters, and components are defined in Python,
which are then passed into `cli.main` which parses common command line options
and then solves the given problem.

Examples
--------

Note: All of these examples require the repository root to be in the
`PYTHONPATH`.

Placement of a resistor on a 1x2 stripboard:

   examples/1-resistor.py --svg output/1-resistor.svg

Placement of a 4-pin DIP package, with resistors joining adjacent pins:

   examples/dip2.py --allow-drilled --svg output/dip2.svg

This example requires `--allow-drilled` to be passed to find solutions, to
ensure opposing pins of the DIP package are disconnected.
    
Placement of a 4-pin DIP package, with resistors joining opposing pins:

   examples/dip3.py --first-only --allow-drilled --max-jumper-length=1 --svg output/

Note that `--max-jumper-length=1` is passed to allow jumpers (with a maximum
length of 1) in the solution. `--first-only` is passed so that only the first
solution found (of which there are many) are displayed.


