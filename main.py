from pysmt.shortcuts import *
from parser import *
from thread import *
from initialiser import initialise
from lark import Lark
import sys


def main():
    if len(sys.argv) != 2:
        print('Usage: main.py filename')

    # parse test file
    lark = Lark(grammar, parser='lalr', transformer=Transform())
    with open(sys.argv[1], 'r') as reader:
        program = lark.parse(reader.read()).children[0]

    # extract information from parse results
    pre = program[0]  # program precondition
    post = program[1]  # program postcondition
    global_vars = program[2]  # list of global vars specified in the test file
    procedures: list[Procedure] = program[3:]  # list of parallel procedures

    # print parse results
    # print('=' * 8 + ' PARSE RESULTS ' + '=' * 9)
    # print('pre: ' + str(pre))
    # print('post: ' + str(post))
    # print('globals: ' + str(global_vars))
    # for t in procedures:
    #     print()
    #     print(t.pretty())

    # construct thread objects (currently, each thread has only one procedure)
    threads = []
    thread_count = 1
    for proc in procedures:
        threads.append(Thread(thread_count, proc))
        thread_count += 1

    # perform pre-computation on threads
    # this allocates useful information to the CFG nodes
    initialise(threads, global_vars)

    # todo: perform analysis
    # perform one iteration and print results
    fixpoint_reached = False
    while not fixpoint_reached:
        fixpoint_reached = True
        for t in threads:
            t.stable_sp_proof(pre)
            if not t.fixpoint_reached:
                fixpoint_reached = False
    local_posts = [t.procedure.eof.pre for t in threads]
    program_post = And(local_posts)

    for t in threads:
        print()
        print(t.procedure.pretty_proof())
    print()
    print('Derived Postcondition: ' + str(simplify(program_post).serialize()))
    print()
    if is_sat(And(program_post, Not(post))):
        print('Verification Unsuccessful.')
    else:
        print('Verification Successful!')

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


if __name__ == '__main__':
    main()
