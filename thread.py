from pysmt.shortcuts import *
from typing import List


class Statement:
    def __init__(self):
        self.pre = TRUE
        self.post = TRUE

    def pretty(self) -> str:
        pass

    def compute_sp(self, pre):
        pass


class Procedure:
    def __init__(self, name: str, block: List[Statement]):
        # for now, specifications are handled with assume and assert statements
        self.name = name
        self.block = block
        self.requires = TRUE
        self.ensures = TRUE

    def get_name(self):
        return self.name

    def pretty(self):
        body = "".join(['\n' + s.pretty() for s in self.block])
        # indenting the body must be done like this to ensure that newlines
        # within s.pretty() are also indented
        body = body.replace('\n', '\n\t')
        return "procedure " + self.name + "() {" + body + "\n" + "}"


class Assignment(Statement):
    def __init__(self, left, right):
        super().__init__()
        self.left = left  # a symbol
        self.right = right  # an arithmetic expression or symbol

    def pretty(self):
        return str(self.left) + " := " + str(self.right) + ";"

    def compute_sp(self, pre):
        y = FreshSymbol(INT)
        # for x := E with precondition P:
        # exists y :: x == E[x\y] && P[x\y]
        first_conjunct = Equals(self.left, self.right.substitute(self.left, y))
        second_conjunct = pre.substitute(self.left, y)
        return Exists([y], And(first_conjunct, second_conjunct))


class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assume " + str(self.cond) + ";"

    def compute_sp(self, pre):
        return And(pre, self.cond)


class Assertion(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assert " + str(self.cond) + ";"

    def compute_sp(self, pre):
        # todo: unsure about this
        #  do asserts even need postconditions in my program structure?
        #  if correctness is only measured going backwards, the only reason
        #  asserts would need postconditions is in the case where there's one
        #  in the middle of a program, or multiple in a line. consider this case
        return Implies(self.cond, pre)


class Conditional(Statement):
    def __init__(self, cond, block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.block = block

    def pretty(self):
        body = "".join(['\n' + s.pretty() for s in self.block])
        body = body.replace('\n', '\n\t')
        return "if (" + str(self.cond) + ") {" + body + "\n" + "}"

    def compute_sp(self, pre, ):
        # todo: there is a problem here
        #  since the sp is defined in terms of the sp of the inner block, it
        #  needs to be computed first. this raises questions about how sp's will
        #  be computed over the whole procedure, which data structures will
        #  be used and generally how the algorithm will be implemented
        pass
