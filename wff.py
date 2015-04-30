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
WFF module.

Routines for making propositional logic formulae, as well as routines for
converting them to CNF expressions in an efficient manner.

"""

__all__ = (
)

import enum

import cnf

class _Formula():
    """
    Base class for formula types.

    Overloads operators so that formulae can be composed.

    """

    def __invert__(self):
        return _Op(_OpType.NOT, [self])

    def __and__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.AND, [self, other])

    def __or__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.OR, [self, other])

    def __rrshift__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IMPLIES, [self, other])

    def __rlshift__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IMPLIES, [other, self])

    def iff(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IFF, [self, other])

class _OpType(enum.Enum):
    NOT     = 1
    AND     = 2
    OR      = 4
    IMPLIES = 5
    IFF     = 6

class _Op(_Formula):
    """
    A formula consisting of a binary or unary operation on 2 other formulae.

    Attributes:
        op_type: The operation that this formula represents.
        args: Arguments to the operation.

    """

    OP_ARITY = {_OpType.NOT: 1,
                _OpType.AND: 2,
                _OpType.OR: 2,
                _OpType.IMPLIES: 2,
                _OpType.IFF: 2,
               }
    
    def __init__(self, op_type, args):
        self._op_type = op_type
        self._args = args

        if len(args) != OP_ARITY[op_type]:
            raise ValueError

    def __repr__(self):
        op_to_str = {_OpType.AND: "and",
                     _OpType.OR: "or",
                     _OpType.IMPLIES: ">>"}

        if self._op_type == _OpType.NOT:
            return "~{!r}".format(self.args[0])
        elif self._op_type == _OpType.IFF:
            return "({!r}).iff({!r})".format(*self.args)
        else:
            return "({!r} {} {!r})".format(args[0],
                                           op_to_str[self._op_type],
                                           args[1])

class Var(cnf.Var, _Expr):
    def __init__(self, name=None):
        super().__init__(name=name)

    def __repr__(self):
        return "Var({!r})".format(name)

