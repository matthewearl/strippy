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
A simple example, placing 4 resistors in a loop on a 3x4 strip board.

Three of the resistors have a maximum length of 1, whereas the other has a
maximum length of 3. There should be 12 solutions in total.

"""

import component
import cli

r1 = component.LeadedComponent("R1", 3)
r2 = component.LeadedComponent("R2", 1)
r3 = component.LeadedComponent("R3", 1)
r4 = component.LeadedComponent("R4", 1)
components = (r1, r2, r3, r4)

board = component.StripBoard((3, 4))

nets = (
    (r1.terminals[1], r2.terminals[0]),
    (r2.terminals[1], r3.terminals[0]),
    (r3.terminals[1], r4.terminals[0]),
    (r4.terminals[1], r1.terminals[0]),
)

cli.main(board, components, nets)
