#!/usr/bin/env python3
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
Place a 6-pin DIP-backage with resistors placed horizontally.

"""

import component
import cli

ic = component.DualInlinePackage("IC1", 6, row_spacing=2)
r1 = component.Resistor("R1", 1)
r2 = component.Resistor("R2", 2)
r3 = component.Resistor("R3", 2)

components = (ic, r1, r2, r3)

board = component.StripBoard((7, 6))

nets = (
    (ic.terminals[0], r1.terminals[0]),
    (ic.terminals[1], r2.terminals[0]),
    (ic.terminals[2], r3.terminals[0]),
    (ic.terminals[3], r3.terminals[1]),
    (ic.terminals[4], r2.terminals[1]),
    (ic.terminals[5], r1.terminals[1]),
)

cli.main(board, components, nets)

