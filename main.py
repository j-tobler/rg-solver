from parser import *
from thread import *
from lark import Lark
import sys
from colorama import Fore


def main():
    if len(sys.argv) != 2:
        print('Usage: main.py filename')

    # Parse test file.
    program = parse_test_file(sys.argv[1])
    specified_precondition = program[0]
    specified_postcondition = program[1]
    global_variables = program[2]
    threads: list[Procedure] = program[3:]

    # Pre-compute necessary CFG-node information.
    # Allocate a unique program counter to each node in the CFG.
    init_program_counters(threads)
    # Allocate to assignment nodes the set of PCs they can reach in the CFG.
    init_reachable_pcs(threads)
    # Get the list of global assignments contained in each thread.
    global_assignments: dict[Procedure, list[Assignment]] = \
        init_global_assignments(threads, global_variables)
    # Allocate to each thread the list of environment global assignments.
    init_interfering_assignments(threads, global_assignments)
    # Allocate to each node the thread it belongs to.
    init_owner_thread(threads)
    # Allocate to each thread the set of local variables that appear in it.
    init_local_vars(threads, global_variables)
    # Verify that all local and global variable names are legal.
    verify_variable_names(threads, global_variables)

    # Perform analysis.
    fixpoint_reached = False
    while not fixpoint_reached:
        fixpoint_reached = True
        for t in threads:
            t.regenerate_proof(specified_precondition)
            if not t.fixpoint_reached:
                fixpoint_reached = False
    local_posts = [t.eof.pre for t in threads]
    program_post = And(local_posts)

    for t in threads:
        print()
        print(t.get_proof_str())
    print()
    print('Derived Postcondition: ' + str(simplify(program_post).serialize()))
    print()
    if is_sat(And(program_post, Not(specified_postcondition))):
        print(f'{Fore.RED}Verification Unsuccessful.{Fore.RESET}')
    else:
        print(f'{Fore.GREEN}Verification Successful!{Fore.RESET}')

    """
    Problem
    
    The current algorithm disjunctively merges images from interference to
    unstable assertions. This means we can't verify cases like mutual increment,
    where the postcondition cannot be satisfied by any thread in isolation.
    
    To improve completeness, we cannot directly disjoin images. We need to do a
    refinement like:
    (pc <= k ==> Q) && (pc > k ==> img)
    However, this may affect soundness or efficiency. For example, the env may
    be able to transition from pc <= k to !img under a different precondition
    than Q. This needs more investigation.
    
    In general, this code needs to be significantly cleaned up, simplified and
    documented. Generated predicates need to be simplified on the fly to ease
    existential elimination. In future, we may aid this elimination further by
    strategically distributing the existential over its disjuncts in DNF, or
    a similar divide-and-conquer strategy. We must also find a way to add a knob
    to the level of the abstraction used in deriving interference images. There
    is also plenty of room for optimisation in many of the subroutines contained
    in this algorithm. For example, a lot of objects store data they don't need
    to.
    """


def parse_test_file(filename):
    lark = Lark(grammar, parser='lalr', transformer=Transform())
    with open(filename, 'r') as reader:
        return lark.parse(reader.read()).children[0]


def recurse_cfg(node, function):
    """
    Applies the given function to all statements in this CFG, except EOFs.
    This function is used liberally throughout this file to apply particular
    initialisation procedures to all statements in the CFG in this order.
    """
    if isinstance(node, Procedure):
        for stmt in node.block:
            recurse_cfg(stmt, function)
    elif isinstance(node, Conditional):
        function(node)
        for stmt in node.true_block:
            recurse_cfg(stmt, function)
        for stmt in node.false_block:
            recurse_cfg(stmt, function)
    else:
        function(node)


def init_program_counters(threads: list[Procedure]):
    """
    Provides each statement with a unique program counter.

    Technically, for this analysis, only global assignment statements require
    program counters. This is because PCs are only used when strengthening
    the image of an interfering transition such to constrain the range of
    possibly-interfering instructions the environment may execute from that
    point. Since only global assignments can cause interference, only their PCs
    will appear in proof outlines and be useful in this purpose of eliminating
    impossible interference.
    """
    pc = [1]

    def pc_initialiser(node):
        node.pc = pc[0]
        pc[0] += 1

    for t in threads:
        pc[0] = 1
        recurse_cfg(t, pc_initialiser)


