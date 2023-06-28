"""
One of the key issues in the strongest-proof approach is constructing assertions
in a way that both facilitates relational states such as x > y, as well as
simple SP transformations. The standard SP transformer for assignments is
rather complicated, and may impede efficiency or even feasibility of verifying
concurrent programs.

In this algorithm, assertions are represented plainly as in Hoare proofs. Hence,
it uses the standard existentially quantified SP transformer. Moreover, the
local variables of environment threads in the images of interfering transitions
are also existentially quantified out. It it thus twice necessary that we have
a sophisticated method for simplifying out existential quantifiers, and a
strategy for minimally weakening them out if this is not possible.

To this end, here is my recipe for removing existential quantifiers:
1: Convert the quantified predicate into disjunctive normal form.
2: Distribute the quantification over each disjunct. For each of these
quantified conjunctions, do the following steps.
3: Remove each bounded variable that does not appear in the quantified
predicate. If this is all bounded variables, then we have eliminated this
quantifier and can move onto the next one. Otherwise, continue to step 4.
4: Each atom is an arithmetic comparison or boolean literal. For each negated
atom, flip the comparison or literal and remove the negation. For example,
we convert !(X > Y) to X <= Y, where X and Y are arithmetic expressions.
5: Convert all exclusive comparisons to inclusive comparisons. For example,
we convert X < Y to X <= Y - 1. We can do this because the algorithm only
supports integers currently.
6: For each bounded variable v, derive from the atoms a range for v. For
example, we extract the range [X,Y] from the atoms v >= X && v <= Y, where
X and Y are arithmetic expressions. From the atom v == X, we can derive [X,X].
This may involve complex arithmetic calculations, for which we use SymPy. This
range will always be contiguous, since there are no disjuncts in the predicate.
7: Apply an extended version of the one-point rule, that replaces each
occurrence of each bounded variable with a variable that represents its range.
The extended rule includes two sets of rules:
Set 1:
[X,Y] . Z simplifies to [X . Z, Y . Z] for . = {+, -, *, /}
Z . [X,Y] simplifies to [Z . X, Z . Y] for . = {+, *}
Z . [X,Y] simplifies to [Z . Y, Z . X] for . = {-, /}
Set 2:
Z == [X,Y] simplifies to Z >= X && Z <= Y
Z >= [X,Y] simplifies to Z >= X
Z <= [X,Y] simplifies to Z <= Y
Sometimes, the range will not have a lower or upper limit. In this case, we have
[-inf, Y] and [X, inf] respectively. Hence, we must also define:
Z >= -inf simplifies to true
Z <= inf simplifies to true
Note that a case like Z <= -inf cannot occur as per the above rules.
As per the grammar for our target programs, arithmetic comparisons can only
take integers as arguments. Hence there will only be one comparison operator per
atom. Hence, we (todo: what about intervals + intervals, etc?) applying the rules in Set 1, then the rules in Set 2




This algorithm takes the rather bold step of existentially quantifying SPs
of assignments, as well as
"""

from pysmt.shortcuts import *

def simplify_existential(existential):
    p = simplify(existential)
    if not p.is_quantifier():
        return p
    p = eliminate_redundant_bound_vars(p)
    if not p.is_quantifier():
        return p
    p = apply_one_point_rule(p)


def eliminate_redundant_bound_vars(p):
    """
    A.75: If x is not free in A then: (exists x :: A) == A
    """
    pred = p.args()[0]
    used = [i for i in p.quantifier_vars() if i in pred.get_free_variables()]
    if not used:
        return pred
    return Exists(used, pred)


def apply_one_point_rule(p):
    """
    A.56: (exists x :: x == E && A) == A[x <- E]
    """
    bound_vars = p.quantifier_vars()
    pred = p.args()[0]


