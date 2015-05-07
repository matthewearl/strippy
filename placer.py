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
import wff

_DEBUG = True

class Placement(collections.abc.Mapping):
    """
    A solution yielded by `place`.

    This is a mapping of components to positions, with some utility methods.

    """

    def __init__(self, board, mapping, drilled_holes):
        self.board = board
        self._mapping = mapping
        self._drilled_holes = drilled_holes

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
        print("Drilled: {}".format(self._drilled_holes))

class _Link():
    """
    A link is a conductive element between two holes.

    It is represented by the unordered set of the two holes that it goes
    between.

    """

    def __init__(self, h1, h2):
        if h2 < h1:
            h1, h2 = h2, h1
        self.h1, self.h2 = h1, h2
        
    def __eq__(self, other):
        return (self.h1, self.h2) == (other.h1, other.h2)

    def __hash__(self):
        return hash((self.h1, self.h2))

def place(board, components, nets, allow_drilled=False):
    """
    Place components on a board, according to a net list.

    board: The board to place components on. A subclas of `component.Board`. 
    components: Iterable of components to place on the board. Each component is
        subclass of `component.Component`.
    nets: Iterable of nets. Each net is a set of terminals that are to be
        condutively connected.
    allow_drilled: If set, solutions may contain drilled out holes. Traces that
        are connected to drilled out holes are considered to not conduct.

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
        occ = {(c, s): wff.Var("{} occ {}".format(c, s))
               for s in board.spaces for c in components}

        # Generate constraints to enforce the definition of `occ`. occ[s, c] is
        # true iff there is a position `p` for `c` which covers `s` such that
        # comp_pos[c, p] is true. The first line handles the forward
        # implication, and the second the converse.
        positions_which_occupy = {(c, s): [p for p in positions[c]
                                                            if s in p.occupies]
                                  for c in components
                                  for s in board.spaces}
        occ_constraints = wff.to_cnf(
                wff.for_all(occ[c, s].iff(wff.exists(comp_pos[c, p]
                                        for p in positions_which_occupy[c, s]))
                    for c in components
                    for s in board.spaces))

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
        # Produce a dict which maps a terminal `t` and a hole `h` to a list of
        # positions of t.component which have `t` in `h`. Used a couple of
        # times in this function.
        positions_which_have_term_in = {
            (t, h): [p for p in positions[c] if p.terminal_positions[t] == h]
                    for c in components
                    for t in c.terminals
                    for h in board.holes}

        # Produce an adjacency dict for the electrical continuity graph implied
        # by board.holes and board.traces.
        neighbours = {h1: [h2 for h2 in board.holes if _Link(h1, h2) in links]
                                                         for h1 in board.holes}

        # Make internal variables to indicate whether a hole is connected to a
        # particular terminal. Defined for all holes, and the first terminal in
        # each net. (This is sufficient for validating (dis)continuity
        # constraints.
        term_conn = {(n[0], h): wff.Var("{} conn {}".format(n[0], h))
                        for n in nets
                        for h in board.holes}

        # Also make internal variables to indicate the minimum distance of each
        # hole to the nearest terminal. term_dist[h, i] is true iff there is no
        # path of length `i` or less from hole `h` to a head terminal. (A head
        # terminal is a terminal that is at the start of its net.)
        #
        # In other words, term_dist[h, *] is a unary encoding of the distance
        # to the nearest head terminal. Holes which are not connected to a
        # terminal will take the maximum value len(board.holes). Conversely,
        # holes which are connected will take a value < len(board.holes).
        term_dist = {(h, i): wff.Var("{} dist {}".format(h, i))
                        for h in board.holes
                        for i in range(len(board.holes))}

        # Internal variables are needed for the expression link_pres[h, n] ^
        # term_conn[t, n] for all head terminals t, all holes h, and all
        # neighbours n of each hole. 
        neighbour_and_term_conn = {(net[0], h, n):
               tseitin_and(link_pres[_Link(h, n)], term_conn[t, n])
                    for net in nets
                    for h in board.holes
                    for n in neighbours[h]}

        # Pull out the cnf exprs from the above, and just leave the vars as
        # values.
        neighbour_and_term_conn_constraints = cnf.Expr.all(
                        expr for var, expr in neighbour_and_term_conn.values())
        neighbour_and_term_conn = {k: var for k, (var, expr) in
                                               neighbour_and_term_conn.items()}

        # Generate constraints to enforce the definition of `term_conn`. A hole
        # is connected to a particular terminal iff one of its neighbours is
        # connected to the terminal or the terminal is in this hole. The first
        # expression handles the forward implication, whereas the second
        # expression handles the converse.
        term_conn_constraints = wff.to_cnf(
            wff.for_all(
                    term_conn[net[0], h].iff(
                        wff.exists(term_conn[net[0], n]
                                                      for n in neighbours[h]) |
                        wff.exists(comp_pos[net[0].component, p]
                             for p in positions_which_have_term_in[net[0], h]))
                    for net in nets
                    for h in board.holes))
        if _DEBUG:
            print("Term conn constraints: {}".format(
                      term_conn_constraints.stats))

        # Add constraints to enforce the definition of `term_dist[h, 0]`, for
        # all holes `h`. term_hist[h, 0] is false iff a component is positioned
        # such that a head terminal is in hole `h`. The first statement
        # expresses the forward implication, and the second statement expresses
        # the converse.
        zero_term_dist_constraints = wff.to_cnf(
                wff.for_all(
                    (~term_dist[h, 0]).iff(
                        wff.exists(comp_pos[net[0].component, p]
                             for net in nets
                             for p in positions_which_have_term_in[net[0], h]))
                    for h in board.holes))
        if _DEBUG:
            print("Zero term dist constraints: {}".format(
                      zero_term_dist_constraints.stats))

        # Add constraints to enforce the definition of `term_dist[h, i]`, for
        # 0 < 1 < |holes|. term_dist[h, i] is true iff for each neighbour `n`
        # term_dist[n, i - 1] is true. The first statement expresses the
        # forward implication, and the second statement expresses the converse.
        #@@@ Integrate link_pres[] into the below
        non_zero_term_dist_constraints = wff.to_cnf(
                wff.for_all(
                    term_dist[h, i].iff(
                        wff.for_all(
                            term_dist[n, i - 1] for n in [h] + neighbours[h]))
                    for h in board.holes
                    for i in range(1, len(board.holes))))
        if _DEBUG:
            print("Non-zero term dist contraints: {}".format(
                      non_zero_term_dist_constraints.stats))

        # Add constraints which ensure any terminals are connected to the
        # terminal that's at the head of its net.
        def term_to_net(t):
            l = [net for net in nets if t in net]
            assert len(l) == 1, "Terminal is not in exactly one net"
            return l[0]
        head_term = {t: term_to_net(t)[0]
                            for c in components
                            for t in c.terminals}
        net_continuity_constraints = wff.to_cnf(
            wff.for_all(comp_pos[c, p] >> term_conn[head_term[t], h]
                                  for h in board.holes
                                  for c in components
                                  for t in c.terminals
                                  for p in positions_which_have_term_in[t, h]))
        if _DEBUG:
            print("Net continuity constraints: {}".format(
                      net_continuity_constraints.stats))

        # Add constraints which ensure that no hole is part of more than one
        # net, and if its disconnected from all nets, then it can be part of no
        # net.
        net_discontinuity_constraints = cnf.Expr.all(
                          cnf.at_most_one(
                              {term_conn[net[0], h] for net in nets} |
                              {term_dist[h, len(board.holes) - 1]})
                    for h in board.holes)
        if _DEBUG:
            print("Net discontinuity constraints: {}".format(
                      net_discontinuity_constraints.stats))

        # Return all of the above.
        return (term_conn_constraints |
                neighbour_and_term_conn_constraints |
                zero_term_dist_constraints |
                non_zero_term_dist_constraints |
                net_discontinuity_constraints |
                net_continuity_constraints)

    # Make variables to indicate whether a component is in a particular
    # position. Assignments for these variables will be used to produce
    # placements.
    comp_pos = {(comp, pos): wff.Var("comp {} in pos {}".format(comp, pos))
                    for comp in components
                    for pos in positions[comp]}

    # Constrain the `comp_pos` variables such that a component must be in
    # exactly one position.
    one_pos_per_comp = cnf.Expr.all(cnf.exactly_one(comp_pos[comp, pos]
                                               for pos in positions[comp])
                                    for comp in components)

    # Make variables to indicate holes which have been drilled out.
    drilled = {h: cnf.Var("{} drilled".format(h)) for h in board.holes}

    # Create `links`, using `board.traces`. This is used when building the
    # continuity constraints rather than using `board.traces` directly. In
    # future, `links` will be extended to include other possible conductive
    # elements (eg. jumper wires).
    links = [_Link(l) for l in board.traces]
    
    # Make internal variables which indicate which links are present in the
    # solution.
    link_pres = {l: cnf.Var("{} present".format(l)) for l in links}

    # Enforce the relationship between `drilled` and `link_pres`.
    hole_to_links = {h: {_Link(tr) for tr in board.traces if h in tr} for h in
                     board.holes}
    drilled_link_constraints = cnf.Expr(
        cnf.Clause({cnf.Term(drilled[h], negated=True),
                    cnf.Term(link_pres[l], negated=True)})
                for h in board.holes
                for l in hole_to_links[h])
    drilled_link_constraints |= cnf.Expr(
        cnf.Clause({cnf.Term(link_pres[l]) for l in hole_to_links[h]} |
                   {cnf.Term(drilled[h])})
                for h in board.holes)

    # Combine all the constraints into a single expression.
    expr = (one_pos_per_comp | 
            drilled_link_constraints |
            physical_constraints() |
            continuity_constraints())

    if _DEBUG:
        print(expr.stats)
        print("Solving!")

    # Find solutions and map each one back to a Placement.
    for sol in cnf.solve(expr):
        if _DEBUG:
            print("Done")
            for var, val in sol.items():
                print("{} {}".format("~" if not val else " ", var))
        mapping = {comp: pos
                     for (comp, pos), var in comp_pos.items() if sol[var]}
        drilled_holes = {h for h in holes if sol[drilled_holes[h]]}

        # If this fails the "exactly one position" constraint has been
        # violated.
        assert len(mapping) == len(components)
        yield Placement(board, mapping, drilled_holes)


