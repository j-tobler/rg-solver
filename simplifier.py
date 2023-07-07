from pysmt.shortcuts import *

def simplify_formula(formula):
    ...


def to_dnf(formula):
    ...


def to_nnf(formula):
    """
    Converts to negation normal form, then applies negations to atoms, resulting
    in total elimination of negations.
    """
    ...


def apply_negation(formula):
    """
    Requires that the formula is negated.
    """
    assert formula.is_not()
    body = formula.args()[0]
    if body.is_true():
        return FALSE()
    elif body.is_false():
        return TRUE()
    elif body.is_le():
        return GT(body.args()[0], body.args()[1])
    elif body.is_lt():
        return GE(body.args()[0], body.args()[1])
    elif body.is_equals():
        # fixme: no representation of != in pysmt?
        return formula
