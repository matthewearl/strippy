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

A wrapper around the solver module with some more Pythonic primitives, and
utility functions.

"""

__all__ = (
    'at_least_one',
    'at_most_one',
    'exactly_one',
    'iff',
    'implies',
    'Clause',
    'Expr',
    'solve',
    'solve_one',
    'tseitin_and',
    'Term',
    'Var',
)

import collections 
import sys

import solver

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

class Term():
    """
    A term in a clause.

    Either a variable, or a negated variable.

    """
    def __init__(self, var, negated=False):
        self.var = var
        self.negated = negated

    def __repr__(self):
        return "Term(var={!r}, negated={!r}".format(self.var, self.negated)

    def __str__(self):
        return "{}{}".format("~" if self.negated else "",
                             self.var)

class Clause():
    """
    A CNF clause.

    That is, a set of positive or negative vars all logically OR'd together.

    """
    def __init__(self, terms):
        self.terms = frozenset(terms)

    def __repr__(self):
        return "Clause(terms={!r})".format(self.terms)

    def __str__(self):
        return " v ".join(str(t) for t in
                                sorted(self.terms, key=(lambda t: t.var.name)))

    def __iter__(self):
        return iter(self.terms)

    def __or__(self, other):
        return Clause(self.terms | other.terms)

    def __len__(self):
        return len(self.terms)

class Expr():
    """
    A CNF expression.

    That is, a set of CNF clauses.

    """
    def __init__(self, clauses=()):
        self.clauses = frozenset(clauses)

    def __repr__(self):
        return "Expr(clauses={!r})".format(self.clauses)

    def __str__(self):
        return " ^ ".join("({})".format(c) for c in self.clauses)

    def __or__(self, other):
        return Expr(self.clauses | other.clauses)

    def __iter__(self):
        return iter(self.clauses)

    def __len__(self):
        return len(self.clauses)

    @property
    def stats(self):
        num_clauses = len(self.clauses)
        num_terms = sum(len(c.terms) for c in self.clauses)
        num_vars = len({t.var for c in self.clauses for t in c.terms})

        return collections.namedtuple('Stats', ('clauses', 'terms', 'vars'))(
                          num_clauses,
                          num_terms,
                          num_vars)

    @staticmethod
    def all(cnfs):
        """
        Concatenate an iterable of CNFs.

        """
        return Expr(clause for cnf in cnfs for clause in cnf)

    def print(self, file=sys.stdout):
        for s in sorted("({})".format(c) for c in self.clauses):
            print(s, file=file)
        print(file=file)

def _pairwise_at_most_one(pvars):
    """
    Return a CNF expression which is true iff at most one of `pvars` is true.

    Do this naively by considering all possible pairs.

    """
    pvars = list(pvars)

    return Expr(Clause({Term(pvars[i], negated=True),
                       Term(pvars[j], negated=True)})
                  for i in range(len(pvars)) for j in range(i + 1, len(pvars)))
                

def _create_commander(pvars):
    """
    Create a commander variable for a set of vars.

    The commander var is true if and only if at least one of the input vars is
    true.

    Returns the new commander variable, and the CNF expression that encodes the
    above constraint.

    """
    c = Var()

    clauses = set()

    # If the commander is true, then at least one of the vars must be true.
    clauses |= {Clause({Term(v) for v in pvars} | {Term(c, negated=True)})}

    # If the commander is false, then none of the variables can be true.
    clauses |= {Clause({Term(c), Term(p, negated=True)}) for p in pvars}

    return c, Expr(clauses)

def _at_most_one_reduce(pvars):
    """
    Given a list of vars V1 return a shorter list of new vars V2 and associated
    constraints C such that:

        at_most_one(V1) <=> C ^ at_most_one(V2)

    """

    assert len(pvars) >= 6

    commanders = []
    cnf = Expr()
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

    pvars = list(pvars)
    cnf = Expr()
    while len(pvars) >= 6:
        pvars, new_cnf = _at_most_one_reduce(pvars)
        cnf |= new_cnf
    cnf |= _pairwise_at_most_one(pvars)

    return cnf

def at_least_one(pvars):
    """
    Return a CNF expression which is true iff at least one of `pvars` is true.

    """
    return Expr({Clause(Term(v) for v in pvars)})

def exactly_one(pvars):
    """
    Return a CNF expression which is true iff exactly one of `pvars` is true.

    """
    pvars = list(pvars)

    return at_least_one(pvars) | at_most_one(pvars)

def implies(pvar1, pvar2):
    """
    Return a CNF expression which is true iff var1 implies var2.

    """
    return Expr({Clause({Term(pvar1, negated=True), Term(pvar2)})})

def iff(pvar1, pvar2):
    """
    Return a CNF expression which is true iff var1 is equivalent to var2.

    """
    return implies(pvar1, pvar2) | implies(pvar2, pvar1)

def tseitin_and(pvars):
    """
    Make a new var equivalent to the logical AND of a set of vars.

    Also return the CNF expression which enforces this relationship.

    """
    out_var = Var()
    expr = Expr({Clause({Term(pvar, negated=True) for pvar in pvars} |
                        {Term(out_var)})} |
                {Clause({Term(pvar), Term(out_var, negated=True)})
                                                  for pvar in pvars})

    return out_var, expr

def solve(cnf, slvr=None):
    """
    Solve a CNF formula.

    """

    if slvr is None:
        slvr = solver.solvers["pycosat"]

    # Construct mappings between Vars and variable IDs. Variable IDs are
    # integers > 0 used by the solver module to identify variables.
    pvars = list(sorted({term.var for clause in cnf for term in clause},
                        key=lambda v: v.name))
    pvar_to_id = {pvar: idx + 1 for idx, pvar in enumerate(pvars)}

    # The solver module input is just a list of lists, mirroring the CNF/Clause
    # hierarchy. Terms are replaced by their variable IDs, (numerically)
    # negated if the term is (logically) negated.
    cnf = [[pvar_to_id[term.var] * (-1 if term.negated else 1)
                for term in clause]
                    for clause in cnf]
    
    for sol in slvr.itersolve(cnf):
        yield {pvars[abs(n) - 1]: (n > 0) for n in sol}

def solve_one(cnf, slvr=None):
    """
    Solve a CNF formula. Return only the first solution.

    Raises an IteratorException if no solutions exist.

    """
    
    return next(solve(cnf, slvr=slvr))

