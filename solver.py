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
Solver module.

Generic interface for SAT solvers, as well as a collection of SAT solvers
conforming to this interface.

Problems are represented as a list of lists of numbers, in a format analogous
to DIMACS: Each number represents a variable, negated if it's negative. Each
inner list represents a clause in the CNF formula.

Solutions are represented as a list of numbers; there is a number for each
variable in the input formula. If the number is negative the corresponding
variable is false, otherwise the variable is true.

"""

__all__ = (
    'LingelingSolver',
    'PycosatSolver',
    'Unknown',
    'Unsatisfiable',
)

import abc
import os
import subprocess
import sys
import tempfile

import pycosat

_DEBUG = True

# Dictionary mapping solver names to solver instances.
solvers = {}

class Unsatisfiable(Exception):
    """The formula has no solutions."""
    pass

class Unknown(Exception):
    """
    The solver could not determine whether the formula is (un)satisfiable.

    """
    pass

def _solver_class(name):
    """
    Class decorator for solvers.

    Adds an instance of the class to the `solvers` dict.

    """
    def decorator(cls):
        solvers[name] = cls()
        return cls

    return decorator

class _BaseSolver(metaclass=abc.ABCMeta):
    """Abstract base class from which all solvers are derived."""

    @abc.abstractmethod
    def solve(self, cnf):
        """
        Find the first solution to a CNF problem.

        If no solution exists, `Unsatisfiable` is returned.

        """
        raise NotImplemented

    def itersolve(self, cnf):
        """Find all solutions to a CNF problem."""

        # Once a solution is found, add the negation of the solution to the set
        # of clauses and search for another solution.
        cnf = cnf[:]
        while True:
            try:
                sol = self.solve(cnf)
            except Unsatisfiable:
                break

            yield sol
            cnf.append([-t for t in sol])
    
@_solver_class("pycosat")
class PycosatSolver(_BaseSolver):
    """Solver that uses pycosat."""

    def solve(self, cnf):
        return pycosat.solve(cnf)

    def itersolve(self, cnf):
        return pycosat.itersolve(cnf)

class _DimacsSolver(_BaseSolver):
    """
    Solver that uses an external process.

    The external process should accept input in DIMACS format.

    """
    _ENCODING = "ascii"

    @abc.abstractmethod
    def _get_cmd(self):
        return NotImplemented

    def solve(self, cnf):
        num_clauses = len(cnf)
        num_vars = max(abs(t) for c in cnf for t in c)

        with subprocess.Popen(self._get_cmd(),
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE) as proc:

            # Write the CNF and close stdin.
            def write(s):
                proc.stdin.write(s.encode(self._ENCODING))
            write("p cnf {} {}\n".format(num_vars, num_clauses))
            for clause in cnf:
                write("{} 0\n".format(" ".join(str(t) for t in clause)))
            proc.stdin.close()

            # Read the output.
            sol = []
            for line in proc.stdout.readlines():
                line = line.decode(self._ENCODING)

                if _DEBUG:
                    sys.stdout.write(line)

                if line.startswith("s UNSATISFIABLE"):
                    raise Unsatisfiable 

                if line.startswith("v "):
                    sol += [int(x) for x in line.split()[1:]]
                    if sol[-1] == 0:
                        return sol[:-1]

            raise Unknown

@_solver_class("lingeling")
class LingelingSolver(_DimacsSolver):
    """Solver that uses Lingeling."""

    _ENV_VAR = "LINGELING"
    _DEFAULT = "lingeling"

    def _get_cmd(self):
        if self._ENV_VAR in os.environ:
            return os.environ[self._ENV_VAR]
        else:
            return self._DEFAULT

