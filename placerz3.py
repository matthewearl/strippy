# Copyright (c) 2015, 2018 Matthew Earl
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
    'Placement',
)


import collections

import z3


_DEBUG = True

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
        self.pres_var = z3.Bool("{}->{} jumper".format(h1, h2))
        self.occupies = self._get_occupies()

    def _get_occupies(self):
        if self.h2[0] - self.h1[0] == 0:
            assert self.h1[1] < self.h2[1]
            inc = 0, 1
        elif self.h2[1] - self.h1[1] == 0:
            assert self.h1[0] < self.h2[0]
            inc = 1, 0
        else:
            assert False

        def gen_coords():
            h = self.h1
            while h != self.h2:
                yield h
                h = h[0] + inc[0], h[1] + inc[1]
            yield h

        return set(gen_coords())

    @classmethod
    def gen_jumpers(cls, board, max_jumper_length):
        """Generate valid jumpers for a board."""

        def gen_all():
            for hole in board.holes:
                for length in range(1, max_jumper_length + 1):
                    yield hole, (hole[0] + length, hole[1])
                    yield hole, (hole[0], hole[1] + length)

        def is_between(h1, h2, h):
            """Check if `h` is between `h1` and `h2`"""
            if h1[0] == h2[0]:
                return (h[0] == h1[0] and
                               min(h1[1], h2[1]) <= h[1] <= max(h1[1], h2[1]))
            if h1[1] == h2[1]:
                return (h[1] == h1[1] and 
                               min(h1[0], h2[0]) <= h[0] <= max(h1[0], h2[0]))
            assert False, "Jumper is neither horizontal nor vertical"

        neighbours = collections.defaultdict(set)
        for h1, h2 in board.traces:
            neighbours[h1].add(h2)
            neighbours[h2].add(h1)

        def is_redundant(h1, h2):
            # Indicate if a potential jumper is superceded by traces.
            # This is the case if there are traces which follow the path of the
            # jumper, and there are no branches along this path.

            # Starting from `h1`, step through neighbours of the current hole.
            h = h1
            prev_h = None
            while h != h2:
                # Search for neighbours that are between h1 and h2. There
                # should be at most one (otherwise an unsupported board layout
                # has been used).
                next_hs = [n for n in neighbours[h] if
                                        is_between(h1, h2, n) and 
                                        n != prev_h]
                if len(next_hs) == 0:
                    return False
                if len(next_hs) > 1:
                    assert False, "{} has multiple neighbours between {} " \
                                  "and {}".format(h, h1, h2)
                next_h = next_hs[0]

                # Check there are no branches at this point in the link.
                if (prev_h is not None and
                    next_h is not h2 and 
                    neighbours[h] != {prev_h, next_h}):
                    return False

                prev_h = h
                h = next_h
                next_h = None
            return True 

        return (cls(h1, h2) for h1, h2 in gen_all()
                             if h2 in board.holes and not is_redundant(h1, h2))


def sum_bool(l):
    return z3.Sum([z3.If(b, 1, 0) for b in l])


