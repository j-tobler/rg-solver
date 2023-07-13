### Tracee
(TRansition Abstraction via Complete Existential Elimination)
Early-stage prototype of a concurrent-program verifier for a low level language.\
Automates the Owicki-Gries proof directly, rather than operating on intermediate transition invariants.\
Abstracts local variables out from interfering state transitions using existential quantification.

### Priority Developments
- [ ] Simplify predicates using intervals, or related abstract-interpretation techniques.
- [ ] Add a list of predicate structures that vary in expressiveness in order to facilitate parameterised precision.
  - [ ] Formalise and implement the implicit abstraction performed by existing techniques.
- [ ] Investigate the scalability of the current quantifier elimination strategy.
