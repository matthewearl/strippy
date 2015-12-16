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

### Single resistor

Placement of a resistor on a 1x2 stripboard:

    examples/1-resistor.py --svg output/1-resistor.svg

Here is the output:

<img src="https://cdn.rawgit.com/matthewearl/strippy/master/example-output/1-resistor.svg"></img>

The resistor is shown as a green rectangle. Note there are two output images
because of the two possible orientations of the resistor. The numbers indicate
the components' terminal numbering.

### 4-PIN DIP package, with vertical resistors

Placement of a 4-pin DIP package, with resistors joining adjacent pins:

    examples/dip2.py --max-drilled=2 --svg output/dip2.svg

This example requires `--max-drilled` to be passed to find solutions, to
allow the holes between the pins of the DIP package to be drilled.

Here is the output:

<img src="https://cdn.rawgit.com/matthewearl/strippy/master/example-output/dip2.svg"></img>

Again, there are two possible solutions. The horizontal grey lines indicate the
conductive traces on the stripboard, and the red crosses indicate which holes
should be drilled out (breaking the conductive trace).

### 4-pin DIP package, with horizontal resistors
    
Placement of a 4-pin DIP package, with resistors joining opposing pins:

    examples/dip3.py --first-only --max-drilled=2 --max-jumpers=2 --max-jumper-length=1 --svg output/dip3.svg

Note that `max-jumpers=2` and `--max-jumper-length=1` is passed to allow at
most 2 jumpers (with a maximum length of 1) in the solution. `--first-only` is
passed so that only the first solution found (of which there are many) are
displayed.

Here is the output:

<img src="https://cdn.rawgit.com/matthewearl/strippy/master/example-output/dip3.svg"></img>

The thick lines indicate where jumpers should be placed.

