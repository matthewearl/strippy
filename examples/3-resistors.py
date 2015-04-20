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
A simple example placing 3 resistors in a loop on a 2x3 strip board.

Two of the resistors have a maximum length of 1, whereas the other has a
maximum length of 1. As such there should be 2 solutions in total.

"""

import component
import placer

r1 = component.LeadedComponent(2)
r2 = component.LeadedComponent(1)
r3 = component.LeadedComponent(1)

board = component.StripBoard((2, 3))

nets = (
    (r1.terminals[1], r2.terminals[0]),
    (r2.terminals[1], r3.terminals[0]),
    (r3.terminals[1], r1.terminals[0]),
)

for placement in placer.place(board, (r1, r2, r3), nets):
    print("R1: {}".format(placement[r1]))
    print("R2: {}".format(placement[r2]))
    print("R3: {}".format(placement[r3]))
    print()
