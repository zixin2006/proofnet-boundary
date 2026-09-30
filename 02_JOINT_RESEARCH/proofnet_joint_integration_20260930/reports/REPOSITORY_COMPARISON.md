# What the two repositories change about your part

**Decision:** integrate your work into `proof-graphs`; do not build another parallel Lean graph extractor. Retain `proofnet-ir` as the formally verified MLL reference layer. Recast Boundary-Lens as a **typed, transaction-aware evidence and proof-reuse interface**, evaluated against your friend's existing structural-state and coupled-group search baselines.

This is a recommendation about research direction, not a judgment about authorship or personal ability. The code is treated as your friend's contribution because that is how you described it. The repositories alone do not establish who contributed every idea, nor how publication credit should be divided.

## 1. The honest comparison

At the inspected commits, your friend's work is ahead of the last Boundary-Lens artifact in both implementation and experimental maturity. Your earlier design remains useful, but much of its originally proposed engineering is now overlapping work. The right response is to reuse that foundation rather than defend an obsolete novelty claim. [R1–R8, U1]

| Dimension | `proofnet-ir` | `proof-graphs` | Your last available Boundary-Lens package |
|:--|:--|:--|:--|
| Core object | Actual proof-net certificates for a restricted MLL calculus | Extracted step-dependency graphs and live search graphs | Goal-boundary snapshots and proposed typed graph updates |
| Trust basis | Lean-formalized checker/sequentialization results in that calculus | Executed Lean traces, structural checks, final proof replay | Included controlled Lean logs and custom frontier checks |
| Data scale | Formal-library and MLL experiment artifacts | 7,285 corrected step graphs, plus search artifacts | Five controlled theorems, 15 success rows and five failure rows in the inspected ZIP |
| Identity | Canonical identity for the specified MLL representation | Lean-expression keys, renaming, and coupled groups | Raw goal transport; schema and feature separation still incomplete |
| Search evidence | Registered restricted-logic experiments | Several registered Lean search comparisons | No demonstrated incremental search improvement |
| Best role in joint project | Logical reference and certified restricted testbed | Shared implementation and empirical baseline | Proposed evidence-quality, transport, and checked-reuse layer |

The 7,285 graphs are not 7,285 fully annotated open-boundary traces. The exported rows contain step kinds, source lines, edges, and graph statistics; expression-rich state snapshots cannot be reconstructed from that dataset alone. A sidecar enrichment must return to raw extraction or re-elaborate a source subset. [R2, R7, R8, R17]

## 2. What your friend has actually contributed

### A. A genuine formal proof-net library

`proofnet-ir` establishes substantial guarantees for **unit-free, cut-free multiplicative linear logic**: a correctness checker, conversion from derivations, sequentialization of accepted certificates, and canonical identity. Its rolling result includes a stated quadratic symbolic-operation bound, not a general linear-time guarantee or a bound on arbitrary Lean proof search. This is a formal-methods contribution in its own right. [R1]

It is not simply a backend that can certify any Lean dependency graph. Lean's dependent type theory and tactic meta-state are not MLL; a bridge requires a separate definition and theorem. Shared terminology is not such a bridge.

### B. An actual extraction and search program

`proof-graphs` already traverses Lean InfoTrees, derives dependency graphs, drives a live Lean REPL, compares state and goal searches, normalizes identities structurally, and keeps metavariable-coupled goals together. It also reconstructs proof scripts and checks completed candidates from the statement. Those are implementations, not only plans. [R5–R8]

Consequently, “we use real Lean states,” “we preserve metavariable identity,” “we group coupled goals,” and “we reuse solved goals” are no longer distinctive next contributions for your branch.

### C. Useful negative evidence

The most valuable change is empirical. The repositories distinguish the number of possible orderings of a completed proof graph from the order redundancy actually encountered by a search policy. Default first-goal scheduling can suppress the latter without eliminating the former. [R2–R4]

In search-v0.8, the registered comparable set contains **158 tasks, with three draw sets per task**:

| Search | Set 0 | Set 1 | Set 2 | Total / 474 task-sets |
|:--|--:|--:|--:|--:|
| Whole states | 38 | 37 | 41 | 116 |
| Independent goals | 40 | 39 | 42 | 121 |
| Coupled goal groups | 40 | 39 | 43 | 122 |

None of the three registered pairwise comparisons passed the Holm-adjusted decision rule. These are neither 474 independent theorems nor proof of equivalence between algorithms. They are evidence against expecting a large automatic benefit from replacing state search by this graph search in the tested setting. [R3]

