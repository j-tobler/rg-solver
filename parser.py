from lark import Transformer
from thread import *


grammar = """
    // Welcome to Lark!
    // Lark builds an AST using the following grammar. I'll provide some brief
    // explanations along the way, but this page is otherwise a great resource:
    // https://manpages.ubuntu.com/manpages/impish/man7/lark.7.html
    
    // This is a list of terminals. Terminals preceded by an underscore are
    // ignored in the tree. For example, since we have _IF and not IF, the node
    // for an if-statement is simply [<condition>, <body>] rather than
    // [if, <condition>, <body>]. This is illustrated in the implementation of
    // Transform.branch() later in the file, which converts this node to a
    // Conditional object, which we define in thread.py.
    _PRECONDITION: "precondition"
    _POSTCONDITION: "postcondition"
    _GLOBALS: "globals"
    _PROCEDURE: "procedure"
    _IF: "if"
    _ELSE: "else"
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

    // The top-level pattern Lark initially matches.
    start: program
    // Here, the * symbol means 0 or more. Lark automatically expands procedure*
    // to the standard recursive definition in EBNF.
    program: precondition postcondition globals procedure procedure*
    
    // Tokens wrapped in quotations like the colon here are omitted from the
    // generated AST, just like terminals with underlines.
    // We use impl here to denote a boolean expression, since an implication is
    // defined in terms of disjunctions, which are defined in terms of
    // conjunctions, and so on as per the order of operations. Note that
    // quantifiers are not currently supported in the grammar.
    precondition: _PRECONDITION ":" impl
    postcondition: _POSTCONDITION ":" impl
    globals: _GLOBALS ":" variable*
    
    // Procedures do not currently support parameters. The parentheses are just
    // a placeholder. CNAME is a predefined pattern that is imported at the
    // bottom of this grammar.
    procedure: _PROCEDURE CNAME "()" block
    
    // A block is zero or more of any of these statements.
    block: "{" (assign | branch | assume | assertion)* "}"
    
    // For the moment, variables may only be integers, and hence may only be
    // assigned to arithmetic expressions.
    assign: variable ":=" a_expr ";"
    
    // The parser does not currently support else blocks.
    branch: _IF "(" impl ")" block _ELSE block
    assume: _ASSUME impl ";"
    assertion: _ASSERT impl ";"
    
    // Expressions can be boolean or arithmetic. The question mark tells Lark to
    // ignore this node if it only has one child. Here, Lark will replace the
    // expr node with either an impl or a_expr node, compressing the tree.
    ?expr: impl | a_expr 
    
    // Similar to above, the question mark here says: If this implication is
    // simply a disjunction, then replace the implication node with the
    // disjunction node. We do this for all expression types so that the
    // transformer knows, for example, that a neg will always be of the form 
    // [NOT, neg], and never [atom]. This simplifies Transform.neg().
    ?impl: disj IMPLIES impl | disj
    ?disj: disj OR conj | conj
    ?conj: conj AND neg | neg
    ?neg: NOT neg | atom
    // This may include variables when bool variable types are supported.
    ?atom: "(" impl ")" | bool | comp
    bool: TRUE | FALSE
    // Arithmetic comparisons.
    comp: a_expr (LE | LT | GE | GT | EQ | NE) a_expr
    
    // Arithmetic expressions support the basic operators +,-,*,/
    ?a_expr: a_expr (PLUS | MINUS) term | term
    ?term: term (TIMES | DIV) num | num
    ?num: int_literal | variable
    int_literal: SIGNED_INT
    variable: CNAME
    
    // https://github.com/lark-parser/lark/blob/master/lark/grammars/common.lark
    %import common.CNAME
    %import common.WS
    %import common.SIGNED_INT
    %ignore WS
"""


class Transform(Transformer):
    """
    The transformer contains a set of methods for converting nodes of the same
    name in the (compressed) AST to the custom data types defined in thread.py.
    """
    def __init__(self):
        super().__init__()
        self.t_id = 0

    @staticmethod
    def program(args):
        return args

    @staticmethod
    def precondition(args):
        return args[0]

    @staticmethod
    def postcondition(args):
        return args[0]

    @staticmethod
    def globals(args):
        return args

    def procedure(self, args):
        self.t_id += 1
        return Procedure(str(args[0]), self.t_id, args[1])

    @staticmethod
    def block(args):
        return args

    @staticmethod
    def assign(args):
        return Assignment(args[0], args[1])

    @staticmethod
    def branch(args):
        return Conditional(args[0], args[1], args[2])

    @staticmethod
    def assume(args):
        return Assumption(args[0])

    @staticmethod
    def assertion(args):
        return Assertion(args[0])

    @staticmethod
    def impl(args):
        return Implies(args[0], args[2])

    @staticmethod
    def disj(args):
        return Or(args[0], args[2])

    @staticmethod
    def conj(args):
        return And(args[0], args[2])

    @staticmethod
    def neg(args):
        return Not(args[1])

    @staticmethod
    def atom(args):
        return args[0]

    @staticmethod
    def bool(args):
        return TRUE() if str(args[0]) == 'true' else FALSE()

    @staticmethod
    def comp(args):
        op = str(args[1])
        if op == '<=':
            return LE(args[0], args[2])
        if op == '<':
            return LT(args[0], args[2])
        if op == '>=':
            return GE(args[0], args[2])
        if op == '>':
            return GT(args[0], args[2])
        if op == '==':
            return Equals(args[0], args[2])
        if op == '!=':
            return NotEquals(args[0], args[2])

    @staticmethod
    def a_expr(args):
        op = str(args[1])
        if op == '+':
            return Plus(args[0], args[2])
        if op == '-':
            return Minus(args[0], args[2])

    @staticmethod
    def term(args):
        op = str(args[1])
        if op == '*':
            return Times(args[0], args[2])
        if op == '/':
            return Div(args[0], args[2])

    @staticmethod
    def int_literal(args):
        return Int(int(args[0]))

    @staticmethod
    def variable(args):
        return Symbol(str(args[0]), INT)
