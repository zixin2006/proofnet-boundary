# Reflection on `proofnet_state_extractor_v05.zip`

## Bottom line

The v0.5 Codex project is a meaningful transition from a proof-net dataset scaffold toward a real Lean-backed extraction system. It implements a controlled Lean tactic-state probe that emits `state_before`, `tactic`, `state_after`, success/failure status, and shallow graph deltas for six small theorems. This is the first part of the project that deserves the label **silver** for controlled examples: the goals, targets, and local contexts in the emitted trace records are derived from Lean state snapshots, not from manual graph labels.

It is not yet a general Lean repository extractor, not yet a faithful cumulative partial proof graph system, and not yet evidence for graph-guided pruning on frontier proofs. PFR and frontier examples remain bronze/source-only or parsed-without-state in this package.

## What was implemented

The package contains a small Lean library and Python runner:

- `ProofNet/Extract/InfoTree.lean` defines a `proofnet_state "tag"` tactic. It captures the current Lean goals with `getGoals` and logs a JSON state snapshot.
- `ProofNet/Extract/State.lean` serializes each goal's metavariable ID, target expression, and local context declarations.
- `ProofNet/Extract/Expr.lean` pretty-prints Lean expressions into a `{pretty, normalized}` payload.
- `scripts/run_state_extractor.py` hardcodes six controlled declarations, replays tactic prefixes, inserts `proofnet_state "before"`, runs one tactic, inserts `proofnet_state "after"`, and emits JSONL trace records.
- `data/extracted_trace_steps.jsonl` contains 21 trace records: 15 successes and 6 failures.
- `data/proofnet_declarations_split.jsonl` separates `formal_statement_header`, `proof_body_source`, and `full_declaration_source`, with an explicit model-input policy excluding proof-bearing fields.
- `scripts/validate_extracted_traces.py` validates high-level leakage guards, nonempty deltas, and frontier-length consistency.

I could not independently run `lake build` in this execution environment because `lake` is not installed here. I did run the Python validator, which reports `PASS` with 21 trace records, 6 failures, 0 empty graph deltas, 0 proof-leakage violations, and 0 frontier-count violations. Static inspection of the package supports the report's main claim for controlled examples.

## What is scientifically strong

1. **The extractor now touches real Lean states.**

   The key improvement over v0.4 is that controlled traces no longer have null `state_before` and `state_after`. The trace records contain Lean-generated targets such as `q ∧ p`, `q`, `p`, `a = c`, and local contexts such as `h : p ∧ q`.

2. **Proof leakage is being handled correctly at the declaration-split level.**

   The new declaration records make `formal_statement_header` the only declaration-source field allowed for model input. The proof body is retained for audit and trace generation, but marked forbidden for model input.

3. **Failure records are real Lean failures for controlled examples.**

   Failed tactics such as `exact h.left` against goal `q ∧ p`, `exact hp` against `p ∨ q`, and `rfl` against `a = c` preserve the Lean pre-state and record an error excerpt. This is exactly the kind of negative branch needed later for compatibility/value/pruning models.

4. **The project is honest about frontier status.**

   PFR is not promoted to silver. The package records a bronze extraction attempt and states that the extractor must be run inside the actual `teorth/pfr` Lake project before PFR can become a state-trace dataset.

5. **The architecture is pointing in the right direction.**

   The before/after probe pattern is the correct MVP idea: instrument Lean around accepted tactic transitions, compare states, and emit graph deltas. This is the practical route from manually described proof-net abstractions to Lean-certified partial proof graphs.

## What is still weak or incomplete

1. **The extractor is hardcoded to six declarations.**

   `scripts/run_state_extractor.py` contains a Python list of controlled declarations and proof steps. It does not yet parse arbitrary `.lean` files, traverse proof scripts, or attach to a repository-scale Lean build.

2. **The file named `InfoTree.lean` does not yet traverse Lean InfoTrees.**

   It defines a useful state-marker tactic, but it does not inspect Lean's elaboration info tree, tactic spans, nested syntax, tactic expansion, or generated subterms. That is fine for an MVP, but future reports should avoid implying InfoTree extraction is already implemented.

3. **Expression normalization is currently a placeholder.**

   `normalizeExprString` returns the pretty-printed expression unchanged. This means expression payloads are sensitive to pretty-printer settings, local names, implicit arguments, notation, and Lean version differences. It is not yet a canonical representation suitable for robust graph equivalence or pruning.

