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
CNF module.

A wrapper around pycosat with some more Pythonic primitives, and utility
functions.

"""

__all__ = (
    'Clause',
    'Var',
)

import pycosat

class Var():
    """
    A propositional variable.

    Can optionally have a name.

    """
    def __init__(self, name=None):
        if name is None:
            name = "t{}".format(hash(self))

        self.name = name

    def __repr__(self):
        return "<Var(name={}, hash={})>".format(self.name, hash(self))

    def __str__(self):
        return self.name

class Clause():
    """
    A CNF clause.

    That is, a set of positive or negative vars all logically OR'd together.

    """
    def __init__(self, positive_terms, negative_terms):
        self.positive_terms = frozenset(positive_terms)
        self.negative_terms = frozenset(negative_terms)

    def __repr__(self):
        terms = ["{!r}".format(t) for t in self.positive_terms]
        terms += ["~{!r}".format(t) for t in self.negative_terms]
        return "<Clause({})>".format(", ".join(terms))

    def __str__(self):
        terms = ["{}".format(t) for t in self.positive_terms]
        terms += ["~{}".format(t) for t in self.negative_terms]
        return ", ".join(terms)

def all_cnfs(cnfs):
    """
    Concatenate a set of CNFs (ie. concatenate sets of clauses).

    """
    return {clause for cnf in cnfs for clause in cnf}

def at_least_one(pvars):
    """
    Return a CNF expression which is true iff at least one of `pvars` is true.

    """
    return {Clause(positive_terms=pvars, negative_terms={})}

def _pairwise_at_most_one(pvars):
    """
    Return a CNF expression which is true iff at most one of `pvars` is true.

    Do this naively by considering all possible pairs.

    """
    pvars = list(pvars)
    return { Clause(positive_terms={}, negative_terms={pvars[i], pvars[j]})
                                        for i in range(len(pvars))
                                            for j in range(i + 1, len(pvars)) }

def _create_commander(pvars):
    """
    Create a commander variable for a set of vars.

    The commander var is true if and only if at least one of the input vars is
    true.

    Returns the new commander variable, and the CNF expression that encodes the
    above constraint.

    """
    c = Var()

    cnf = set()
    cnf |= {Clause(positive_terms=pvars, negative_terms={c})}
    cnf |= { Clause(positive_terms={c}, negative_terms={p}) for p in pvars }

    return c, cnf

def _at_most_one_reduce(pvars):
    """
    Given a list of vars V1 return a shorter list of new vars V2 and associated
    constraints C such that:

        at_most_one(V1) <=> C ^ at_most_one(V2)

    """

    assert len(pvars) >= 6

    commanders = []
    cnf = set()
    while pvars:
        group, pvars = pvars[:3], pvars[3:]
        c, sub_cnf = _create_commander(group)
        commanders.append(c)
        cnf |= sub_cnf
        cnf |= _pairwise_at_most_one(group)

    return commanders, cnf

def at_most_one(pvars):
    """
    Return a CNF expression which is true iff at most one of `pvars` is true.

    Do this by repeatedly splitting into groups of 3, and replacing each group
    of 3 by a commander variable. Continue until the number of vars is < 6,
    when the naive pairwise method will be used.

    """

    cnf = set()
    while len(pvars) >= 6:
        pvars, new_cnf = _at_most_one_reduce(pvars)
        cnf |= new_cnf
    cnf |= _pairwise_at_most_one(pvars)

    return cnf

def exactly_one(pvars):
    """
    Return a CNF expression which is true iff exactly one of `pvars` is true.

    """

    return at_least_one(pvars) | at_most_one(pvars)

def solve(cnf):
    """
    Solve a CNF formula.

    """

    pvars = { v for clause in cnf for v in clause.negative_terms }
    pvars |= { v for clause in cnf for v in clause.positive_terms }
    pvars = list(pvars)

    pvar_to_index = {pvar: idx + 1 for idx, pvar in enumerate(pvars)}


    cnf = [ [ pvar_to_index[v] for v in clause.positive_terms ] + 
            [ -pvar_to_index[v] for v in clause.negative_terms ]
                                                            for clause in cnf ]
        
    for sol in pycosat.itersolve(cnf):
        yield { pvars[abs(idx) - 1]: (idx > 0) for idx in sol }

