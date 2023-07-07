from pysmt.shortcuts import *
from typing import List

class Thread:
    def __init__(self, t_id, procedure):
        # program counter symbol of the thread
        self.pc_symb = Symbol('pc_' + str(t_id), INT)
        # root procedure
        self.procedure = procedure
        # true iff the thread has reached a fixpoint
        # A fixpoint for the thread is reached when the preconditions of all its
        # global assignments reach a fixpoint. For now however, for ease of
        # implementation, we check all statements except conditionals.
        self.fixpoint_reached = False
        # the set of local variables of this thread
        self.local_vars = set()

    def stable_sp_proof(self, pre):
        self.fixpoint_reached = True
        return self.procedure.regenerate_proof(pre)


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
        # the thread this statement is in
        self.thread = None

    def regenerate_proof(self, pre):
        updated_pre = False
        # first, check if the given precondition is weaker than the current one
        if is_sat(And(pre, Not(self.pre))):
            # new precondition contains states not captured by old precondition
            # since assertions are only weakened, we should have old ==> new
            assert not is_sat(And(self.pre, Not(pre)))
            self.pre = pre
            updated_pre = True
        # now check stability
        for assign in self.interfering_assignments:
            image = assign.compute_sp_interfere(self.pre)
            if is_sat(And(image, Not(self.pre))):
                # precondition is unstable - stabilise it
                self.pre = Or(self.pre, image)
                updated_pre = True
        # return the cached postcondition if the precondition hasn't changed
        if updated_pre:
            self.post = self.compute_sp()
            self.thread.fixpoint_reached = False
        return self.post

    def compute_sp(self):
        return self.pre

    def pretty(self) -> str:
        return ""

    def pretty_proof(self) -> str:
        return '{' + str(self.pre) + '}' + '\n' + self.pretty()


class Procedure:
    def __init__(self, name: str, block: List[Statement]):
        self.name = name
        self.block = block
        self.eof = Eof()

    def regenerate_proof(self, pre):
        for stmt in self.block:
            pre = stmt.regenerate_proof(pre)
        return self.eof.regenerate_proof(pre)

    def pretty(self):
        body = "".join(['\n' + s.pretty() for s in self.block])
        body = body.replace('\n', '\n' + ' ' * 4)
        return "procedure " + self.name + "() {" + body + "\n" + "}"

    def pretty_proof(self):
        body = "".join(['\n' + s.pretty_proof() for s in self.block + [self.eof]])
        body = body.replace('\n', '\n' + ' ' * 4)
        return "procedure " + self.name + "() {" + body + "\n" + "}"


class Assignment(Statement):
    def __init__(self, left, right):
        super().__init__()
        self.left = left  # a symbol
        self.right = right  # an arithmetic expression or symbol
        # reachable instructions in the CFG, necessary for auxiliary variables
        self.reachable_pcs = TRUE()

    def pretty(self):
        return str(self.pc) + ": " + str(self.left) + " := " + str(self.right) + ";"

    def compute_sp(self):
        """
        sp(x := E, P) = exists y :: x == E[x <- y] && P[x <- y]
        """
        y = FreshSymbol(INT)
        body = And(Equals(self.left, self.right.substitute({self.left: y})),
                   self.pre.substitute({self.left: y}))
        eliminated = qelim(Exists([y], body), 'z3')
        assert not eliminated.is_quantifier()
        return eliminated

    def compute_sp_interfere(self, env_pred):
        """
        Where P = pre, Q = env_pred, L = thread.local_vars, R = reachable_pcs,
        A = P && Q, k = self.pc, pc = thread.pc_symb, and y is fresh:
        sp_interfere(x := E, A)
        = (exists y, L, pc :: x == E[x <- y] && A[x <- y] && pc == k) && R
        """
        pc_symb = self.thread.pc_symb
        y = FreshSymbol(INT)
        quantified_vars = [y] + list(self.thread.local_vars) + [pc_symb]
        body = And([Equals(self.left, self.right.substitute({self.left: y})),
                    And(self.pre, env_pred).substitute({self.left: y}),
                    Equals(pc_symb, Int(self.pc))])
        existential = Exists(quantified_vars, body)
        eliminated = qelim(existential, 'z3')
        assert not eliminated.is_quantifier()
        return And(eliminated, self.reachable_pcs)


class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return str(self.pc) + ": " + "assume " + str(self.cond) + ";"

    def compute_sp(self):
        """
        sp(assume E, P) = P && E
        """
        return And(self.pre, self.cond)


class Assertion(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def pretty(self):
        return str(self.pc) + ": " + "assert " + str(self.cond) + ";"

    def compute_sp(self):
        """
        sp(assert E, P) = E ==> P
        """
        return Implies(self.cond, self.pre)


class Conditional(Statement):
    def __init__(self, cond, true_block: List[Statement],
                 false_block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.true_block = true_block
        self.false_block = false_block
        self.true_block_post = FALSE()
        self.false_block_post = FALSE()

    def regenerate_proof(self, pre):
        # first, check if the given precondition is weaker than the current one
        if is_sat(And(pre, Not(self.pre))):
            # new precondition contains states not captured by old precondition
            # since assertions are only weakened, we should have old ==> new
            assert not is_sat(And(self.pre, Not(pre)))
            self.pre = pre
        # now check stability
        for assign in self.interfering_assignments:
            image = assign.compute_sp_interfere(self.pre)
            if is_sat(And(image, Not(self.pre))):
                # precondition is unstable - stabilise it
                self.pre = Or(self.pre, image)
        # regenerate proofs for the blocks
        true_post = And(self.pre, self.cond)
        for stmt in self.true_block:
            true_post = stmt.regenerate_proof(true_post)
        false_post = And(self.pre, Not(self.cond))
        for stmt in self.false_block:
            false_post = stmt.regenerate_proof(false_post)
        self.true_block_post = true_post
        self.false_block_post = false_post
        # Since we don't know if the pre of a statement within a block changed
        # without doing comparisons between true_block and self.true_block_post,
        # we always update self.post here and assert it is weaker than before.
        post = self.compute_sp()
        assert not is_sat(And(self.post, Not(post)))
        self.post = post
        return self.post

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

    def pretty_proof(self):
        true_body = "".join(['\n' + s.pretty_proof() for s in self.true_block])
        true_body = true_body.replace('\n', '\n' + ' ' * 4)
        false_body = "".join(['\n' + s.pretty_proof() for s in self.false_block])
        false_body = false_body.replace('\n', '\n' + ' ' * 4)
        pc = str(self.pc) + ": "
        whole_statement = pc + "if (" + str(self.cond) + ") {" + true_body + \
                          "\n} else {" + false_body + "\n}"
        whole_statement = whole_statement.replace('\n', '\n' + ' ' * len(pc))
        return '{' + str(self.pre) + '}' + '\n' + whole_statement

    def compute_sp(self):
        """
        sp(if B then S1 else S2, P)
            = sp(S1, B && P) || sp(S2, !B && P)
        where:
            sp(S1, B && P) = true_block_post
            sp(S2, !B && P) = false_block_post
        """
        return Or(self.true_block_post, self.false_block_post)


class Eof(Statement):
    def __init__(self):
        super().__init__()

    def pretty(self) -> str:
        return "E"
