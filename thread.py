from pysmt.shortcuts import *
from typing import List


# Indent for printing proof outlines.
INDENT = 4

class Statement:
    """
    In this implementation, a procedure contains of a block of statements. All
    nodes in the CFG except Procedure nodes are statements. Statements can be:
    - Conditionals, which contain their own blocks of statements.
    - Assignment statements, which may be local or global.
    - Assume statements (Assumptions).
    - Assert statements (Assertions).
    - The special EOF 'E' statement that is appended to procedures.
    Each statement stores its precondition and a cached postcondition.
    Each statement also contains a function for recomputing its precondition as
    per the strongest-proof approach.
    """
    def __init__(self):
        # The precondition of this statement. Formally, a proof outline is a
        # list of <precondition, instruction> pairs.
        self.pre = FALSE()
        # Cached postcondition, to avoid recomputing identical postconditions.
        self.post = FALSE()
        # The program counter of this statement. -1 indicates an error.
        self.pc = -1
        # The thread this statement belongs to.
        self.thread = None

    def regenerate_proof(self, pre):
        """
        Recomputes the precondition of this statement.

        The parameter 'pre' represents the postcondition of the previous
        statement, and represents the tentative precondition of this statement.
        This tentative precondition must be a simplified first-order predicate.

        If this precondition contains states not captured by the current
        precondition, the latter must be updated to include these states. Then,
        if the current precondition is unstable, it must be stabilised via a
        weakening. If either of these steps results in a change to the current
        precondition, the cached postcondition must be updated via a strongest-
        postcondition derivation before it is passed to the next statement.

        For conditionals (and later, loops), the proof for the contained blocks
        must be regenerated before a postcondition can be derived. For
        simplicity, the cached postconditions for these statements are always
        updated, regardless of whether the proof for the inner block was
        changed. This is OK, since the SP transformers for these statements are
        quite simple (e.g. they do not contain quantifiers).
        """
        updated_pre = False
        # Check if the given precondition is weaker than the current one.
        if is_sat(And(pre, Not(self.pre))):
            # New precondition contains states not captured by old precondition.
            self.pre = simplify(Or(self.pre, pre))
            updated_pre = True
        # Check stability.
        for assign in self.thread.interfering_assignments:
            image = assign.compute_sp_interfere(self.pre)
            if is_sat(And(image, Not(self.pre))):
                # Precondition is unstable - stabilise it.
                self.pre = simplify(Or(self.pre, image))
                updated_pre = True
        # If the statement is a conditional, update the proofs of its blocks.
        if isinstance(self, Conditional):
            # Regenerate proof for the true-block.
            true_post = And(self.pre, self.cond)
            for stmt in self.true_block:
                true_post = stmt.regenerate_proof(true_post)
            # Regenerate proof for the false-block.
            false_post = And(self.pre, Not(self.cond))
            for stmt in self.false_block:
                false_post = stmt.regenerate_proof(false_post)
            # Store the postconditions of the contained blocks.
            self.update_block_postconditions(true_post, false_post)
            # Always recompute postcondition for conditionals.
            self.post = self.compute_sp()
        elif updated_pre:
            # For non-conditionals, only recompute post if pre hasn't changed.
            self.post = self.compute_sp()
        # If any statement's pre has been updated, a fixpoint is not reached.
        if updated_pre:
            self.thread.fixpoint_reached = False
        return self.post

    def compute_sp(self):
        return self.pre

    def get_proof_str(self, annotations=True):
        proof_str = ''
        if annotations:
            proof_str += '{' + str(self.pre) + '}\n'
        proof_str += str(self)
        if isinstance(self, Conditional):
            proof_str += ' {'
            body = ''
            for n in self.true_block:
                body += '\n'
                body += n.get_proof_str(annotations=annotations)
            body = body.replace('\n', '\n' + ' ' * INDENT)
            proof_str += body
            proof_str += '\n} else {'
            body = ''
            for n in self.false_block:
                body += '\n'
                body += n.get_proof_str(annotations=annotations)
            body = body.replace('\n', '\n' + ' ' * INDENT)
            proof_str += body
            proof_str += '\n}' if body else '}'
        return proof_str


