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

__all__ = (
    'place',
)

import cnf


class PositionVar(cnf.Var):
    """
    A variable which is true if a particular component is in a particular
    position.

    """

    def __init__(self, component, position_idx):
        self.component = component
        self.position_idx = position_idx

        super().__init__()

class NetVar(cnf.Var):
    """
    A variable which is true iff a particular hole is in a particular net.

    """

    def __init__(self, hole_idx, net_idx):
        self.hole_idx = hole_idx
        self.net_idx = net_idx

        super().__init__()

class _HashableDict():
    """
    A dumb wrapper around a dict to make it hashable.

    The hash is just the id() so don't use in sets/dicts where this might be an
    issue.

    """
    def __init__(self, position):
        self._position = position

    def __getitem__(self, key):
        return self._position[key]


def place(board, components, nets):
    """

    """

    # Modify all objects that we wish to use as keys below such that they are
    # hashable.
    nets = [frozenset(net) for net in nets]
    positions = {c: [_HashableDict(p) for p in c.get_positions(board)]
                                                           for c in components}

    # Set up variables.
    #  - position_vars[comp, pos] is true iff component `comp` is in position
    #    `pos`.
    #  - net_vars[hole, net] is true iff hole `net` is part of the net `net`.
    #  - grid_vars[comp, hole] if component `comp` is occupying hole `hole`.
    position_vars = {(comp, pos): cnf.Var()
                                for comp in components for pos in positions[c]}
    net_vars = {(hole, net): cnf.Var() for hole in holes for net in nets}
    grid_vars = {(comp, hole): cnf.Var()
                                      for comp in components for hole in holes}

    # Build up a CNF expression:
    #  - A component can be in at most one position.
    #  - If a hole that is part of a strip is in a net, then the next hole in
    #    the strip is also in that net, and vice versa.
    expr = cnf.Expr.all(cnf.at_most_one(position_vars[comp, pos]
                                            for pos in positions[c])
                            for comp in components)
    expr |= cnf.Expr.all(cnf.iff(net_vars[strip[i], net],
                                     net_vars[strip[i + 1], net])
                            for strip in board.strips
                                for i in range(len(strip) - 1)
                                    for net in nets)


