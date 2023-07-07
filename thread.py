from pysmt.shortcuts import *
from typing import List

class Thread:
    def __init__(self, t_id, procedure):
        # program counter symbol of the thread
        self.pc_symb = Symbol('pc_' + str(t_id), INT)
        # root procedure
        self.procedure = procedure
        # true iff the thread has reached a fixpoint
        self.fixpoint_reached = False
        # the set of local variables of this thread
        self.local_vars = set()

    def stable_sp_proof(self, pre):
        self.procedure.stable_sp_proof(pre)


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

    def regenerate_precondition(self, new_pre):
        """
        When regenerating a proof, each node performs the following steps:
        1. Receive a new precondition from the previous node.
           (This will be simple first-order predicate.)
        2. If the new precondition is weaker, replace the current one with it.
        3. If it is unstable, replace it with its stabilisation.
           (The returned stabilisation should also be a first-order predicate.
           In this method, checking stability requires quantifier elimination.)
        4. If it has been updated by (2) or (3), recompute the postcondition.
           (Eliminate quantifiers before returning post.)
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
            post = assign.compute_sp_interfere(self.pre)
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

    def stable_sp_proof(self, pre):
        pass

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

    def compute_sp_interfere(self, env_pred):
        # Where P = pre, Q = env_pred, L = thread.local_vars, R = reachable_pcs,
        # A = P && Q, k = self.pc, pc = thread.pc_symb, and y is fresh:
        # sp_interfere(x := E, A)
        # = (exists y, L, pc :: x == E[x\y] && A[x\y] && pc == k) && R
        pc_symb = self.thread.pc_symb
        y = FreshSymbol(INT)
        quantified_vars = [y] + list(self.thread.local_vars) + [pc_symb]
        body = And([Equals(self.left, self.right.substitute({self.left: y})),
                    And(self.pre, env_pred).substitute({self.left: y}),
                    Equals(pc_symb, Int(self.pc))])
        existential = Exists(quantified_vars, body)
        eliminated = qelim(existential, 'z3')
        assert eliminated.is_quantifier()
        return And(eliminated, self.reachable_pcs)


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