4. **Graph deltas are shallow and generic.**

   The current delta contains a `TacticEffect` node and generic edges such as `tactic_consumes_frontier`, `tactic_creates_frontier`, `goal_has_target`, and `goal_has_local`. It does not yet emit tactic-specific semantic edges such as `decomposes`, `closes`, `rewrites`, `introduces_hypothesis`, `splits_case`, `applies_lemma`, or `constructs`.

5. **The current delta logic consumes all frontier goals.**

   In multi-goal states, a tactic usually acts on the focused goal, not all open goals. For example, in `CEX_AND`, after `constructor` there are two goals. The step `exact h.right` closes the first goal, leaving the second. The current delta logic adds `tactic_consumes_frontier` edges from both frontier goals and marks both as closed/transformed, because it loops over all `frontier_before` nodes. This is a major fidelity issue.

6. **Open goal identity is not stable enough.**

   Node IDs are computed from theorem ID, variant ID, step index, ordinal, and target. When the second goal becomes the first goal after a preceding goal is closed, its ordinal and step index change, so the node ID changes even though it is the same Lean metavariable goal. The result is an artificial close-and-recreate pattern. The future system should maintain `rho : MVarId -> node_id` and use Lean metavariable IDs plus robust goal matching to preserve unchanged frontier nodes.

7. **The validator is too weak.**

   The included validator checks useful surface invariants, but it does not validate against the JSON Schema files. Running JSON Schema validation on `data/extracted_trace_steps.jsonl` finds six schema errors: failure records set `graph_after_hash` to `null`, while `proofnet_trace_step_schema.json` requires a string. The schema should use `oneOf` for success/failure records or allow `graph_after_hash: null` for failures.

8. **Used declarations are regex-estimated, not proof-term-derived.**

   `estimate_used_declarations` extracts names from tactic text and local context names. This is useful as a weak hint, but it misses elaborated constants, constructors, recursors, projections, coercions, typeclass instances, simplification lemmas, and hidden dependencies.

9. **There is no cumulative graph state yet.**

   The system emits a per-step before-hash, delta, and after-hash, but does not maintain a persistent `G_i` across the whole proof with a verified frontier map. This means it is not yet implementing the core formal object `G_{i+1} = G_i ∪ ΔG_i` in a faithful way.

10. **The frontier records are not training-ready.**

    PFR and the Erdős records have useful verified-source metadata in the package, but their trace status is still `parsed_no_state_only` or bronze. Their candidate graphs remain hand-written/coarse and should not be used as positive graph-delta training data.

## Research interpretation

The project has crossed an important threshold: it now demonstrates that a Lean-side tactic can emit real state snapshots and that a Python pipeline can package those snapshots into graph-delta records with leakage guards. That is a legitimate MVP for the methodology.

The current graph abstraction, however, is still closer to a **state-diff annotation** than a proof-net-inspired dependency graph. The proof-net research value will appear only after the system can distinguish:

- focused goal versus unrelated open siblings;
- goal decomposition versus goal closure;
- local hypotheses introduced by tactics versus merely carried through;
- rewrite orientation and rewrite lemma dependency;
- constructor/case/induction branch structure;
- proof-term constants and hidden automation dependencies;
- canonical equivalence of partial proof states without using theorem IDs or manual labels.

The eureka idea remains strong: maintain an open, frontier-preserving proof graph during search, rather than trying to construct a complete proof net after the proof is complete. The current implementation is the first small engineering proof-of-concept of that idea.

## Recommended next steps

### 1. Fix frontier identity and focused-goal semantics

Add an explicit graph state object with a persistent frontier map:

```text
rho_i : Lean.MVarId -> GraphNodeId
```

For each tactic transition, identify the focused goal before the tactic and compare the post-state goals to the pre-state goals. Only the focused goal should receive `tactic_consumes_frontier` unless the tactic explicitly operates on all goals. Unchanged sibling goals should preserve node identity.

### 2. Replace pretty-string normalization with expression-structural normalization

Emit a Lean expression AST payload, not only pretty strings. At minimum record:

- expression kind (`const`, `app`, `forallE`, `lam`, `fvar`, `mvar`, `sort`, `lit`, etc.);
- constant names;
- binder structure;
- local variable de Bruijn/ordinal indices;
- universe levels;
- optional pretty string for debugging only.

The model can still consume compact tokenized strings, but pruning/canonicalization should use structural payloads.

### 3. Implement tactic-specific delta rules

