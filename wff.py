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
    'add_var',
    'for_all',
    'exists',
    'to_cnf',
    'Var',
)

import abc
import collections
import enum
import functools
import operator

import cnf

class _Term(collections.namedtuple('_TermBase', ('atom', 'negated'))):
    """
    A single term in a CNF expression.
    
    Distinguised from a cnf.Term by the fact that the term may contain an atom
    of any kind (a variable or a constant), as opposed to just a variable.
    
    """
    pass

class _Formula(metaclass=abc.ABCMeta):
    """
    Base class for formula types.

    Provides common methods. Suitable for use as a mixin.

    _Formulas are immutable, and sub-classes should respect this.

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

    def __rshift__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IMPLIES, [self, other])

    def __lshift__(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IMPLIES, [other, self])

    def iff(self, other):
        if not isinstance(other, _Formula):
            raise NotImplemented
        return _Op(_OpType.IFF, [self, other])

    @abc.abstractmethod
    def _is_op(self):
        """
        Is this formula an operation?

        """
        raise NotImplemented

    @abc.abstractmethod
    def _eliminate_iff(self):
        """
        Convert iff operations into two implies operations, ANDed.

        """
        raise NotImplemented

    @abc.abstractmethod
    def _eliminate_implies(self):
        """
        Convert implies operations (a >> b) into (~a | b).

        """
        raise NotImplemented

    @abc.abstractmethod
    def _move_nots(self):
        """
        Push NOTs inwards using De Morgan's Law.

        """
        raise NotImplemented

    @abc.abstractmethod
    def _distribute_ors(self):
        """
        Distribute AND over ORs.

        """
        raise NotImplemented

    @abc.abstractmethod
    def _extract_clauses(self):
        """
        Get a set of CNF clauses for this formula.

        Returns:
            A set of sets of _Term objects. Each set of _Term objects
            represents a clause of the CNF expression.

        """
        raise NotImplemented

    @abc.abstractmethod
    def _create_intermediate_vars(self):
        """
        Replace sub-formulae with intermediate vars, if needed.

        A sub-formula is replaced if it is wrapped with _AddVarFlag.

        Returns:
            A sequence of `(var, formula)` pairs, of intermediate vars and the
            formulas they represent, and the formula with variables in place of
            the sub trees.

        """
        raise NotImplemented

    @staticmethod
    def _eliminate_constants(clauses):
        """
        Remove constants from a set of CNF clauses.

        This amounts to removing clauses which contain terms which are always
        true, and removing terms which are always false.

        """

        # Remove clauses that contain terms which are always true.
        clauses = {clause for clause in clauses if not
                            (_Term(_Const(True), negated=False) in clause or
                             _Term(_Const(False), negated=True) in clause)}

        # Remove terms which are always false.
        clauses = {frozenset(term for term in clause if 
                              term not in (_Term(_Const(False), negated=False),
                                           _Term(_Const(True), negated=True)))
                    for clause in clauses}
        
        return clauses

    def _add_intermediate_vars_to_expr(self, intermediate_vars, expr):
        """
        Augment a CNF expression to enforce the intermediate variabele
        definitions. In general this is done by appending clauses equivalent to
        the following:
        
            <new var> iff <associated formula>
        
        However, in the case where <new var> only appears in positive terms
        elsewhere in the expression, this can be reduced to:
        
            <new var> => <associated formula>
        
        While preserving satisfiability. Similarly, if <new var> only appears
        in negative terms elsewhere in the expression, clauses equivalent to
        the following can be added:
        
            <new var> <= <associated formula>
        
        While also preserving satisfiability.

        """
        # Iterate over the intermediate variables and their associated CNF
        # expressions. Nested intermediate vars (ie. intermediate
        # vars in the formula associated with a different intermediate vars)
        # are handled in the recursive call to `to_cnf`.
        for var, var_formula in intermediate_vars:
            any_pos = any(not t.negated for c in expr for t in c
                                                               if t.var == var)
            any_neg = any(t.negated for c in expr for t in c if t.var == var)

            if any_neg and any_pos:
                # Mixed negative and positive.
                expr |= to_cnf(var.iff(var_formula))
            elif not any_neg and any_pos:
                # Purely positive.
                expr |= to_cnf(var >> var_formula)
            elif any_neg and not any_pos:
                # Purely negative.
                expr |= to_cnf(var << var_formula)
            else:
                # No occurences of the variable. This can happen if an
                # `add_var` node appears in an expression that was optimised
                # out due to constant elimination (eg. `(exists([]) &
                # add_var(Var()))`).
                pass

        return expr

    def _to_cnf(self):
        """Implementation of `to_cnf()`."""

        intermediate_vars, formula = self._create_intermediate_vars()

        formula = formula._eliminate_iff()
        formula = formula._eliminate_implies()
        formula = formula._move_nots()
        formula = formula._distribute_ors()

        clauses = self._eliminate_constants(formula._extract_clauses())

        expr = cnf.Expr(
            cnf.Clause(cnf.Term(term.atom, negated=term.negated)
                                                            for term in clause)
                for clause in clauses)

        expr = self._add_intermediate_vars_to_expr(intermediate_vars, expr)

        return expr

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

        if len(args) != self.OP_ARITY[op_type]:
            raise ValueError

    def __repr__(self):
        op_to_str = {_OpType.AND: "&",
                     _OpType.OR: "|",
                     _OpType.IMPLIES: ">>"}

        if self._op_type == _OpType.NOT:
            return "~{!r}".format(self._args[0])
        elif self._op_type == _OpType.IFF:
            return "({!r}).iff({!r})".format(*self._args)
        else:
            return "({!r} {} {!r})".format(self._args[0],
                                           op_to_str[self._op_type],
                                           self._args[1])

    def _is_op(self):
        return True

    def _eliminate_iff(self):
        new_args = [arg._eliminate_iff() for arg in self._args]
        if self._op_type == _OpType.IFF:
            out = (new_args[0] >> new_args[1]) & (new_args[0] << new_args[1])
        else:
            out = _Op(self._op_type, new_args)
        return out

    def _eliminate_implies(self):
        new_args = [arg._eliminate_implies() for arg in self._args]
        if self._op_type == _OpType.IMPLIES:
            out = (~new_args[0] | new_args[1])
        else:
            out = _Op(self._op_type, new_args)
        return out

    def _move_nots(self):
        if self._op_type == _OpType.NOT and self._args[0]._is_op():
            # Not of an operation. Either move the NOT in through De Morgan's
            # Law (in the case of an OR or an AND), or in the case of a NOT of
            # a NOT eliminate both NOTs. Recursively apply to the result.
            arg = self._args[0]
            if arg._op_type == _OpType.NOT:
                out = arg._args[0]
            elif arg._op_type == _OpType.AND:
                out = ~arg._args[0] | ~arg._args[1]
            elif arg._op_type == _OpType.OR:
                out = ~arg._args[0] & ~arg._args[1]
            else:
                assert False, ("Op of type {} should have been "
                               "eliminated".format(self._op_type))
            out = out._move_nots()
        elif self._op_type == _OpType.NOT and not self._args[0]._is_op():
            # NOT of a var. Nothing to do.
            out = self
        else:
            # Some other operation. Apply the operation to the children.
            new_args = [arg._move_nots() for arg in self._args]
            out = _Op(self._op_type, new_args)
        return out

    def _distribute_ors(self):
        # Precondition: The formula contains only AND, OR and NOT operators,
        #               and vars. The NOT operations only appear applied to
        #               vars.
        # Postcondition: The formula is in CNF.

        new_args = [arg._distribute_ors() for arg in self._args]

        if (self._op_type == _OpType.OR and
            new_args[1]._is_op() and new_args[1]._op_type == _OpType.AND):
            # We have an expression of the form P | (Q & R), so distribute to
            # (P | Q) & (P | R).
            out = ((new_args[0] | new_args[1]._args[0]) &
                   (new_args[0] | new_args[1]._args[1]))

            # The RHS or LHS of `out` ((P | Q) or (P | R)) may still contain
            # ANDs, so run _distribute_ors() on them to bring ANDs up to the
            # top. After this `out` will be in CNF.
            out = (out._args[0]._distribute_ors() &
                   out._args[1]._distribute_ors())
        elif (self._op_type == _OpType.OR and
              new_args[0]._is_op() and new_args[0]._op_type == _OpType.AND):
            # We have an expression of the form (P & Q) | R, so distribute to
            # (P | R) & (Q | R)
            out = ((new_args[0]._args[0] | new_args[1]) &
                   (new_args[0]._args[1] | new_args[1]))

            # Distribute the ORs on the children, as in the previous case.
            out = (out._args[0]._distribute_ors() &
                   out._args[1]._distribute_ors())
        else:
            # We either have a pure tree of ORs, a tree with ANDs at the top, 
            # or just a single term. All of these satisfy the post-condition
            # for this function.
            out = _Op(self._op_type, new_args)

        return out

    def _extract_clauses(self):
        child_clauses = tuple(a._extract_clauses() for a in self._args)

        if self._op_type == _OpType.AND:
            out = child_clauses[0] | child_clauses[1]
        elif self._op_type == _OpType.OR:
            assert all(len(a) == 1 for a in child_clauses), \
                    "AND found under OR in CNF formula"
            out = {next(iter(child_clauses[0])) | 
                   next(iter(child_clauses[1]))}
        elif self._op_type == _OpType.NOT:
            assert len(child_clauses[0]) == 1, \
                    "AND found under NOT in CNF formula"
            clause = next(iter(child_clauses[0]))
            assert len(clause) == 1, \
                    "OR found under NOT in CNF formula"
            term = next(iter(clause))
            assert not term.negated, "NOT found under NOT in CNF formula"

            out = {frozenset({_Term(term.atom, negated=True)})}

        return out

    def _create_intermediate_vars(self):
        child_results = tuple(a._create_intermediate_vars()
                                                           for a in self._args)

        child_vars = [pair for pairs, _ in child_results for pair in pairs]
        child_formulae = [r[1] for r in child_results]

        return child_vars, _Op(self._op_type, child_formulae)

class _Atom(_Formula):
    """
    A formula which cannot be broken into smaller parts.

    Either a variable, or a constant.

    """
    def _is_op(self):
        return False

    def _eliminate_iff(self):
        return self

    def _eliminate_implies(self):
        return self

    def _move_nots(self):
        return self

    def _distribute_ors(self):
        return self

    def _extract_clauses(self):
        return {frozenset({_Term(self, negated=False)})}

    def _create_intermediate_vars(self):
        return [], self

class Var(cnf.Var, _Atom):
    def __init__(self, name=None):
        super().__init__(name=name)

    def __repr__(self):
        return "Var({!r})".format(self.name)

class _Const(_Atom):
    def __init__(self, val):
        if not isinstance(val, bool):
            raise ValueError
        self.val = val

    def __repr__(self):
        return "Const({!r})".format(self.val)

    def __hash__(self):
        return hash((self.val, _Const))

    def __eq__(self, other):
        if not isinstance(other, _Const):
            return False
        return self.val == other.val

class _AddVarFlag(_Formula):
    def __init__(self, formula):
        self.formula = formula

    def _create_intermediate_vars(self):
        new_var = Var()

        intermediate_vars, formula = self.formula._create_intermediate_vars()

        return (intermediate_vars + [(new_var, formula)]), new_var

    def _is_op(self):
        raise AssertionError

    def _eliminate_iff(self):
        raise AssertionError

    def _eliminate_implies(self):
        raise AssertionError

    def _move_nots(self):
        raise AssertionError

    def _distribute_ors(self):
        raise AssertionError

    def _extract_clauses(self):
        raise AssertionError
            
def to_cnf(formula):
    """
    Convert the formula to CNF (conjunctive normal form).

    """
    return formula._to_cnf()

def exists(formulae):
    """
    Return a formula which is true if any of the given formulas are true.

    """
    return functools.reduce(operator.or_, formulae, _Const(False))

def for_all(formulae):
    """
    Return a formula which is true if all of the given formulas are true.

    """
    return functools.reduce(operator.and_, formulae, _Const(True))

def add_var(formula):
    """
    Flag that an intermediate variable should represent the given formula.

    """
    return _AddVarFlag(formula)

