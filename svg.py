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
_PIXELS_PER_GRID_CELL = 30.
_HOLE_RADIUS = 5.
_HOLE_COLOR = "black"
_TRACE_COLOR = "black"

def _grid_coords_to_pixel(coords, center=False):
    x, y = coords
    if center:
        x += 0.5
        y += 0.5
    return (x * _PIXELS_PER_GRID_CELL, y * _PIXELS_PER_GRID_CELL)

def _make_hole_mask(holes, file=sys.stdout):
    print('<mask id="hole-mask">', file=file)
    print('<rect width="100%" height="100%" x="0" y="0" fill="white" />',
          file=file)
    for hole in holes:
        center =_grid_coords_to_pixel(hole, center=True)
        print('<circle cx="{}" cy="{}" r="{}" fill="black" stroke="black" '
              'stroke-width="{}" />'.format(
                              center[0], center[1], _HOLE_RADIUS, _LINE_WIDTH),
              file=file)
    print('</mask>', file=file)

def _draw_hole(h, file=sys.stdout):
    center = _grid_coords_to_pixel(h, center=True)

    print('<circle cx="{}" cy="{}" r="{}" stroke="{}" '
          'stroke-width="{}" fill="transparent" />'.format(
                center[0], center[1], _HOLE_RADIUS, _HOLE_COLOR, _LINE_WIDTH),
          file=file)

def _draw_trace(t, file=sys.stdout):
    points = tuple(_grid_coords_to_pixel(t[i], center=True) for i in range(2))

    print('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" '
          'stroke-width="{}" mask="url(#hole-mask)" />'.format(
            points[0][0], points[0][1], points[1][0], points[1][1],
            _TRACE_COLOR, _LINE_WIDTH),
          file=file)

def print_svg(placement, file=sys.stdout):

    size = tuple(_PIXELS_PER_GRID_CELL * (1 + max(h[i] 
                                               for h in placement.board.holes))
                 for i in (0, 1))
    print('<svg width="{}" height="{}">'.format(size[0], size[1]), file=file)

    _make_hole_mask(placement.board.holes, file=file)

    for hole in placement.board.holes:
        _draw_hole(hole, file=file)

    for trace in placement.board.traces:
        _draw_trace(trace, file=file)
    print('</svg>', file=file)