Move from generic `TacticEffect` edges to family-specific rules:

- `constructor`: one goal decomposes into constructor subgoals; add `decomposes` and `creates_subgoal` edges.
- `left`/`right`: disjunction choice; add `selects_constructor` edge.
- `exact`/`assumption`: close focused goal using local/term; add `closes` and `uses` edges.
- `rw`: rewrite target/local context; add `rewrites`, `uses_rewrite_lemma`, and `rewrite_direction` fields.
- `cases`/`induction`: add case-split/recursor nodes and branch frontier nodes.
- `have`/`suffices`/`let`: add intermediate claim/local-definition nodes and dependency edges.
- `simp`/`aesop`/`omega`/`linarith`/`ring`: first as coarse automation bundles, then enriched through proof-term/dependency inspection.

### 4. Strengthen validation

Add a strict validator that checks:

- JSON Schema compliance;
- no proof-bearing field in model input files;
- every open Lean goal maps to exactly one open frontier node;
- every open frontier node maps back to one Lean goal;
- unchanged sibling goals preserve graph identity;
- graph-delta edge endpoints exist in `G_i ∪ ΔG_i`;
- failure records satisfy a separate failure schema;
- graph hashes are recomputable;
- canonical/pruning hashes do not consume theorem IDs, variant IDs, source IDs, or manual labels.

### 5. Stop parsing state from log messages for large-scale extraction

`logInfo` is acceptable for a tiny MVP, but fragile for large states. Long JSON may wrap, and parser failures will become common. Prefer one of:

- a Lean command/tactic that writes JSONL directly to a file;
- a Lean server/RPC extractor;
- LeanDojo-style tracing where available;
- a custom Lake executable that elaborates files and serializes traces.

### 6. Add a complete controlled tactic suite

Create synthetic theorems covering every tactic in the methodology table:

```text
intro, intros, exact, assumption, apply, refine, constructor,
left, right, cases, rcases, induction, have, suffices, let,
rw, simp, rfl, ext, omega, linarith, ring, aesop, tauto,
contradiction, exfalso
```

For each tactic, include success cases, plausible failures, multi-goal cases, and sibling-preservation tests.

### 7. Promote PFR only after in-repository extraction

Run the extractor inside the actual `teorth/pfr` Lake project. Start with a small selected theorem or subproof around `PFR_conjecture`, not the whole repository. The promotion criterion should be:

- exact source theorem builds;
- tactic states extracted for selected steps;
- graph deltas are Lean-state-derived;
- graph fidelity report maps extracted deltas to the source theorem structure;
- no source-only/manual graph is used as a positive example.

### 8. Add proof-term enrichment as gold layer

After a controlled proof elaborates, inspect the proof term or environment dependencies to recover constants, constructors, recursors, projections, rewrite lemmas, and typeclass instances. Use this to validate/enrich silver traces, not to replace them.

### 9. Run the first real pruning experiment only after silver graphs are faithful

The first convincing experiment should not be on PFR. It should be on a larger controlled corpus with many equivalent but bureaucratically different proof scripts. Compare:

- tactic-only best-first search;
- state-normalized search;
- state + partial-graph canonical search;
- graph-guided value/pruning model.

The key metric should be redundant expansions avoided at equal or higher proof success rate.

## Suggested v0.6 milestone

The next version should be called successful if it achieves all of the following:

1. Extracts from at least 30–50 controlled theorems without hardcoding declarations in Python.
2. Covers at least 15 tactic families.
3. Maintains a cumulative partial graph `G_i` and persistent `rho_i` frontier map.
4. Correctly preserves open sibling goal identity across focused tactic steps.
5. Emits JSON Schema-valid success and failure records.
6. Provides structural expression normalization beyond pretty strings.
7. Produces strict validation reports with schema, leakage, frontier-map, and hash checks.
8. Includes one small external Lean project extraction attempt, clearly labeled bronze/silver/gold.

## Final judgment

This v0.5 project is a strong **controlled silver extraction MVP** and a good engineering proof of concept. It fixes the most serious v0.4 weakness for synthetic examples: missing Lean states. It does not yet solve the hard research problem, because the graph deltas are generic, focused-goal semantics are wrong in multi-goal steps, expression canonicalization is placeholder-level, and frontier examples remain non-silver.

The future work is clear and feasible: make the frontier map persistent, make deltas tactic-specific, normalize expressions structurally, validate against strict schemas, and move from controlled hardcoded examples to repository-scale Lean instrumentation.
