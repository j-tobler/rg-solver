from pysmt.shortcuts import *
from thread import *


def initialise(thread: Thread):
    intervals = [[1, -1]]
    intervals_map = {}
    initialise_helper(thread.procedure, intervals, intervals_map)

def initialise_helper(node, init_intervals, intervals_map):
    if isinstance(node, Procedure):
        for n in node.block:
            intervals = init_intervals
            intervals = initialise_helper(n, intervals, intervals_map)
    elif isinstance(node, Conditional):
        intervals_map[node] = init_intervals
        pc_true_block_start = node.true_block[0]  # what if the block is empty??

        true_block_intervals = init_intervals  # todo: deep copy?
        true_block_intervals[0][0] = true_block_intervals[0][0] + 1
        false_block_intervals = init_intervals
        false_block_intervals[0][0] = false_block_intervals[0][0] + 1


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
    return intervals