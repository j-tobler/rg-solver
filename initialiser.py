from pysmt.shortcuts import *
from thread import *


def initialise(threads: list[Thread], global_vars):
    init_program_counters(threads)
    init_reachable_pcs(threads)
    global_assigns = init_global_assignments(threads, global_vars)
    init_interfering_assignments(threads, global_assigns)

    print_info(threads)


def recurse_cfg(node, function):
    """
    Applies the given function to all statements in this cfg.
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


def init_program_counters(threads: list[Thread]):
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
        recurse_cfg(t.procedure, pc_initialiser)


def init_reachable_pcs(threads: list[Thread]):
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
    branch_stack = []

    def reachable_pc_initialiser(node):
        if isinstance(node, Conditional) and node.false_block:
            max_true_pc = get_last_pc_in_true_block(node)
            max_false_pc = get_last_pc_in_false_block(node)
            first_interval = pc_intervals.pop(0)
            pc_intervals.insert(0, [max_false_pc + 1, first_interval[1]])
            pc_intervals.insert(0, [first_interval[0] + 1, max_true_pc])
            branch_stack.append(max_true_pc + 1)
        else:
            pc_intervals[0][0] += 1
            end_of_block = False
            if pc_intervals[0][0] > pc_intervals[0][1] != -1:
                pc_intervals.pop(0)
                end_of_block = True
            if isinstance(node, Assignment):
                formula = intervals_to_formula(pc_intervals, thread.pc_symb)
                node.reachable_pcs = formula
            if end_of_block and branch_stack:
                # reached end of true branch
                else_pc = branch_stack.pop()
                pc_intervals[0][0] = else_pc

    for t in threads:
        thread = t
        pc_intervals = [[1, -1]]
        branch_stack = []
        recurse_cfg(t.procedure, reachable_pc_initialiser)


def init_global_assignments(threads: list[Thread], global_vars):
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
        recurse_cfg(t.procedure, global_assignments_initialiser)
        thread_to_global_assigns[t] = global_assigns

    return thread_to_global_assigns


def init_interfering_assignments(threads: list[Thread], global_assigns):
    """
    Attaches to each statement a list of all other program statements that may
    destabilise its precondition. This list is all global assignments in the
    environment.
    """
    interfering_assigns = []

    def interfering_assignments_initialiser(node):
        node.interfering_assignments.update(interfering_assigns)

    for t in threads:
        interfering_assigns = []
        for t2, assigns in global_assigns.items():
            if t2 != t:
                interfering_assigns.extend(assigns)
        recurse_cfg(t.procedure, interfering_assignments_initialiser)

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

# =========================== Testing ============================

def print_info(threads: list[Thread]):
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
        recurse_cfg(t.procedure, print_node_info)