def place(board, components, nets, *,
          allow_drilled=False, max_jumper_length=0,
          max_drilled=None, max_jumpers=None):
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
    max_drilled: Maximum number of drilled holes in the solution. None implies
        unbounded.
    max_jumpers: Maximum number of jumpers in the solution. None implies
        unbounded.

    Yields:
        Placements which satify the input constraints.

    """

    # Unpack arguments in case the caller provided a generator (or other
    # one-time iterable), so they can be re-iterated and subscripted in this
    # function.
    nets = [list(net) for net in nets]
    components = list(components)

    terminal_to_net_idx = {t: net_idx for net_idx, net in enumerate(nets)
                                      for t in net}

    # Position objects that represent the same position may have different
    # hashes (their hash function is the default id based implementation).
    # 
    # Allow the positions to be hashed correctly by using only one Position for
    # each component position within this function.
    positions = {c: list(c.get_positions(board)) for c in components}

    holes = list(board.holes)
    spaces = list(board.spaces)

    solver = z3.Solver()

    # Make jumpers.
    if max_jumpers == 0:
        max_jumper_length = 0
    jumpers = [j for j in _Jumper.gen_jumpers(board, max_jumper_length)]

    # Make position vars to indicate which position each component is in.
    pos_vars = {c: z3.Int("{} pos".format(c)) for c in components}
    solver.append([v >= 0 for v in pos_vars.values()])
    solver.append([v < len(positions[c]) for c, v in pos_vars.items()])

    # At most one component or jumper can occupy a single space.
    space_occupied = collections.defaultdict(list)
    for c in components:
        for pos_idx, pos in enumerate(positions[c]):
            for s in pos.occupies:
                space_occupied[s].append(pos_vars[c] == pos_idx)
    for j in jumpers:
        for s in j.occupies:
            space_occupied[s].append(j.pres_var)
    for l in space_occupied.values():
        solver.add(sum_bool(l) <= 1)

    # Make net vars, which indcate which net a particular hole belongs to.
    net_vars = {h: z3.Int("{} net".format(h)) for h in holes}
    solver.append([v >= -1 for v in net_vars.values()])
    solver.append([v < len(nets) for v in net_vars.values()])

    # Make drilled vars, which indicate if a particular hole is drilled.
    drilled_vars = {h: z3.Bool("{} drilled".format(h)) for h in holes}

    # The component being in the given position implies that the
    # holes corresponding with the terminals are on the net associated
    # with the terminal.
    solver.append([z3.Implies(pos_var == pos_idx,
                              net_vars[pos.terminal_positions[t]] ==
                                terminal_to_net_idx[t])
                    for c, pos_var in pos_vars.items()
                    for pos_idx, pos in enumerate(positions[c])
                    for t in c.terminals])

    # Holes that are joined by a trace are on the same net.
    solver.append([z3.Implies(z3.Not(z3.Or(drilled_vars[h1], drilled_vars[h2])),
                              net_vars[h1] == net_vars[h2])
                    for h1, h2 in board.traces])

    # Holes that are joined by a jumper are on the same net.
    solver.append([z3.Implies(z3.And(z3.Not(drilled_vars[j.h1]),
                                     z3.Not(drilled_vars[j.h2]),
                                     j.pres_var),
                              net_vars[j.h1] == net_vars[j.h2])
                    for j in jumpers])

    # Drilled holes are not on a net.
    solver.append([z3.Implies(drilled_vars[h], net_vars[h] == -1)
                    for h in holes])

    neighbours = collections.defaultdict(list)
    for j in jumpers:
        jumper_not_drilled = z3.Not(z3.Or(drilled_vars[j.h1],
                                          drilled_vars[j.h2]))
        neighbours[j.h1].append((j.h2, z3.And(j.pres_var, jumper_not_drilled)))
        neighbours[j.h2].append((j.h1, z3.And(j.pres_var, jumper_not_drilled)))
    for h1, h2 in board.traces:
        trace_not_drilled = z3.Not(z3.Or(drilled_vars[h1], drilled_vars[h2]))
        neighbours[h1].append((h2, trace_not_drilled))
        neighbours[h2].append((h1, trace_not_drilled))
    term_dist = {h: z3.Int("Term dist {}".format(h)) for h in board.holes}

    # Each hole must have a neighbour that has a lower term dist, unless the
    # term dist of the hole is 0 or len(board.holes).
    solver.append([z3.Or(z3.Or(*(z3.And(pres, term_dist[h] > term_dist[n])
                                 for n, pres in neighbours[h])),
                         term_dist[h] == len(board.holes),
                         term_dist[h] == 0)
                    for h in board.holes])

    # Min / max constraints on term dist
    solver.append([term_dist[h] >= 0 for h in board.holes])
    solver.append([term_dist[h] <= len(board.holes) for h in board.holes])

    # A hole has a term dist of 0 iff there is a component with its head
    # terminal in the hole.
    head_terminal_conditions = collections.defaultdict(list)
    for head_term, *_ in nets:
        comp = head_term.component
        pos_var = pos_vars[comp]
        for pos_idx, pos in enumerate(positions[comp]):
            h = pos.terminal_positions[head_term]
            head_terminal_conditions[h].append(pos_var == pos_idx)
    solver.append([z3.Or(*head_terminal_conditions[h]) == (term_dist[h] == 0)
                   for h in board.holes])

    # A hole is on net -1 iff its term dist is == len(board.holes)
    solver.append([(net_vars[h] == -1) == (term_dist[h] == len(board.holes))
                   for h in board.holes])

    # Constraint on number of drilled holes.
    solver.add(sum_bool(drilled_vars.values()) <= max_drilled)

    # Constraint on the number of jumpers
    solver.add(sum_bool(j.pres_var for j in jumpers) <= max_jumpers)

    if _DEBUG:
        print(solver)
        print("Solving!")

    # Find solutions and map each one back to a Placement.
    if solver.check() == z3.sat:
        model = solver.model()
        if _DEBUG:
            print(model)
        drilled_holes = {h for h, v in drilled_vars.items() if model[v]}
        jumpers = {(j.h1, j.h2) for j in jumpers if model[j.pres_var]}
        mapping = {c: positions[c][model[v].as_long()]
                        for c, v in pos_vars.items()}
        from pprint import pprint
        pprint(list(sorted((h, model[v]) for h, v in term_dist.items())))

        assert len(mapping) == len(components)
        yield Placement(board, mapping, drilled_holes, jumpers)