def init_reachable_pcs(threads: list[Procedure]):
    """
    When an assertion is destabilised, the image of the interference needs to
    have conjoined to it a restriction on the future value of the interfering
    thread's program counter. This requires all global assignments to contain
    a set of program counters they can reach in the CFG. For simplicity, we
    attach this information to every assignment in general.

    Generating this set is quite tricky. This algorithm traverses the CFG with
    a reference to a list of intervals that denote the possible future PC range.
    This list of intervals is updated at each instruction, depending on the type
    of that instruction. Upon entering the true-block of a conditional, the
    range must be updated so as to exclude reachability of the else-block, and
    vice-versa. The specific implementation here assumes that PCs are ordered
    precisely in the manner they are generated by init_program_counters.
    """
    thread = threads[0]
    pc_intervals = [[1, -1]]
    # Each time the true block of a conditional is entered/exited, this stack
    # pushes/pops the first PC of the false block. This is necessary for
    # adding false-block PCs to the set of reachable PCs when the true block
    # is exited and false block is entered in the recurse_cfg traversal.
    branch_stack = []

    def reachable_pc_initialiser(node):
        # conditionals with empty false-blocks can be treated like regular stmts
        if isinstance(node, Conditional) and node.false_block:
            # PCs of the final statements in the true-block and false-block
            last_true_block_pc = get_last_pc_in_true_block(node)
            last_false_block_pc = get_last_pc_in_false_block(node)
            # upon entering the true-block, we want to split the first interval
            first_interval = pc_intervals.pop(0)
            # split it such to avoid the PCs of the false-block statements
            pc_intervals.insert(0, [last_false_block_pc + 1, first_interval[1]])
            pc_intervals.insert(0, [first_interval[0] + 1, last_true_block_pc])
            # record the first PC of the false-block
            branch_stack.append(last_true_block_pc + 1)
        else:
            # we want an exclusive range, so increment the lower bound
            pc_intervals[0][0] += 1
            # True iff this statement is the last of a true-block of a
            # conditional with a non-empty false-block, OR is the last statement
            # of a procedure.
            end_of_block = False
            if pc_intervals[0][0] > pc_intervals[0][1] != -1:
                # We've reached the end of a block and the first interval is no
                # longer valid.
                pc_intervals.pop(0)
                end_of_block = True
            if isinstance(node, Assignment):
                # Only assignments record their set of reachable PCs in the CFG.
                # This set is recorded as a concise logical formula.
                formula = intervals_to_formula(pc_intervals, thread.pc_symb)
                node.reachable_pcs = formula
            if end_of_block and branch_stack:
                # since branch_stack != [], we're at the end of a true-block
                else_pc = branch_stack.pop()
                pc_intervals[0][0] = else_pc

    for t in threads:
        thread = t
        pc_intervals = [[1, -1]]
        branch_stack = []
        recurse_cfg(t, reachable_pc_initialiser)


def init_global_assignments(threads: list[Procedure], global_vars):
    """
    Returns a dictionary of {thread -> list[Assignment]} that maps each thread
    to a list of its contained global assignments. This is necessary because we
    want to eventually provide each program statement with a list of statements
    which may destabilise their preconditions - that is, a list of environment
    assignments to global variables (see init_interfering_assignments).
    """
    thread_to_global_assigns = {}
    global_assigns = []

    def global_assignments_initialiser(node):
        if isinstance(node, Assignment) and symbol_in(node.left, global_vars):
            global_assigns.append(node)

    for t in threads:
        global_assigns = []
        recurse_cfg(t, global_assignments_initialiser)
        thread_to_global_assigns[t] = global_assigns

    return thread_to_global_assigns


def init_interfering_assignments(threads: list[Procedure], global_assigns):
    """
    Attaches to each thread a list of all environment instructions that may
    destabilise one of its assertions. This list happens to be the list of
    all global assignments in the environment.
    """
    for t in threads:
        interfering_assigns = []
        for t2, assigns in global_assigns.items():
            if t2 != t:
                interfering_assigns.extend(assigns)
        t.interfering_assignments = interfering_assigns


def init_owner_thread(threads: list[Procedure]):
    """
    Provides each statement with the thread it is in.
    """
    def owner_thread_initialiser(node):
        node.thread = t

    for t in threads:
        recurse_cfg(t, owner_thread_initialiser)
        t.eof.thread = t  # EOF statements also need to know their threads.


