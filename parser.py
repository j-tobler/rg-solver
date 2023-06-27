from lark import Lark, Transformer
from thread import *

'''
Test:
[x] Signed integers
[ ] Booleans mixed with comparisons
[ ] Failure of boolean variables
[ ] True and False literals

To add:
[ ] If and only if
'''

grammar = """
    _PROCEDURE: "procedure"
    _IF: "if"
    _ASSUME: "assume"
    _ASSERT: "assert"
    PLUS: "+"
    MINUS: "-"
    TIMES: "*"
    DIV: "/"
    IMPLIES: "==>"
    OR: "||"
    AND: "&&"
    NOT: "!"
    TRUE: "true"
    FALSE: "false"
    LT: "<"
    LE: "<="
    GT: ">"
    GE: ">="
    EQ: "=="
    NE: "!="

    start: procedure
    procedure: _PROCEDURE CNAME "()" block  // currently not supporting parameters
    block: "{" (assign | branch | assume | assertion)* "}"
    
    assign: CNAME ":=" a_expr ";"  // currently not supporting boolean variable types
    branch: _IF "(" impl ")" block  // currently not supporting else blocks
    assume: _ASSUME impl ";"
    assertion: _ASSERT impl ";"
    
    ?expr: impl | a_expr  // expressions can be boolean or arithmetic
    
    ?impl: disj IMPLIES impl | disj  // impl takes bools and returns bool, c_expr takes ints and returns bool
    ?disj: disj OR conj | conj
    ?conj: conj AND neg | neg
    ?neg: NOT neg | atom
    ?atom: "(" impl ")" | bool | comp  // currently not supporting boolean variable types
    bool: TRUE | FALSE
    comp: a_expr (LE | LT | GE | GT | EQ | NE) a_expr
    
    ?a_expr: a_expr (PLUS | MINUS) term | term
    ?term: term (TIMES | DIV) num | num
    ?num: int_literal | variable
    int_literal: SIGNED_INT
    variable: CNAME
    
    %import common.WORD
    %import common.CNAME
    %import common.WS
    %import common.SIGNED_INT
    
    %ignore WS
"""


def with_type(arg):
    return str(arg) + ' ' + str(type(arg))


class Transform(Transformer):
    def procedure(self, args):
        return Procedure(str(args[0]), args[1])

    def block(self, args):
        return args

    def assign(self, args):
        return Assignment(args[0], args[1])

    def branch(self, args):
        return Conditional(args[0], args[1])

    def assume(self, args):
        return Assumption(args[0])

    def assertion(self, args):
        return Assertion(args[0])

    def impl(self, args):
        return Implies(args[0], args[2])

    def disj(self, args):
        return Or(args[0], args[2])

    def conj(self, args):
        return And(args[0], args[2])

    def neg(self, args):
        return Not(args[1])

    def atom(self, args):
        return args[0]

    def bool(self, args):
        TRUE() if str(args[0]) == "true" else FALSE()

    def comp(self, args):
        op = str(args[1])
        if op == "<=":
            return LE(args[0], args[2])
        if op == "<":
            return LT(args[0], args[2])
        if op == ">=":
            return GE(args[0], args[2])
        if op == ">":
            return GT(args[0], args[2])
        if op == "==":
            return Equals(args[0], args[2])
        if op == "!=":
            return NotEquals(args[0], args[2])

    def a_expr(self, args):
        op = str(args[1])
        if op == "+":
            return Plus(args[0], args[2])
        if op == "-":
            return Minus(args[0], args[2])

    def term(self, args):
        op = str(args[1])
        if op == "*":
            return Times(args[0], args[2])
        if op == "/":
            return Div(args[0], args[2])

    def int_literal(self, args):
        return Int(int(args[0]))

    def variable(self, args):
        return Symbol(str(args[0]), INT)


with open("t1.txt", "r") as reader:
    obj: Procedure = Lark(grammar, parser='lalr', transformer=Transform()).parse(reader.read()).children[0]
    print(obj.pretty())

print()

with open("t2.txt", "r") as reader:
    obj: Procedure = Lark(grammar, parser='lalr', transformer=Transform()).parse(reader.read()).children[0]
    print(obj.pretty())
