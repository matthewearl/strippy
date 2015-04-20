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

class _HashableDict():
    """
    A dumb wrapper around a dict to make it hashable.

    The hash is just the id() so don't use in sets/dicts if you want different
    objects with the same value to have only one entry.

    """
    def __init__(self, position):
        self.position = position

    def __getitem__(self, key):
        return self.position[key]

def place(board, components, nets):
    """
    Place components on a board, according to a net list.

    board: The board to place components on. A subclas of `component.Board`. 
    components: Iterable of components to place on the board. Each component is
        subclass of `component.Component`.
    nets: Iterable of nets. Each net is a set of terminals that are to be
        condutively connected.

    Yields:
        A dict of component to position mappings, which represents a placement
        of the components which satisfies the net list.

    """

    # Modify all objects that we wish to use as keys below such that they are
    # hashable.
    nets = [frozenset(net) for net in nets]
    positions = {c: [_HashableDict(p) for p in c.get_positions(board)]
                                                           for c in components}
    holes = board.holes

    # A lookup used below, which gives the net corresponding with a 
    terminal_to_net = {t: net for net in nets for t in net}

    # Set up variables.
    #  - position_vars[comp, pos] is true iff component `comp` is in position
    #    `pos`.
    #  - net_vars[hole, net] is true iff hole `net` is part of the net `net`.
    #  - grid_vars[comp, hole] if component `comp` is occupying hole `hole`.
    position_vars = {(comp, pos): cnf.Var()
                             for comp in components for pos in positions[comp]}
    net_vars = {(hole, net): cnf.Var() for hole in holes for net in nets}
    grid_vars = {(comp, hole): cnf.Var()
                                      for comp in components for hole in holes}

    # Build up a CNF expression:
    #  - A component must be in exactly one position.
    #  - If a hole that is part of a trace is in a net, then the other hole in
    #    the trace is also in that net, and vice versa.
    #  - At most one component can be in a given hole.
    #  - Each hole can be part of at most one net.
    #  - If a component is in a particular position, then each hole occupied by
    #    a terminal of the component must be part of the net corresponding with
    #    that terminal.
    #  - If a component is in a particular position, then the holes
    #    corresponding with its terminals are considered occupied.
    #    TODO: Encode physical hole occupation info, to avoid components
    #    overlapping at non-terminal locations.
    expr = cnf.Expr.all(cnf.exactly_one(position_vars[comp, pos]
                                                    for pos in positions[comp])
                            for comp in components)
    expr |= cnf.Expr.all(cnf.iff(net_vars[h1, net], net_vars[h2, net])
                                    for h1, h2 in board.traces for net in nets)
    expr |= cnf.Expr.all(cnf.at_most_one(grid_vars[comp, hole]
                                                        for comp in components)
                            for hole in holes)
    expr |= cnf.Expr.all(cnf.at_most_one(net_vars[hole, net] for net in nets)
                            for hole in holes)
    expr |= cnf.Expr.all(cnf.implies(position_vars[comp, pos],
                                     net_vars[pos[term],
                                                        terminal_to_net[term]])
                            for comp in components
                            for pos in positions[comp]
                            for term in comp.terminals)
    expr |= cnf.Expr.all(cnf.implies(position_vars[comp, pos],
                                     grid_vars[comp, pos[term]])
                         for comp in components
                         for pos in positions[comp]
                         for term in comp.terminals)

    # Find solutions and map each one back to a mapping of components to
    # positions.
    for sol in cnf.solve(expr):
        mapping = {comp: pos.position 
                     for (comp, pos), var in position_vars.items() if sol[var]}
        # If this fails the "exactly one position" constraint has been
        # violated.
        assert len(mapping) == len(components)
        yield mapping
        
