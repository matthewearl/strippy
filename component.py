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
Component and board class definitions.

"""

__all__ = (
    'Board',
    'Component',
    'LeadedComponent',
    'StripBoard',
    'Terminal',
)

import abc

class Board():
    """
    Base class for a grid-based prototyping board.

    Attributes:
        size: (width, height) pair giving the width and height of the board in
            terms of the number of holes in either dimension.
        holes: Set of (x, y) pairs indicating the coordinates of holes in the
            board: If a pair (x, y) is in the set then the board has a hole at
            this position.
        strips: A list of lists of holes that are conductively connected. The
            ordering of each list indicates connectedness, in that if the kth
            element of a strip is drilled out then elements i and j are
            considered disconnected for all i < k, j > k. As such a given hole
            can only be connected to up to two other holes, so some board
            topologies (eg. T junctions) cannot be represented.

    """
    def __init__(self, size, holes, strips):
        """
        Initialize the object.

        Arguments initialize the object's attributes.

        """
        self.size = tuple(size)
        self.holes = set(holes)
        self.strips = set(tuple(strip) for strip in strips)

        # Check each hole is within the bounds of the board.
        if not all(0 <= x < size[0] and 0 <= y < size[1] for (x, y) in
                   self.holes):
            raise ValueError

        # Check all the strip elements are located on holes.
        if not all(h in self.holes for strip in self.strips for h in strip):
            raise ValueError

class StripBoard(Board):
    """
    A rectangular board in which holes are connected if and only if they are in
    the same row.

    """
    def __init__(self, size):
        holes = [(x, y) for y in range(size[1]) for x in range(size[0])]
        strips = [[(x, y) for x in range(size[0])] for y in range(size[1])]
        super().__init__(size, holes, strips)

class Terminal():
    """
    Object to represent a terminal of given component object.

    """
    pass

class Component(metaclass=abc.ABCMeta):
    """
    Object to represent a component.

    A component has a number of terminals, and a component can be placed in
    numerous positions on a given board.

    A position is defined by a mapping of the component's terminals to (x, y)
    coordinates. See methods for more information.

    """
    def __init__(self, terminals):
        self.terminals = list(terminals)
    
    @abc.abstractmethod
    def get_relative_positions(self):
        """
        Get relative positions for this component.

        Each position is a dict mapping the component's terminals to (x, y)
        positions, and the first terminal always maps to (0, 0).

        This function assumes an infinite grid of holes is available.

        """
        raise NotImplemented

    def get_positions(self, board):
        """
        Get absolute positions for this component, given a board.

        Each position is a dict mapping the component's terminals to (x, y)
        positions. Each (x, y) position is a hole in the board.

        """
        for hx, hy in board.holes:
            for rel_pos in self.get_relative_positions():
                abs_pos = {terminal: (hx + x, hy + y)
                            for terminal, (x, y) in rel_pos.items()}

                if all(v in board.holes for v in abs_pos.values()):
                    yield abs_pos

class LeadedComponent(Component):
    """
    Class for leaded components.

    For example, through-hole resistors, diodes, capacitors.

    """

    def __init__(self, max_length, *,
                 allow_vertical=True,
                 allow_horizontal=True):
        terminals = (Terminal(), Terminal())

        self._max_length = max_length
        self._allow_horizontal = allow_horizontal
        self._allow_vertical = allow_vertical

        super().__init__(terminals)

    def get_relative_positions(self):
        for length in range(1, self._max_length + 1):
            if self._allow_vertical:
                yield {self_terminals[0]: (0, 0),
                       self.terminals[1]: (length, 0)}
                yield {self.terminals[1]: (0, 0),
                       self.terminals[0]: (length, 0)}
            if self._allow_horizontal:
                yield {self.terminals[0]: (0, 0),
                       self.terminals[1]: (0, length)}
                yield {self.terminals[1]: (0, 0),
                       self.terminals[0]: (0, length)}

