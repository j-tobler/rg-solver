import pyparsing as pp
from pyparsing import *
from pysmt.shortcuts import *
from typing import List
import thread
from thread import *

# tokens

lpar = Literal("(").suppress()
rpar = Literal(")").suppress()
lcub = Literal("{").suppress()
rcub = Literal("}").suppress()
assgn = Literal(":=").suppress()
semi = Literal(";").suppress()
aop = one_of("+ - * /")
bop = one_of("&& || ==> <==>")
cop = one_of("< <= >= > ==")
bang = Literal("!")
neg = Literal("-")


# variables and literals

def identifier_action(tokens): return Symbol(tokens[0], INT)
identifier = pp.Word(alphas + "_", alphanums + "_")
identifier.set_parse_action(identifier_action)


def int_literal_action(tokens): return Int(int(tokens[0]))
int_literal = pp.Word(nums)
int_literal.set_parse_action(int_literal_action)


def bool_literal_action(tokens): return Bool(tokens[0] == 'true')
bool_literal = one_of("true false")
bool_literal.set_parse_action(bool_literal_action)

# expressions (does not currently support boolean variable types)

operand = int_literal | identifier
expr = infixNotation(operand,
    [
        (oneOf('* /'), 2, opAssoc.LEFT),
        (oneOf('+ -'), 2, opAssoc.LEFT),
    ])

def expr_pre_action(tokens):
    print(tokens)
    return expr_action(tokens[0])

'''
Fuck this. Use parsimonious or lark.
'''

def expr_action(tokens):
    print(tokens)
    if isinstance(tokens, ParseResults):
        # expression is some operation
        if tokens[1] == '+':
            return Plus(tokens[0], tokens[2])
        if tokens[1] == '-':
            return Minus(tokens[0], tokens[2])
        if tokens[1] == '*':
            return Times(tokens[0], tokens[2])
        if tokens[1] == '/':
            return Div(tokens[0], tokens[2])
        else:
            exit('Unknown arithmetic operator.')
expr.set_parse_action(expr_pre_action)


'''
aexp <<= int_literal | (aexp + aop + aexp) | (lpar + aexp + rpar) | (neg + aexp) | identifier

bexp <<= one_of("true false") | (aexp + cop + aexp) | (bexp + bop + bexp) | (bang + bexp) | (lpar + bexp + rpar)

expr = aexp | bexp

# statements
stmt = Forward()
block = lcub + stmt[...] + rcub
assignment = identifier + assgn + expr + semi
assignment.set_parse_action(Assignment.create)
conditional = pp.Keyword("if") + lpar + bexp + rpar + block
assumption = pp.Keyword("assume") + bexp + semi
assertion = pp.Keyword("assert") + bexp + semi
stmt <<= conditional | assumption | assertion | assignment

# procedures
# does not currently support parameters
procedure = pp.Keyword("procedure").suppress() + identifier + lpar + rpar + block
procedure.set_parse_action(Procedure.create)
'''

with open("t2.txt", "r") as reader:
    contents = reader.read()
    f = expr.parse_string('x+y+z')
    print(f[0])
