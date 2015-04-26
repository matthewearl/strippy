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
This module contains routines finding placements for components on a circuit
board.

"""

__all__ = (
    'place',
    'Placement',
)

import collections.abc

import cnf

_DEBUG = False

class Placement(collections.abc.Mapping):
    """
    A solution yielded by `place`.

    This is a mapping of components to positions, with some utility methods.

    """

    def __init__(self, board, mapping):
        self.board = board
        self._mapping = mapping

    def __getitem__(self, key):
        return self._mapping[key]

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)

    def print_solution(self):
        comps = list(sorted(self._mapping.keys(),
                            key=(lambda comp: comp.label)))
        for comp in comps:
            pos = self[comp]
            print("{}: {}".format(comp.label,
                ", ".join("{}:{}".format(terminal.label,
                                         pos.terminal_positions[terminal])
                                         for terminal in comp.terminals)))

def place(board, components, nets):
    """
    Place components on a board, according to a net list.

    board: The board to place components on. A subclas of `component.Board`. 
    components: Iterable of components to place on the board. Each component is
        subclass of `component.Component`.
    nets: Iterable of nets. Each net is a set of terminals that are to be
        condutively connected.

    Yields:
        Placements which satify the input constraints.

    """

    # Unpack arguments in case the caller provided a generator (or other
    # one-time iterable), so they can be re-iterated and subscripted in this
    # function.
    nets = [list(net) for net in nets]
    components = list(components)

    # Position objects that represent the same position may have different
    # hashes (their hash function is the default id based implementation).
    # 
    # Allow the positions to be hashed correctly by using only one Position for
    # each component position within this function.
    positions = {c: list(c.get_positions(board)) for c in components}

    def physical_constraints():
        """
        Produce a CNF expression to enforce physical constraints.

        Ie. There must not be multiple components that occupy a given space.

        """
        # Make internal variables to determine whether a given component is in
        # a particular space.
        occ = {(c, s): cnf.Var("{} occ {}".format(c, s))
               for s in board.spaces for c in components}

        # Generate constraints to enforce the definition of `occ`. occ[s, c] is
        # true iff there is a position `p` for `c` which covers `s` such that
        # comp_pos[c, p] is true. The first line handles the forward
        # implication, and the second the converse.
        positions_which_occupy = {(c, s): [p for p in positions[c]
                                                            if s in p.occupies]
                                  for c in components
                                  for s in board.spaces}
        occ_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(occ[c, s], negated=True)} |
                       {cnf.Term(comp_pos[c, p])
                                        for p in positions_which_occupy[c, s]})
                    for c in components
                    for s in board.spaces)
        occ_constraints |= cnf.Expr(
            cnf.Clause({cnf.Term(comp_pos[c, p], negated=True),
                        cnf.Term(occ[c, s])})
                    for c in components
                    for s in board.spaces
                    for p in positions_which_occupy[c, s])

        # Enforce that at most one component can occupy a space.
        one_component_per_space = cnf.Expr.all(
                                 cnf.at_most_one(occ[c, s] for c in components)
                    for s in board.spaces)

        # Return all of the above.
        return occ_constraints | one_component_per_space

    def continuity_constraints():
        """
        Produce a CNF expression to enforce electrical continuity constraints.

        Ie. continuity between terminals that are in a common net, and
        discontinuity between terminals that are in different nets.

        """
        # Make internal variables to determine which nodes are reachable from
        # which by paths less than or equal to a given length.
        conn = {(h1, h2, i): cnf.Var("{} conn {} <= {}".format(h1, h2, i))
                        for h1 in board.holes
                        for h2 in board.holes
                        for i in range(len(board.holes))}

        # Create extra entries in the dict which maps to the vars which
        # indicate connectivity by paths of any length. (In a board with N
        # holes, two holes being connected is equivalent to them being
        # connected by a path of length N - 1 or less.
        conn.update({(h1, h2): conn[h1, h2, len(board.holes) - 1]
                                  for h1 in board.holes for h2 in board.holes})

        # Make some more internal variables which indicate whether a terminal
        # is in a particular hole.
        term_hole = {(t, h): cnf.Var("{} in {}".format(t, h))
                        for c in components
                        for t in c.terminals
                        for h in board.holes} 

        # Generate constraints to enforce the definition of `conn` for paths of
        # length 0. Two holes are connected by a path of a length 0 iff they
        # are the same hole.
        zero_length_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(conn[h1, h2, 0], negated=(h1 != h2))})
                    for h1 in board.holes
                    for h2 in board.holes)
                
        # Generate constraints to enforce the definition of `conn` for paths
        # that are not of length 0. Two holes are connected by a path of length
        # <= i iff they are connected by a path of length i - 1, or a neighbour
        # of the first node is connected to the second node by a path of length
        # i - 1. The first line handles the forward implication, and the second
        # the converse.
        neighbours = {h1: [h2 for h2 in board.holes 
                              if (h1, h2) in board.traces or
                                 (h2, h1) in board.traces]
                      for h1 in board.holes}
        non_zero_length_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(conn[h1, h2, i], negated=True),
                        cnf.Term(conn[h1, h2, i - 1])} |
                       {cnf.Term(conn[n, h2, i - 1]) for n in neighbours[h1]})
                    for h1 in board.holes
                    for h2 in board.holes
                    for i in range(1, len(board.holes)))
        non_zero_length_constraints |= cnf.Expr(
            {cnf.Clause({cnf.Term(conn[h1, h2, i - 1], negated=True),
                         cnf.Term(conn[h1, h2, i])})
                    for h1 in board.holes
                    for h2 in board.holes
                    for i in range(1, len(board.holes))} |
            {cnf.Clause({cnf.Term(conn[n, h2, i - 1], negated=True),
                         cnf.Term(conn[h1, h2, i])})
                    for h1 in board.holes
                    for h2 in board.holes
                    for i in range(1, len(board.holes))
                    for n in neighbours[h1]})

        # Generate constraints to enforce the definition of `term_hole`.
        # term_hole[t, h] is true iff there is a position `p` of `c` which
        # places `t` in # `h` such that comp_pos[c, p] is true.
        # comp_pos[c, p] is true. The first line handles the forward
        # implication, and the second the converse.
        positions_which_have_term_in = {
            (t, h): [p for p in positions[c] if p.terminal_positions[t] == h]
                    for c in components
                    for t in c.terminals
                    for h in board.holes}
        term_hole_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(term_hole[t, h], negated=True)} |
                       {cnf.Term(comp_pos[c, p])
                                  for p in positions_which_have_term_in[t, h]})
                    for c in components
                    for t in c.terminals
                    for h in board.holes)
        term_hole_constraints |= cnf.Expr(
            cnf.Clause({cnf.Term(comp_pos[c, p], negated=True),
                        cnf.Term(term_hole[t, h])})
                    for c in components
                    for t in c.terminals
                    for h in board.holes
                    for p in positions_which_have_term_in[t, h])
        
        # Add constraints which ensure each terminal in a net is connected.
        # Just check the first node is connected to all the others.
        # Transitivity and reflexivity of connectedness should guarantee full
        # connectedness.
        net_continuity_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(term_hole[n[0], h1], negated=True),
                        cnf.Term(term_hole[t2, h2], negated=True),
                        cnf.Term(conn[h1, h2])}) 
                    for n in nets
                    for t2 in n[1:]
                    for h1 in board.holes
                    for h2 in board.holes)

        # Add constraints which ensure that terminals in different nets are
        # disconnected. Check all pairs of nets are disconnected, using only
        # the first element.
        net_discontinuity_constraints = cnf.Expr(
            cnf.Clause({cnf.Term(term_hole[n1[0], h1], negated=True),
                        cnf.Term(term_hole[n2[0], h2], negated=True),
                        cnf.Term(conn[h1, h2], negated=True)}) 
                    for idx, n1 in enumerate(nets)
                    for n2 in nets[(idx + 1):]
                    for h1 in board.holes
                    for h2 in board.holes)

        # Return all of the above.
        return (zero_length_constraints |
                non_zero_length_constraints |
                term_hole_constraints |
                net_continuity_constraints |
                net_discontinuity_constraints)
                        
    # Make variables to indicate whether a component is in a particular
    # position. Assignments for these variables will be used to produce
    # placements.
    comp_pos = {(comp, pos): cnf.Var("comp {} in pos {}".format(comp, pos))
                    for comp in components
                    for pos in positions[comp]}


    # Constrain the `comp_pos` variables such that a component must be in
    # exactly one position.
    one_pos_per_comp = cnf.Expr.all(cnf.exactly_one(comp_pos[comp, pos]
                                               for pos in positions[comp])
                                    for comp in components)

    # Combine all the constraints into a single expression.
    expr = one_pos_per_comp | physical_constraints() | continuity_constraints()

    # Find solutions and map each one back to a Placement.
    for sol in cnf.solve(expr):
        if _DEBUG:
            for var, val in sol.items():
                print("{} {}".format("~" if not val else " ", var))
        mapping = {comp: pos
                     for (comp, pos), var in comp_pos.items() if sol[var]}
        # If this fails the "exactly one position" constraint has been
        # violated.
        assert len(mapping) == len(components)
        yield Placement(board, mapping)
        