The latest correction explicitly withdraws a simple runtime-cost advantage: searches share model draws and run in a rotating order, so later searches can inherit cached work. Both the pooled timing and the “ran first” subsets are inadequate as a clean isolated latency comparison. [R3]

A further update matters in `proofnet-ir`: with the thinking condition in representation-v0.3, 35 nets, 32 labelled derivations, and 30 positional derivations verify out of 90 tasks; no pairwise format difference is significant after the adjustment. Without thinking the counts are 11, 0, 0. An earlier headline that nets reliably outperform derivations is too broad. [R9]

## 3. Where your contribution still has value

### Immediate, defensible value: independent semantic audit

The existing handoff identifies unaudited failure combinators and normalization concerns. A genuinely independent reconstruction and adversarial Lean test suite is useful work, particularly because structural invariants can pass when an extractor consistently assigns the wrong interpretation. [R4]

Your Boundary-Lens perspective is valuable here: it asks what each edge means, what state it belongs to, and what evidence permits reuse. Convert that perspective into executable checks rather than another layer of terminology.

### Medium-term value: a shared semantic interface

The offline extractor records goal identifiers and tactic-tree structure, while the live search exporter records instantiated expressions. A joint interface can connect these without treating them as identical evidence: versioned goal capsules, transaction/branch identities, assignment deltas, term/local provenance, and an explicit record of incomplete dependency coverage. [R5–R7]

This is a proposed integration contribution. It is not yet implemented in Lean in this deliverable, and it should not be advertised as a new proof theory by naming it a lens.

### High-upside, uncertain value: transportable proof fragments

The new experiment should target a narrower question:

> Can a boundary-aware index find and replay already checked proof fragments in new compatible contexts, avoiding repeated tactic work beyond structural-state deduplication and ordinary proof-term caching?

Existing search already shares proofs for matching goal keys. The possible extension is **typed context transport**: reuse when irrelevant local assumptions differ, when required local evidence can be mapped to a different context, or when the same subargument appears inside different surrounding proofs. Start with closed fragments; require Lean to check each transported application. Graph indexing must beat a non-graph cache receiving the same fragment pool before graph-specific value is claimed. [R6; proposed extension]

This has no guaranteed payoff. It may turn out that ordinary premise retrieval or a typed cache captures almost everything. That outcome would still determine which part of your representation is worth keeping.

## 4. Findings from this review

A fresh Python audit of the available v0.7.1 ZIP found 15 success records and five failure records, no typed edges in any success delta, no explicit `rho_before` in those rows, and 15/15 failures against the shipped trace schema. That refines earlier conversation counts: use the inspected artifact's five failures, not a remembered six. No Lean execution was rerun here. [U1]

Reviewing `goal_identity.py` also revealed a concrete **testable hazard**: metavariable renaming uses regular expressions over the complete serialized expression string, including quoted string literals. Thus a literal containing a metavariable-looking token can be altered as though it were a genuine metavariable. This package reproduces that mechanism in small Python fixtures and shows how a tagged AST avoids it. This is not evidence that a particular published Lean proof was wrong or that the empirical conclusions are invalid. It is a regression to verify in actual Lean. [R5]

Other bounded audit targets are an `h?` fallback for unexported free variables, omitted implementation-detail locals, grouping by directly visible term-metavariable mentions, and a printed carried-goal check in the otherwise structural-key search. These deserve conservative handling and tests. They are not a blanket claim that the entire engine is unsound. Final proof replay protects theorem acceptance, but unsafe merging can still discard solvable branches or distort measurements. [R5, R6]

## 5. What to retire from the old pitch

Retire “factorial proof-order reduction implies factorial Lean search savings.” Retire “state plus graph hashing safely prunes more than faithful state hashing.” Retire “only the focused goal can change.” Retire “every successful tactic or recorded dependency edge is kernel-certified.” Keep the mathematical motivation, but distinguish formal theorems, executed observations, derived annotations, and speculative proposals.

Do not lead with a PFR or condensed-mathematics diagram whose states were not extracted. Use those areas later as held-out semantic stress tests, not as decorative evidence of scale.

## 6. Proposed joint position

A suitable joint research question is:

> Which proof-graph abstractions remain useful once ordinary goal scheduling and structural-state sharing have already removed the easy redundancy, and what evidence is needed to reuse a proof fragment safely?

A suitable description of your part is:

> I am developing the typed boundary and proof-transport layer that turns extracted search graphs into auditable, reusable proof fragments, and testing its incremental value against the project's existing state and graph baselines.

That is stronger than another general graph extractor because it connects directly to the evidence your friend already collected. It is also honest about what still has to be implemented and measured.