def init_local_vars(threads: list[Procedure], global_vars):
    """
    Provides each thread with a list of its local variables.
    """

    def get_vars(node):
        if isinstance(node, Assignment):
            add_if_distinct([node.left], vars_used)
            add_if_distinct(get_free_variables(node.right), vars_used)
        else:
            add_if_distinct(get_free_variables(node.cond), vars_used)

    for t in threads:
        vars_used = []
        recurse_cfg(t, get_vars)
        t.local_vars = \
            set(filter(lambda x: not symbol_in(x, global_vars), vars_used))

    # Check that all local variables are unique.
    duplicate = None
    for t in threads:
        for t2 in threads:
            if t2 != t:
                for v in t.local_vars:
                    if symbol_in(v, t2.local_vars):
                        duplicate = v
    if duplicate:
        exit(f'Error: Duplicate local variable: {str(duplicate)}.\n'
             f'Local variables must be distinct.')


def verify_variable_names(threads: list[Procedure], global_vars):
    """
    Verifies that all program variable names are legal.
    """
    illegal_prefixes = ['pc']
    variables = []
    variables.extend(global_vars)
    for t in threads:
        variables.extend(t.local_vars)
    illegal_vars = False
    for v in variables:
        for s in illegal_prefixes:
            if str(v).startswith(s):
                print(f'Variable {str(v)} has an illegal name.')
                illegal_vars = True
    if illegal_vars:
        exit('Error: Discovered a variable with an illegal name.')

# ======================= Helper Functions =======================

def get_last_pc_in_true_block(branch: Conditional):
    """
    Returns the maximum pc of any instruction in the true block of this branch.
    """
    last_stmt = branch.true_block[-1]
    if isinstance(last_stmt, Conditional):
        return get_last_pc_in_false_block(last_stmt)
    return last_stmt.pc


def get_last_pc_in_false_block(branch: Conditional):
    """
    Returns the maximum pc of any instruction in the false block of this branch.
    """
    if not branch.false_block:
        return get_last_pc_in_true_block(branch)
    last_stmt = branch.false_block[-1]
    if isinstance(last_stmt, Conditional):
        return get_last_pc_in_false_block(last_stmt)
    return last_stmt.pc


def intervals_to_formula(intervals, pc_symbol):
    disjuncts = []
    for i in intervals:
        if i[1] == -1:
            disjuncts.append(LE(Int(i[0]), pc_symbol))
        elif i[0] < i[1]:
            disjuncts.append(And(LE(Int(i[0]), pc_symbol),
                                 LE(pc_symbol, Int(i[1]))))
        elif i[0] == i[1]:
            disjuncts.append(Equals(pc_symbol, Int(i[0])))
    return Or(disjuncts)


def symbol_in(symbol, lst):
    """
    Checks if the given list contains the given symbol.
    This is necessary because symbols must be compared with Equals and not with
    '==', 'is' or 'in'. Often, we may have two of the same symbol with different
    memory addresses, but we'd like to treat them as the same symbol.
    """
    contains = False
    for x in lst:
        if is_valid(Equals(x, symbol)):
            contains = True
    return contains


def add_if_distinct(symbols, lst):
    """
    Adds all given symbols to the list of symbols that are not already in the
    list.
    """
    for s in symbols:
        if not symbol_in(s, lst):
            lst.append(s)

# =========================== Testing ============================

def print_info(threads: list[Procedure]):

    def print_node_info(node):
        if isinstance(node, Conditional):
            print('Conditional:')
        elif isinstance(node, Assertion):
            print('Assertion:')
        elif isinstance(node, Assumption):
            print('Assumption:')
        elif isinstance(node, Assignment):
            print('Assignment:')
        else:
            exit('Unknown Statements')
        print(node.pretty())
        print('PC = ' + str(node.pc))
        interfering_assigns = [i.pretty() for i in
                               node.interfering_assignments]
        print('Interfering Assignments = ' + str(interfering_assigns))
        if isinstance(node, Assignment):
            print('Reachable PCs = ' + str(node.reachable_pcs))
        print()

    for t in threads:
        recurse_cfg(t, print_node_info)


if __name__ == '__main__':
    main()
