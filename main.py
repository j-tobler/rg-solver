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


if __name__ == '__main__':
    main()