class Procedure:
    def __init__(self, name: str, t_id, block: List[Statement]):
        # Human-readable name of this procedure.
        self.name = name
        # This procedure's list of statements.
        self.block = block
        # The special end-of-file 'E' statement, appended for analysis purposes.
        self.eof = Eof()
        # The program counter symbol of the thread. E.g. 'pc_3'.
        self.pc_symb = Symbol('pc_' + str(t_id), INT)
        # True iff the thread has reached a fixpoint.
        self.fixpoint_reached = False
        # The variables local to this thread.
        self.local_vars = []
        # The environment instructions that may interfere with this thread.
        self.interfering_assignments = []

    def regenerate_proof(self, pre):
        self.fixpoint_reached = True
        for stmt in self.block:
            pre = stmt.regenerate_proof(pre)
        return self.eof.regenerate_proof(pre)

    def __str__(self):
        return "procedure " + self.name + "()"

    def get_proof_str(self, annotations=True):
        body = ''
        for n in self.block:
            body += '\n'
            body += n.get_proof_str(annotations=annotations)
        body = body.replace('\n', '\n' + ' ' * INDENT)
        # Add program counters. These are always ordered contiguously from top
        # to bottom in a standard layout, as per main.init_program_counters.
        lines = body[1:].split('\n')
        max_pc = 0
        for line in lines:
            # It just so happens that this is a sufficient condition for
            # excluding line numbers.
            if '}' not in line:
                max_pc += 1
        std_length = len(str(max_pc)) + 2
        lines_with_pcs = []
        pc = 1
        for line in lines:
            pc_segment = ''
            if '}' not in line:
                pc_segment = str(pc) + ': '
                pc += 1
            pc_segment += ' ' * (std_length - len(pc_segment))
            lines_with_pcs.append('\n' + pc_segment + line)
        body = ''.join(s for s in lines_with_pcs)
        return ' ' * std_length + str(self) + ' {' + body + '\n' + \
               ' ' * std_length + '}' + '\n'


class Assignment(Statement):
    def __init__(self, left, right):
        super().__init__()
        self.left = left  # a symbol
        self.right = right  # an arithmetic expression or symbol
        # reachable instructions in the CFG, necessary for auxiliary variables
        self.reachable_pcs = TRUE()

    def __str__(self):
        return str(self.left) + " := " + str(self.right) + ";"

    def compute_sp(self):
        """
        sp(x := E, P) = exists y :: x == E[x <- y] && P[x <- y]
        """
        y = FreshSymbol(INT)
        body = And(Equals(self.left, self.right.substitute({self.left: y})),
                   self.pre.substitute({self.left: y}))
        eliminated = simplify(qelim(Exists([y], simplify(body)), 'z3'))
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
        existential = Exists(quantified_vars, simplify(body))
        eliminated = simplify(qelim(existential, 'z3'))
        assert not eliminated.is_quantifier()
        return And(eliminated, self.reachable_pcs)


class Assumption(Statement):
    def __init__(self, cond):
        super().__init__()
        self.cond = cond

    def __str__(self):
        return "assume " + str(self.cond) + ";"

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
        return "assert " + str(self.cond) + ";"

    def compute_sp(self):
        """
        sp(assert E, P) = E ==> P
        """
        return simplify(Implies(self.cond, self.pre))


class Conditional(Statement):
    def __init__(self, cond, true_block: List[Statement],
                 false_block: List[Statement]):
        super().__init__()
        self.cond = cond
        self.true_block = true_block
        self.false_block = false_block
        self.true_block_post = FALSE()
        self.false_block_post = FALSE()

    def update_block_postconditions(self, true_block_post, false_block_post):
        self.true_block_post = true_block_post
        self.false_block_post = false_block_post

    def regenerate_proof(self, pre):
        # first, check if the given precondition is weaker than the current one
        if is_sat(And(pre, Not(self.pre))):
            # new precondition contains states not captured by old precondition
            # since assertions are only weakened, we should have old ==> new
            assert not is_sat(And(self.pre, Not(pre)))
            self.pre = pre
        # now check stability
        for assign in self.thread.interfering_assignments:
            image = assign.compute_sp_interfere(self.pre)
            if is_sat(And(image, Not(self.pre))):
                # precondition is unstable - stabilise it
                self.pre = Or(self.pre, image)

        # Since we don't know if the pre of a statement within a block changed
        # without doing comparisons between true_block and self.true_block_post,
        # we always update self.post here and assert it is weaker than before.
        post = self.compute_sp()
        assert not is_sat(And(self.post, Not(post)))
        self.post = post
        return self.post

    def __str__(self):
        return "if (" + str(self.cond) + ")"

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
