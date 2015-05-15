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
    'DualInlinePackage',
    'LeadedComponent',
    'Position',
    'StripBoard',
    'Terminal',
)

import abc

class Position():
    """
    A position represents the position of a component on a board.

    Attributes:
        occupies: Space occupied by the component in this position. This is a
            set of (x, y) coordinates, each representing a cell that is
            occupied.
        terminal_positions: Mapping of terminals to their positions.

    """

    def __init__(self, occupies, terminal_positions):
        self.occupies = set(occupies)
        self.terminal_positions = dict(terminal_positions)

    def __add__(self, offset):
        """
        Return a position that is a translation of this position.

        offset: x, y offset.

        """
        x_offs, y_offs = offset
        offset_occupies = {(x + x_offs, y + y_offs)
                                                   for (x, y) in self.occupies}
        offset_terminal_positions = {t: (x + x_offs, y + y_offs)
                                        for t, (x, y) in
                                               self.terminal_positions.items()}

        return Position(offset_occupies, offset_terminal_positions) 

    def rotate(self, angle):
        """
        Rotate a position counter-clockwise.

        Angle is the number of 90 degree CCW rotations to perform.

        """

        def rot_point(p):
            x, y = p
            if angle == 0:
                return x, y
            if angle == 1:
                return y, -x
            if angle == 2:
                return -x, -y
            if angle == 3:
                return -y, x

        rotated_occupies = {rot_point(p) for p in self.occupies}
        rotated_terminal_positions = {t: rot_point(p) for t, p in
                                               self.terminal_positions.items()}
        return Position(rotated_occupies, rotated_terminal_positions)

    def fits(self, board):
        """
        Indicate whether this position fits on the board.

        Ie. check that there are holes for the terminals, and check that there
        is a space on the board for each cell that the component occupies.

        """
        return (set(self.terminal_positions.values()) <= board.holes and
                set(self.occupies) <= board.spaces)

class Board():
    """
    Base class for a grid-based prototyping board.

    Attributes:
        holes: Set of (x, y) pairs indicating the coordinates of holes in the
            board: If a pair (x, y) is in the set then the board has a hole at
            this position.
        spaces: Coordinates of cells that have space for components to be
            placed: If a pair (x, y) is in the set then the board has room for
            a component at grid cell (x, y).
        traces: A list of pairs of holes that are conductively connected.

    """
    def __init__(self, holes, spaces, traces):
        """
        Initialize the object.

        Arguments initialize the object's attributes.

        """
        self.holes = set(holes)
        self.traces = set(tuple(sorted(hole_pair)) for hole_pair in traces)
        self.spaces = set(spaces)

        # Check all holes in the traces are holes in the board.
        if not {h for t in self.traces for h in t} <= self.holes:
            raise ValueError

class StripBoard(Board):
    """
    A rectangular board in which holes are connected if and only if they are in
    the same row.

    """
    def __init__(self, size):
        holes = [(x, y) for y in range(size[1]) for x in range(size[0])]
        traces = [((x, y), (x + 1, y))
                    for y in range(size[1]) for x in range(size[0] - 1)]
        spaces = holes
        super().__init__(holes, spaces, traces)

class Terminal():
    """
    Object to represent a terminal of given component object.

    Terminals of distinct components must not be equal. Ie. c1 != c2 => t1 !=
    t2, for all components c1, c2, t1 a terminal in c1, t2 a terminal in c2.

    Attributes:
        label: Label used for displaying this terminal. The terminal will
               always be displayed in the context of its component, so the
               component need not be described here.
    """
    def __init__(self, label):
        self.label = str(label)
        self.component = None

    def _set_component(self, component):
        """
        Set the component. It should only be set once, and only by
        Component.__init__().

        A single terminal cannot belong to multiple components.

        """
        assert self.component is None
        self.component = component

    def __str__(self):
        return "{}[{}]".format(self.component.label, self.label)

class Component(metaclass=abc.ABCMeta):
    """
    Object to represent a component.

    A component has a number of terminals, and a component can be placed in
    numerous positions on a given board.

    A position is defined by a mapping of the component's terminals to (x, y)
    coordinates. See methods for more information.

    Attributes:
        label: Label used for displaying thie component.
        terminals: Iterable of terminals tht belong to this component.

    """
    def __init__(self, label, terminals, color="#008000"):
        self.label = str(label)
        self.terminals = tuple(terminals)
        for terminal in self.terminals:
            terminal._set_component(self)
        self.color = color
    
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
        for hole_pos in board.holes:
            for rel_pos in self.get_relative_positions():
                abs_pos = rel_pos + hole_pos
                if abs_pos.fits(board):
                    yield abs_pos

    def __str__(self):
        return self.label

class LeadedComponent(Component):
    """
    Class for leaded components.  
    For example, through-hole resistors, diodes, capacitors.

    """

    def __init__(self, label, max_length, *,
                 allow_vertical=True,
                 allow_horizontal=True):
        terminals = (Terminal(1), Terminal(2))

        self._max_length = max_length
        self._allow_horizontal = allow_horizontal
        self._allow_vertical = allow_vertical

        super().__init__(label, terminals)

    def get_relative_positions(self):
        for length in range(1, self._max_length + 1):
            if self._allow_vertical:
                yield Position({(0, y) for y in range(length + 1)},
                               {self.terminals[0]: (0, 0),
                                self.terminals[1]: (0, length)})
                yield Position({(0, y) for y in range(-length, 1)},
                               {self.terminals[0]: (0, 0),
                                self.terminals[1]: (0, -length)})
            if self._allow_horizontal:
                yield Position({(x, 0) for x in range(length + 1)},
                               {self.terminals[0]: (0, 0),
                                self.terminals[1]: (length, 0)})
                yield Position({(x, 0) for x in range(-length, 1)},
                               {self.terminals[0]: (0, 0),
                                self.terminals[1]: (-length, 0)})

class DualInlinePackage(Component):
    """
    Class for dual-inline package (aka. DIP) components.

    """

    def __init__(self, label, num_terminals, *, row_spacing=3,
                 color="#808080"):
        if num_terminals % 2 != 0:
            raise ValueError
        terminals = tuple(Terminal(i + 1) for i in range(num_terminals))

        self._row_spacing = row_spacing
        self._length = num_terminals // 2

        super().__init__(label, terminals, color=color)

    def get_relative_positions(self):
        # Construct a vertically oriented position, with terminal number
        # initially increasing with Y coordinate. As per convention, terminal
        # numbering is clockwise.
        occupies = {(x, y) for x in range(self._row_spacing + 1)
                            for y in range(self._length)}
        left_positions = {t: (0, i)
                          for i, t in enumerate(self.terminals[:self._length])}
        right_positions = {t: (self._row_spacing, self._length - i - 1)
                          for i, t in enumerate(self.terminals[self._length:])}
        pos = Position(occupies, 
                       dict(left_positions.items() | right_positions.items()))

        # Rotate the position through the 4 angles.
        for angle in range(4):
            yield pos.rotate(angle)

