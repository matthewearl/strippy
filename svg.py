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
Module to output SVG files showing circuit board placements.

"""


__all__ = (
    'print_svg',
)

import sys

_LINE_WIDTH = 1.
_GRID_CELL_SIZE = 60.
_HOLE_RADIUS = 10.
_TERMINAL_RADIUS = 20
_HOLE_COLOR = "#B0B0B0"
_TRACE_COLOR = "#B0B0B0"
_FONT_SIZE = 10
_FONT_COLOR = "black"
_FONT_FAMILY = "Verdana"
_OCCUPY_SIZE = 40
_OCCUPY_OPACITY = 0.5
_PLACEMENT_SEP = 30
_BORDER_COLOR = "black"

def _grid_coords_to_pixel(coords, center=False):
    x, y = coords
    if center:
        x += 0.5
        y += 0.5
    return (x * _GRID_CELL_SIZE, y * _GRID_CELL_SIZE)

def _draw_hole(h, file=sys.stdout):
    center = _grid_coords_to_pixel(h, center=True)

    print('<circle cx="{}" cy="{}" r="{}" stroke="{}" '
          'stroke-width="{}" fill="transparent" />'.format(
                center[0], center[1], _HOLE_RADIUS, _HOLE_COLOR, _LINE_WIDTH),
          file=file)

def _draw_trace(t, file=sys.stdout):
    points = tuple(_grid_coords_to_pixel(t[i], center=True) for i in range(2))

    print('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" '
          'stroke-width="{}" />'.format(
            points[0][0], points[0][1], points[1][0], points[1][1],
            _TRACE_COLOR, _LINE_WIDTH),
          file=file)

def _draw_component_terminals(comp, pos, file=sys.stdout):
    for terminal, hole in pos.terminal_positions.items():
        center = _grid_coords_to_pixel(hole, center=True)

        print('<circle cx="{}" cy="{}" r="{}" stroke="{}" '
              'stroke-width="{}" fill="transparent" />'.format(
                  center[0], center[1], _TERMINAL_RADIUS, comp.color,
                  _LINE_WIDTH),
              file=file)

        print('<text x="{}" y="{}" font-family="{}" font-size="{}" '
              'color="{}">{}</text>'.format(
                  center[0], center[1], _FONT_FAMILY, _FONT_SIZE, _FONT_COLOR,
                  terminal.label),
              file=file)

def _draw_component_label(comp, pos, file=sys.stdout):
    top_left_cell = tuple(min(c[i] for c in pos.occupies) for i in range(2))
    top_left_pixel = _grid_coords_to_pixel(top_left_cell)

    print('<text x="{}" y="{}" font-family="{}" font-size="{}" '
          'color="{}">{}</text>'.format(
              top_left_pixel[0], top_left_pixel[1] + _FONT_SIZE, _FONT_FAMILY,
              _FONT_SIZE, _FONT_COLOR, comp.label),
          file=file)

def _draw_component_occupies(comp, pos, file=sys.stdout):
    """
    Draw a translucent region over cells that are occupied by a component.

    However, don't draw near edges of the region.

    """
    for cell in pos.occupies:
        top_left = _grid_coords_to_pixel(cell)

        # There's a grid of 9 rectangles which may be drawn, depending on
        # which neighbouring cells the component also occupies.
        xs = [top_left[0],
              top_left[0] + (_GRID_CELL_SIZE/2. - _OCCUPY_SIZE/2.),
              top_left[0] + (_GRID_CELL_SIZE/2. + _OCCUPY_SIZE/2.),
              top_left[0] + _GRID_CELL_SIZE]
        ys = [top_left[1],
              top_left[1] + (_GRID_CELL_SIZE/2. - _OCCUPY_SIZE/2.),
              top_left[1] + (_GRID_CELL_SIZE/2. + _OCCUPY_SIZE/2.),
              top_left[1] + _GRID_CELL_SIZE]

        for y_offset in (-1, 0, 1):
            for x_offset in (-1, 0, 1):
                if (cell[0] + x_offset, cell[1] + y_offset) in pos.occupies:
                    print('<rect x="{}" y="{}" width="{}" height="{}" '
                          'fill="{}" fill-opacity="{}" />'.format(
                              xs[1 + x_offset],
                              ys[1 + y_offset],
                              xs[2 + x_offset] - xs[1 + x_offset],
                              ys[2 + y_offset] - ys[1 + y_offset],
                              comp.color,
                              _OCCUPY_OPACITY),
                         file=file)

def print_svg(placements, file=sys.stdout):
    placements = list(placements)

    def placement_size(placement):
        size = tuple(_GRID_CELL_SIZE * (1 + max(h[i] 
                                              for h in placement.board.holes))
                 for i in (0, 1))
        return size

    widths, heights = zip(*(placement_size(placement)
                                                 for placement in placements))
    doc_width = max(widths) + _PLACEMENT_SEP
    doc_height = (sum(heights) + _PLACEMENT_SEP * (len(placements) - 1) +
                    _PLACEMENT_SEP)

    print('<svg width="{}" height="{}" '
          'xmlns="http://www.w3.org/2000/svg">'.format(doc_width, doc_height),
          file=file)

    vertical_offset = _PLACEMENT_SEP / 2
    for placement in placements:
        print('<g transform="translate({} {})">'.format(
                                         _PLACEMENT_SEP / 2, vertical_offset),
              file=file)

        size = placement_size(placement)

        print('<rect x="0" y="0" width="{}" height="{}" '
              'fill="transparent" stroke="{}" stroke-width="{}" />'.format(
                      size[0], size[1], _BORDER_COLOR, _LINE_WIDTH),
              file=file)
        for hole in placement.board.holes:
            _draw_hole(hole, file=file)

        for trace in placement.board.traces:
            _draw_trace(trace, file=file)

        for comp, pos in placement.items():
            _draw_component_terminals(comp, pos, file=file)
            _draw_component_occupies(comp, pos, file=file)
            _draw_component_label(comp, pos, file=file)

        print('</g>', file=file)
        vertical_offset += size[1] + _PLACEMENT_SEP

    print('</svg>', file=file)

