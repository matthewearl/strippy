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
A 555 astable circuit.

"""

import component
import cli

ic555 = component.DualInlinePackage("555", 8)
r1 = component.Resistor("R1", 4)
r2 = component.Resistor("R2", 4)
c1 = component.Capacitor("C1", 4)
c2 = component.Capacitor("C2", 4)
components = (ic555, r1, r2, c1, c2)

board = component.StripBoard((7, 7))

nets = (
    (r1.terminals[0], ic555.terminals[3], ic555.terminals[7]),
    (r1.terminals[1], ic555.terminals[6], r2.terminals[0]),
    (r2.terminals[1], ic555.terminals[5], ic555.terminals[1], c1.terminals[0]),
    (c1.terminals[1], ic555.terminals[0], c2.terminals[1]),
    (c2.terminals[0], ic555.terminals[4]),
    (ic555.terminals[2],)
)

cli.main(board, components, nets)

