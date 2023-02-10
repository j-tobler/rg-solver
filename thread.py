from pysmt.shortcuts import *
from typing import List


class Statement:
    def __init__(self):
        self.pre = TRUE
        self.post = TRUE

    def pretty(self) -> str:
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
        return "procedure " + self.name + "() {" + \
               ("".join(['\n' + s.pretty() for s in self.block])).replace('\n', '\n\t') + "\n}"


class Assignment(Statement):
    def __init__(self, left, right):
        super().__init__()
        self.left = left  # a symbol
        self.right = right  # an arithmetic expression or symbol

    def pretty(self):
        return str(self.left) + " := " + str(self.right) + ";"


class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assume " + str(self.cond) + ";"


class Assertion(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return "assert " + str(self.cond) + ";"


class Conditional(Statement):
    def __init__(self, cond, block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.block = block

    def pretty(self):
        return "if (" + str(self.cond) + ") {" + \
               ("".join(['\n' + s.pretty() for s in self.block])).replace('\n', '\n\t') + "\n}"
