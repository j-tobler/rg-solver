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





'''
class ArithOperator(Enum):
    PLUS = '+'
    MINUS = '-'
    TIMES = '*'
    DIVIDE = '/'


class ArithUnaryOperator(Enum):
    NEGATIVE = '-'


class BinOperator(Enum):
    AND = '&&'
    OR = '||'
    IMPLIES = '==>'
    IFF = '<==>'


class BinUnaryOperator(Enum):
    NEGATE = '!'


class CompOperator(Enum):
    LT = '<'
    LE = '<='
    GT = '>'
    GE = '>='
    EQ = '=='


class AExpr:
    def __init__(self):
        pass


class IntLiteral(AExpr):
    def __init__(self, value: int):
        super().__init__()
        self.value = value

    @staticmethod
    def create(string, location, tokens):
        return IntLiteral(int(tokens[0]))

    def __repr__(self):
        return self.value


class Variable(AExpr):
    def __init__(self, name):
        super().__init__()
        self.name = name

    @staticmethod
    def create(string, location, tokens):
        return Variable(tokens[0])

    def __repr__(self):
        return self.name


class ArithOperation(AExpr):
    def __init__(self, left: AExpr, op: ArithOperator, right: AExpr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class ArithUnaryOperation(AExpr):
    def __init__(self, op: ArithUnaryOperator, right: AExpr):
        super().__init__()
        self.op = op
        self.right = right


class BExpr:
    def __init__(self):
        pass


class BoolLiteral(BExpr):
    def __init__(self, value: bool):
        super().__init__()
        self.value = value

    @staticmethod
    def create(string, location, tokens):
        return BoolLiteral(tokens[0] == "True")


class CompOperation(BExpr):
    def __init__(self, left: AExpr, op: CompOperator, right: AExpr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class BinOperation(BExpr):
    def __init__(self, left: BExpr, op: BinOperator, right: BExpr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right


class BinUnaryOperation(AExpr):
    def __init__(self, op: BinUnaryOperator, right: BExpr):
        super().__init__()
        self.op = op
        self.right = right


class Statement:
    def __init__(self):
        self.pre = TRUE
        self.post = TRUE


class Procedure:
    def __init__(self, name: str, block: List[Statement]):
        self.name = name
        self.block = block
        self.pre = TRUE
        self.post = TRUE

    @staticmethod
    def create(string, location, tokens):
        return Procedure(tokens[0], tokens[1:][0])

    def get_n(self):
        return self.name


class Assignment(Statement):
    def __init__(self, left: Variable, right: AExpr):
        super().__init__()
        self.left = left
        self.right = right

    @staticmethod
    def create(string, location, tokens):
        return Assignment(tokens[0], tokens[1])

    def __repr__(self):
        return str(self.left) + " := " + str(self.right)


class Assumption(Statement):
    def __init__(self, cond: BExpr):
        super().__init__()
        self.cond = cond


class Assertion(Statement):
    def __init__(self, cond: BExpr):
        super().__init__()
        self.cond = cond


class Conditional(Statement):
    def __init__(self, cond: BExpr, block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.stmt_list = block
'''
