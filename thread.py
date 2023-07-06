from pysmt.shortcuts import *
from typing import List

class Thread:
    def __init__(self, t_id, procedure):
        # program counter symbol of the thread
        self.pc_symb = Symbol('pc_' + str(t_id), INT)
        # root procedure
        self.procedure = procedure


class Statement:
    def __init__(self):
        # To represent the proof outline, every statement stores its
        # precondition. Initially, all assertions in the proof are false.
        self.pre = FALSE()
        # cached postcondition, to avoid recomputing identical postconditions
        self.post = FALSE()
        # the set of all assignment statements in other threads, where the
        # variable being assigned is global
        self.interfering_assignments: set[Assignment] = set()
        # program counter of this statement
        self.pc = -1

    def regenerate_precondition(self, new_pre):
        """
        When regenerating a proof, each node performs the following steps:
        1. Receive a new precondition from the previous node.
        2. Replace the current precondition with the new one, if the new one is
        weaker.
        3. Stabilise the precondition.
        4. If the precondition has been updated by (2) or (3), recompute the
        postcondition.
        5: Pass this postcondition to the next node.
        """
        updated_pre = False
        # first, check if the given precondition is weaker than the current one
        if is_sat(And(new_pre, Not(self.pre))):
            # new precondition contains states not captured by old precondition
            # since assertions are only weakened, we should have old ==> new
            assert not is_sat(And(self.pre, Not(new_pre)))
            self.pre = new_pre
            updated_pre = True
        # now check stability
        for assign in self.interfering_assignments:

            if is_sat(And(..., Not(self.pre))):
                # precondition is unstable - stabilise it
                image = ...
        if updated_pre:
            # update post
            # involves eliminating quantifiers
            ...
        return self.post

    def compute_sp(self, pre):
        pass

    def pretty(self) -> str:
        return ""

    def pretty_proof(self) -> str:
        return '{' + str(self.pre) + '}' + '\n' + self.pretty()


class Procedure:
    def __init__(self, name: str, block: List[Statement]):
        self.name = name
        self.block = block
        self.eof = Eof()

    def get_name(self):
        return self.name

    def pretty(self):
        body = "".join(['\n' + s.pretty() for s in self.block])
        body = body.replace('\n', '\n' + ' ' * 4)
        return "procedure " + self.name + "() {" + body + "\n" + "}"


class Assignment(Statement):
    def __init__(self, left, right):
        super().__init__()
        self.left = left  # a symbol
        self.right = right  # an arithmetic expression or symbol
        self.local_vars = set()  # the local vars of this assignment's thread
        # reachable instructions in the CFG, necessary for auxiliary variables
        self.reachable_pcs = TRUE()

    def pretty(self):
        return str(self.pc) + ": " + str(self.left) + " := " + str(self.right) + ";"

    def compute_sp(self, pre):
        # sp(x := E, P) = sp(x := E, pc := k) where k is the pc of this stmt
        # = exists y, z :: x == E[x\y] && pc == k && P[x\y, pc\z]
        y = FreshSymbol(INT)
        z = FreshSymbol(INT)
        first_conjunct = Equals(self.left, self.right.substitute(self.left, y))
        second_conjunct = Equals(self.pc_symb, )
        third_conjunct = pre.substitute({self.left: y, self.pc_symb: z})
        return Exists([y], And(first_conjunct, second_conjunct))

    def compute_sp_interfere(self, pre):
        # sp_interfere(x := E, P)
        # = exists y, z, L :: x == E[x\y] && pc in R && P[x\y, pc\z]
        # where:
        #     k is the pc of this assignment statement
        #     R is the set of reachable PCs in the CFG, including k
        #     L is the set of local variables of this thread, excluding pc
        y = FreshSymbol(INT)
        quantified_vars = [y] + list(self.local_vars)
        first_conjunct = Equals(self.left, self.right.substitute(self.left, y))
        second_conjunct = pre.substitute(self.left, y)
        third_conjunct = ...
        pass


class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return str(self.pc) + ": " + "assume " + str(self.cond) + ";"

    def compute_sp(self, pre):
        # sp(assume E, P) = P && E
        return And(pre, self.cond)


class Assertion(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return str(self.pc) + ": " + "assert " + str(self.cond) + ";"

    def compute_sp(self, pre):
        # sp(assert E, P) = E ==> P
        return Implies(self.cond, pre)


class Conditional(Statement):
    def __init__(self, cond, true_block: List[Statement],
                 false_block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.true_block = true_block
        self.false_block = false_block

    def pretty(self):
        true_body = "".join(['\n' + s.pretty() for s in self.true_block])
        true_body = true_body.replace('\n', '\n' + ' ' * 4)
        false_body = "".join(['\n' + s.pretty() for s in self.false_block])
        false_body = false_body.replace('\n', '\n' + ' ' * 4)
        pc = str(self.pc) + ": "
        whole_statement = pc + "if (" + str(self.cond) + ") {" + true_body + \
            "\n} else {" + false_body + "\n}"
        whole_statement = whole_statement.replace('\n', '\n' + ' ' * len(pc))
        return whole_statement

    def compute_sp(self, pre, block_sp):
        # sp(if B then S, P) = sp(skip, !B && P) || sp(S, B && P)
        # = (!B && P) || sp(S, B && P)
        first_disjunct = And(Not(self.cond), pre)
        return Or(first_disjunct, block_sp)


class Eof(Statement):
    def __init__(self):
        super().__init__()
