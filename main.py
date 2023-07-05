from pysmt.shortcuts import *
from parser import *
from thread import *
from lark import Lark
import sys


def main():
    if len(sys.argv) != 2:
        print('Usage: main.py test_file')
    with open(sys.argv[1], 'r') as reader:
        # parse target program file
        lark = Lark(grammar, parser='lalr', transformer=Transform())
        program = lark.parse(reader.read()).children[0]
        # extract information from parse results
        pre = program[0]
        post = program[1]
        global_vars = program[2]
        procedures: list[Procedure] = program[3:]

        # print parse results
        print('=' * 8 + ' PARSE RESULTS ' + '=' * 9)
        print('pre: ' + str(pre))
        print('post: ' + str(post))
        print('globals: ' + str(global_vars))
        for t in procedures:
            print()
            print(t.pretty())

        # construct thread objects
        threads = []
        thread_count = 1
        for proc in procedures:
            threads.append(Thread(thread_count, proc))
            thread_count += 1

        # initialise cfg node information

        global_assigns = get_global_assignments(threads, global_vars)
        print('=' * 6 + ' GLOBAL ASSIGNMENTS ' + '=' * 6)
        for key, value in global_assigns.items():
            print(key.procedure.name + ":")
            for v in value:
                print('\t' + v.pretty())

        initialise(threads, global_assigns)

        # print parse results
        print('=' * 8 + ' PARSE RESULTS ' + '=' * 9)
        print('pre: ' + str(pre))
        print('post: ' + str(post))
        print('globals: ' + str(global_vars))
        for t in procedures:
            print()
            print(t.pretty())



        # allocate node information




def contains_symbol(lst, symbol):
    contains = False
    for x in lst:
        if is_valid(Equals(x, symbol)):
            contains = True
    return contains


def get_global_assignments(threads, global_vars):
    global_assigns = {}
    for t in threads:
        t_global_assigns = []
        global_assignments_helper(t.procedure, t_global_assigns, global_vars)
        global_assigns[t] = t_global_assigns
    return global_assigns


def global_assignments_helper(node, global_assigns, global_vars):
    if isinstance(node, Procedure):
        for n in node.block:
            global_assignments_helper(n, global_assigns, global_vars)
    elif isinstance(node, Conditional):
        for n in node.true_block:
            global_assignments_helper(n, global_assigns, global_vars)
        for n in node.false_block:
            global_assignments_helper(n, global_assigns, global_vars)
    elif isinstance(node, Assignment):
        if contains_symbol(global_vars, node.left):
            global_assigns.append(node)


def initialise(threads, global_assigns):
    for t in threads:
        pc = 1
        interfering_assigns = []
        for other_t, assigns in global_assigns.items():
            if other_t != t:
                interfering_assigns.extend(assigns)
        initialise_helper(t.procedure, pc, interfering_assigns)


def initialise_helper(node, init_pc, interfering_assigns):
    if isinstance(node, Procedure):
        pc = init_pc
        for n in node.block:
            pc = initialise_helper(n, pc, interfering_assigns)
    elif isinstance(node, Conditional):
        node.interfering_assignments.update(interfering_assigns)
        node.pc = init_pc
        pc = init_pc + 1
        for n in node.true_block:
            pc = initialise_helper(n, pc, interfering_assigns)
        for n in node.false_block:
            pc = initialise_helper(n, pc, interfering_assigns)
    else:
        node.interfering_assignments.update(interfering_assigns)
        node.pc = init_pc
        pc = init_pc + 1
    return pc


if __name__ == '__main__':
    main()
