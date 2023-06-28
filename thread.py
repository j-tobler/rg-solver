from pysmt.shortcuts import *
from typing import List


class Statement:
    def __init__(self):
        # To represent the proof outline, every statement stores its
        # precondition. Initially, all assertions in the proof are false.
        self.precondition = FALSE()

    def pretty(self) -> str:
        pass


class Procedure:
    def __init__(self, name: str, block: List[Statement]):
        self.name = name
        self.block = block

    def get_name(self):
        return self.name

    def pretty(self):
        body = "".join(['\n' + s.pretty() for s in self.block])
        # Indenting the body must be done this way to ensure that newlines
        # within s.pretty() are also indented.
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
        # sp(x := E, P) = exists y :: x == E[x\y] && P[x\y]
        y = FreshSymbol(INT)
        first_conjunct = Equals(self.left, self.right.substitute(self.left, y))
        second_conjunct = pre.substitute(self.left, y)
        sp = Exists([y], And(first_conjunct, second_conjunct))



class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assume " + str(self.cond) + ";"

    def compute_sp(self, pre):
        # sp(assume E, P) = P && E
        return And(pre, self.cond)


class Assertion(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assert " + str(self.cond) + ";"

    def compute_sp(self, pre):
        # sp(assert E, P) = E ==> P
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

    def compute_sp(self, pre, block_sp):
        # sp(if B then S, P) = sp(skip, !B && P) || sp(S, B && P)
        # = (!B && P) || sp(S, B && P)
        first_disjunct = And(Not(self.cond), pre)
        return Or(first_disjunct, block_sp)
