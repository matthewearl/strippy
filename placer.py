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

_DEBUG = False

class Placement(collections.abc.Mapping):
    """
    A solution yielded by `place`.

    This is a mapping of components to positions, with some utility methods.

    """

    def __init__(self, board, mapping, drilled_holes, jumpers):
        self.board = board
        self._mapping = mapping
        self.drilled_holes = drilled_holes
        self.jumpers = jumpers

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
        print("Drilled: {}".format(self.drilled_holes))
        print("Jumpers: {}".format(self.jumpers))

class _Link():
    """
    A link is a conductive element between two holes.

    It's an abstraction of the concept of jumpers and traces used when
    constructing continuity constraints.

    Attributes:
        h1: The coordinates of the first hole.
        h2: The coordinates of the second hole.
        pres_var: Variable indicating whether the link is present.

    """

    def __init__(self, h1, h2, pres_var):
        if h2 < h1:
            h1, h2 = h2, h1
        self.h1, self.h2 = h1, h2
        self.pres_var = pres_var 

    def __repr__(self):
        return "_Link({!r}, {!r}, {!r})".format(
                                               self.h1, self.h2, self.pres_var)

class _Jumper():
    """
    Represents a jumper.

    A jumper is a conductive horizontal or vertical link between two holes. It
    also occupies the space between those holes.

    Attributes:
        h1: The coordinates of the first hole. This must be to the left of (in
            the case of a horizontal link) or above (in the case of a vertical
            link) the second hole.
        h2: The coordinates of the second hole.
        pres_var: Variable indicating whether the jumper is present.

    """

    def __init__(self, h1, h2):
        assert h1[0] == h2[0] or h1[1] == h2[1]
        assert h1 < h2

        self.h1 = h1
        self.h2 = h2
        self.pres_var = wff.Var("{}->{} jumper".format(h1, h2))
        self.occupies = self._get_occupies()

    def _get_occupies(self):
        if h2[0] - h1[0] == 0:
            assert h1[1] < h2[1]
            inc = 0, 1
        elif h2[1] - h2[1] == 0:
            assert h1[0] < h2[0]
            inc = 1, 0
        else:
            assert False

        def gen_coords():
            h = h1
            while h != h2:
                yield h
                h = h[0] + inc[0], h[1] + inc[1]

        return set(gen_coords())

    @classmethod
    def gen_jumpers(cls, board):
        """Generate valid jumpers for a board."""

        def gen_all():
            for hole in board.holes:
                for length in range(1, max_jumper_length + 1):
                    yield hole, (hole[0] + length, hole[1])
                    yield hole, (hole[0], hole[1] + length)

        return (cls(h1, h2) for h1, h2 in gen_all() if h2 in board.holes)

def place(board, components, nets, *,
          allow_drilled=False, max_jumper_length=0):
    """
    Place components on a board, according to a net list.

    board: The board to place components on. A subclas of `component.Board`. 
    components: Iterable of components to place on the board. Each component is
        subclass of `component.Component`.
    nets: Iterable of nets. Each net is a set of terminals that are to be
        condutively connected.
    allow_drilled: If set, solutions may contain drilled out holes. Traces that
        are connected to drilled out holes are considered to not conduct.
    max_jumper_length: Maximum length of conductive jumper links.

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

        # Enforce that at most one component/jumper can occupy a space.
        jumpers_that_occupy_space = {s:
                                       [j for j in jumpers if s in j.occupies]}

        one_component_per_space = cnf.Expr.all(
                 cnf.at_most_one(
                            {occ[c, s] for c in components} |
                            {j.pres_var for j in jumpers_that_occupy_space[s]})
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
        neighbours = {h1: [(l.h2, l.pres_var) for l in links if h1 == l.h1]
                                                       for h1 in board.holes} |
                     {h2: [(l.h1, l.pres_var) for l in links if h2 == l.h2]
                                                       for h2 in board.holes}

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

        # Generate constraints to enforce the definition of `term_conn`. A hole
        # is connected to a particular terminal iff one of its neighbours is
        # connected to the terminal or the terminal is in this hole. The first
        # expression handles the forward implication, whereas the second
        # expression handles the converse.
        term_conn_constraints = wff.to_cnf(
            wff.for_all(
                    term_conn[net[0], h].iff(
                        wff.exists(
                                  wff.add_var(term_conn[net[0], n] & link_pres)
                                           for n, link_pres in neighbours[h]) |
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
        non_zero_term_dist_constraints = wff.to_cnf(
                wff.for_all(
                    term_dist[h, i].iff(
                        wff.for_all(
                            wff.add_var(term_dist[n, i - 1] | ~link_pres)
                                           for n, link_pres in neighbours[h]) &
                        term_dist[h, i - 1])
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

    # Make jumpers, and their associated links.
    jumpers = [_Jumper(h1, h2) in _Jumper.gen_jumpers(board)]
    jumper_links = [_Link(j.h1, j.h2, j.pres_var))
                                                    for h1, h2 in gen_jumpers()
                                                    if h2 in board.holes]

    # Make links for each trace.
    trace_links = [_Link(*l, Var("trace {} link".format(l)))
                                                         for l in board.traces]

    # Make variables to indicate holes which have been drilled out.
    drilled = {h: wff.Var("{} drilled".format(h)) for h in board.holes}

    # Add a constraint to enforce the following: A trace link is present iff
    # neither of the holes it is connected to are drilled.
    drilled_link_constraints = wff.to_cnf(
        wff.for_all(l.pres_var.iff(~drilled[l.h1] & ~drilled[l.h2])
                                                               for l in links))

    links = jumper_links + trace_links

    # If drilling is not allowed, then force drilled[h] to be false for all
    # holes `h`.
    if not allow_drilled:
        drilled_link_constraints |= wff.to_cnf(
                                wff.for_all(~drilled[h] for h in board.holes))

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
        drilled_holes = {h for h in board.holes if sol[drilled[h]]}
        jumpers = {(l.h1, l.h2) for l in jumper_links if sol[l.pres_var]}

        # If this fails the "exactly one position" constraint has been
        # violated.
        assert len(mapping) == len(components)
        yield Placement(board, mapping, drilled_holes, jumpers)


