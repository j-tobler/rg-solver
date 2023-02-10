from pysmt.shortcuts import *


# this probably isn't even necessary
class RgCondition:
    def __init__(self):
        self.conjuncts = []

    def build(self, i=0):
        if i == len(self.conjuncts):
            return TRUE
        if i == len(self.conjuncts) - 1:
            return self.conjuncts[i]
        return And(self.conjuncts[1], self.build(i + 1))

    def print(self):
        print(self.build())


# adds a prime to all free variables in the given formula
# to substitute the primed equivalent of x for y in formula f: f.substitute({primed(x): y})
def primed(f):
    return f.substitute({s: Symbol(str(s) + "'", s.get_type()) for s in f.get_free_variables()})


# removes all primes from the given variable
def unprimed(s):
    return Symbol(str(s).rstrip("'"), s.get_type())


# true iff the given variable is primed
def is_prime(s):
    return str(s)[-1] == "'"


# extracts all primed variables from the given iterable
# to extract all free primed variables from a formula: filter_primes(get_free_variables(formula))
def filter_primes(lst):
    return set(filter(is_prime, lst))


def stable_r(p, r):
    return Implies(And(p, r), primed(p))








"""
todo:
[x] find and replace within formulae
    find: get_free_variables() - excludes literals and bound variables
    replace: substitute()
[x] locating primed variables
[x] priming and un-priming variables
[x] stableR
[ ] re-read notes

parsing plaintext source code >:( (Thursday!)
[ ] parser grammar implementation
[ ] using the parser to generate SMT objects from text files

analysing the generated SMT object (Friday)
[ ] weakest-preconditions and strongest-postconditions
[ ] guar and wpg
[ ] generating basic rely conditions

implementing the algorithm (stage 1) (Friday)
[ ] generating contexts (may require some human input)
[ ] systematically generating and refining rely conditions for one thread, while storing upper and lower bounds

* theory break *

implementing the algorithm (stage 2) (Monday)
[ ] recursively refining rely conditions for two threads, storing and passing necessary information between calls
[ ] failure conditions

* partial prototype complete *

[ ] extending to more than 2 threads?
"""
