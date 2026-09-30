# ProofNet v0.7.1 Audit and Methodology Update

**Input audited:** `proofnet_v071_boundary_lens_complete_20260704.zip`  
**Audited artifact root:** `outputs/proofnet_v071_boundary_lens/`  
**Auditor note:** this execution environment does not provide `lean` or `lake`, so I could not independently rebuild the Lean project. I inspected the shipped Lean source, command logs, emitted JSONL, reports, and scripts; I also reran the package's Python validator, which passed. Treat the included Lean run as evidenced by the package logs, not independently reproduced here.

---

## 1. Executive diagnosis

v0.7.1 is a **real milestone**: it appears to have run Lean on five controlled examples using same-session source instrumentation and emitted Lean-state logs with real goal metavariable identifiers. The key regression test now passes at the data level:

```text
constructor creates two goals: q and p
exact h.right closes q
p remains the same frontier node
exact h.left closes p
```

The package therefore upgrades the project from a Python-repaired reference design to a controlled **Lean-state-extracted silver MVP**.

However, v0.7.1 is not yet a large-scale ProofNet dataset generator. The current graph is still mostly a **frontier transport trace**, not a semantically rich proof-net-inspired dependency graph. The next version should be v0.7.2 / v0.8 and should focus on schema alignment, typed graph deltas, structural expression features, reproducibility, and one real Mathlib/frontier pilot.

---

## 2. What is genuinely good

### 2.1 Actual Lean-state origin for controlled examples

The reports and logs show that the package ran:

```text
lake build
lake env lean ProofNet/Examples/Controlled.lean
lake env lean ProofNet/Examples/ControlledInstrumented.lean
lake exe proofnet_boundary_lens_extract
python3 scripts/postprocess_actual_lean_logs.py
python3 scripts/validate_actual_lean_boundary_lens.py
```

The emitted `PROOFNET_STATE` lines include Lean goal identifiers such as `_uniq.10.12`, targets such as `q`, `p`, and local contexts. This is the correct substrate for the Boundary-Lens method.

### 2.2 Same-session source instrumentation

v0.7.1 uses:

```lean
proofnet_state "before:..."
TACTIC
proofnet_state "after:..."
```

inside a single Lean proof. This avoids the worst flaw of prefix replay: sibling goals can preserve raw Lean metavariable identity across steps.

### 2.3 The core sibling-preservation caveat is fixed for the controlled conjunction theorem

The package's validation summary reports:

```json
{
  "frontier_invariant": true,
  "sibling_preservation": true,
  "sibling_detail": "after_constructor=['G_q', 'G_p'], consumed_after_h_right=['G_q'], after_h_right=['G_p'], consumed_after_h_left=['G_p'], final=[]"
}
```

This is exactly the right local invariant to test first.

### 2.4 Proof leakage is avoided in `model_input`

The raw records contain `full_declaration_source` and `proof_body_source`, but the `model_input` view contains only the formal statement and state-before features. My inspection found no `:= by` in `model_input`.

### 2.5 Failure branches are real Lean failures, not invented failures

The package includes separate Lean runs that emit a real pre-state and then fail on candidate tactics such as `exact h.left` when the goal is `q`. This is the correct direction for search-branch training data.

---

## 3. Main caveats and issues

### Issue 1: The shipped JSON Schema does not validate the actual JSONL records

The actual success records have:

```json
"schema_version": "proofnet-boundary-lens-step-0.7.1",
"record_type": "trace_step"
```

but `schemas/proofnet_lens_trace_step_schema_v0_7.json` expects:

```json
"schema_version": "0.7",
"record_type": "lens_trace_step"
```

It also requires fields such as `rho_before`, `rho_after`, `verification_status`, and a tactic object, none of which appear in the actual records. Running strict JSON Schema validation gives failures such as:

```text
'rho_after' is a required property
```

The package validator is therefore a useful custom invariant checker, but not a true schema validator for the declared schema. This must be fixed immediately.

### Issue 2: `rho_before` and `rho_after` are not in trace-step records

The methodology says the central object is:

```text
B_i = (s_i, G_i, rho_i, boundary_i)
```

But the actual trace records do not contain explicit `rho_before` / `rho_after`; some snapshot records contain `rho_raw_mvar_to_graph_node`. For dataset consumers and reproducibility, the transport map and transport certificate must be first-class fields in every trace step.

### Issue 3: The graph hash is not a canonical graph hash

`graph_hash` is computed from frontier node ids and capsules. Some graph node ids are generated using theorem ids and raw metavariable ids:

```python
node_id = f"G_{theorem_id}_{len(existing):02d}_{sha256_short({'target': target, 'raw': raw})[:8]}"
```

This makes hashes depend on engineering/provenance identifiers. A canonical pruning or redundancy key must exclude theorem id, raw mvar id, fvar id, and graph node id. v0.7.2 should split hashes into:

```text
boundary_hash_raw        includes raw Lean identifiers for audit only
boundary_hash_canonical  excludes raw ids and alpha-normalizes locals
cumulative_graph_hash    hashes the cumulative graph, not just frontier state
provenance_hash          hashes source/log provenance, never used for pruning
```

### Issue 4: The graph is not cumulative enough

The methodology requires:

```text
G_{i+1} = G_i ∪ ΔG_i
```

Current `graph_before_hash` / `graph_after_hash` are hashes of the current frontier and boundary capsules. They do not appear to include all prior tactic nodes, closed goals, typed edges, and intermediate claims. Therefore, they are closer to boundary-state hashes than cumulative proof-graph hashes.

### Issue 5: All `edges_added` are empty

In the actual success records, all 15 graph deltas have:

```json
"edges_added": []
```

The current delta records prove frontier transport but not yet proof-net dependency extraction. For example, `constructor` should emit `decomposes` and `creates_subgoal`; `exact h.right` should emit `uses_local` and `closes`; `rw [h1]` should emit `rewrite_rule` and `rewrites_to`.

### Issue 6: Failure parsing misses Lean error messages

Lean error messages appear in the `.stdout` files, while the postprocessor reads only `.stderr` for error excerpts and classification. As a result, all failure records currently have:

```json
"failure_type": "lean_error",
"lean_error_excerpt": ""
```

This loses exactly the information needed for failure-branch learning. The fix is to parse combined stdout+stderr.

### Issue 7: Source instrumentation is not yet a general tactic wrapper

v0.7.1 uses explicit `proofnet_state` markers. That is acceptable for the first actual Lean milestone, but the next implementation should support either:

```lean
proofnet_step constructor
proofnet_step exact h.right
```

or an automatic source instrumenter that recursively instruments tactic blocks. Large-scale extraction cannot rely on manually written markers.

### Issue 8: Nested tactic blocks are not traced internally

The theorem:

```lean
have hq : q := by
  exact hpq hp
```

is treated as one outer `have` transition. The inner `exact hpq hp` is not separately extracted. For large Lean proofs, nested tactic blocks are common, especially in `have`, `suffices`, `refine`, `calc`, `case`, `by_cases`, and `simp`/automation fallback scripts. v0.7.2 should implement hierarchical traces.

### Issue 9: Expression normalization is pretty-string identity

The Lean code currently uses:

```lean
def normalizeExprString (s : String) : String := s
```

This is intentionally conservative, but it is not stable enough for canonical graph comparison. Pretty strings are sensitive to local names, notation, options, implicit arguments, and Lean version changes. v0.7.2 should add a structural Lean-expression serializer.

### Issue 10: Local identifiers are present in capsules and hashes

Raw `mvar_id`, `fvar_id`, and `graph_node_id` appear in boundary capsules. They are excluded from `model_input`, but they still appear in the data records and current graph hash computation. The dataset needs three separated channels:

```text
identity_channel: raw Lean ids and graph ids for audit/transport
feature_channel: canonical model features, no raw ids
provenance_channel: source/log metadata, no training use
```

### Issue 11: Used declarations are empty and used hypotheses are source-estimated

The records contain:

```json
"used_declarations": [],
"used_local_hypotheses_estimate": [...]
```

This is honest, but weak. The next version should extract at least source-observed tactic arguments and then upgrade to InfoTree/proof-term verified dependencies.

### Issue 12: No Mathlib, PFR, or Lean Liquid theorem was state-extracted

The package correctly labels frontier examples as bronze/source plans. But the research cannot claim frontier-scale success until at least one pinned Mathlib or frontier theorem is traced with real `state_before` / `state_after`.

### Issue 13: The included build artifacts are platform-specific and not enough for reproducibility

The logs report Lean 4.31.0 on `arm64-apple-darwin24.6.0`. This container has no `lean` or `lake`, so I could not reproduce the build. v0.7.2 should add CI instructions and a reproducibility script that installs/uses the pinned `lean-toolchain` through `elan`.

### Issue 14: The quality tier should be more precise

`silver_tactic_state` is appropriate for controlled examples, but it may be too broad. I recommend the following tier labels:

```text
silver_controlled_tactic_state
silver_mathlib_tactic_state
silver_frontier_tactic_state
gold_proof_term_enriched
search_branch_same_session
search_branch_replay
bronze_source_plan
```

This prevents controlled toy traces and frontier proof traces from being accidentally merged as equal-quality data.

---

## 4. Methodology update: v0.7.2 Boundary-Lens with transport certificates

The v0.7.1 method should be updated as follows.

### 4.1 Replace one graph hash by four distinct hashes

For each trace step, compute:

```text
boundary_hash_raw_before/after
boundary_hash_canonical_before/after
cumulative_graph_hash_before/after
provenance_hash
```

Only this pair may be used as a safe redundancy/pruning key:

```text
PruningKey_i = (
  NormalizeLeanState(s_i),
  CanonicalBoundaryGraph(G_i -> Boundary(s_i))
)
```

Neither raw graph ids nor raw Lean ids may enter the canonical pruning key.

### 4.2 Add a first-class `transport_certificate`

Every success step must contain:

```json
"transport_certificate": {
  "focused_before_mvar": "...",
  "goals_before_mvars": [...],
  "goals_after_mvars": [...],
  "preserved_mvars": [...],
  "consumed_mvars": [...],
  "created_mvars": [...],
  "preserved_graph_nodes": [...],
  "consumed_graph_nodes": [...],
  "created_graph_nodes": [...],
  "tactic_modality": "focused",
  "checked_invariant": true
}
```

This certificate is an engineering object, not a model feature. It is the auditable proof that frontier transport was performed correctly.

### 4.3 Make graph deltas typed

Current records prove that goals moved correctly. v0.7.2 must begin extracting proof-net structure:

```text
constructor: decomposes, creates_subgoal
exact: uses_local/uses_term, closes
intro: introduces_hypothesis, transforms_goal
apply: applies_lemma, reduces_goal, creates_subgoal
rw: rewrite_rule, rewrites_to
have: creates_intermediate_claim, introduces_hypothesis
left/right: chooses_constructor
rfl: definitional_equality_closes
simp/linarith/omega/ring: automation_bundle, closes/transforms
```

Each edge should have:

```json
{
  "edge_type": "closes",
  "source": "...",
  "target": "...",
  "verification": "lean_transition_verified | source_observed | proof_term_verified | heuristic",
  "evidence": {...}
}
```

### 4.4 Split data into three channels

Each record should have:

```text
identity_channel:
  raw Lean mvars, fvars, graph ids, rho maps

feature_channel:
  canonical expressions, alpha-normalized local context, goal structure

provenance_channel:
  source spans, log files, command outputs, proof body for audit only
```

Model training should read only `feature_channel` plus certified graph features, never raw ids or proof bodies.

### 4.5 Upgrade failure records

Failures should include:

```text
combined stdout+stderr error excerpt
failure_type
candidate_tactic_kind
ghost_delta_prediction
reason_to_prune_or_penalize
```

When feasible, failures should be generated from a saved same-session state rather than a separate replay file.

### 4.6 Add hierarchical subproof traces

Tactic blocks should become nested traces. For example:

```lean
have hq : q := by
  exact hpq hp
```

should produce an outer `have` transition and an inner subtrace for the proof of `q`.

### 4.7 Add structural expression serialization

A minimal structural serializer should recursively encode:

```text
sort, const, fvar, mvar, bvar, app, lam, forallE, letE, lit, proj, mdata
```

with local variables alpha-renamed by de Bruijn/context ordinal. Pretty strings can remain for debugging, but not as canonical features.

### 4.8 First frontier pilot criterion

Do not jump directly to PFR or Lean Liquid. First run one small Mathlib theorem with available imports and at least one of:

```text
have, obtain/rcases, constructor, rw, apply, exact
```

Promote only that theorem to `silver_mathlib_tactic_state` if real Lean states are emitted.

---

## 5. Recommended next milestones

### v0.7.2: Schema and typed-delta correctness

- Align actual records and JSON Schema.
- Add `rho_before`, `rho_after`, and `transport_certificate` to trace records.
- Remove hardcoded graph-node special cases such as `G_q` / `G_p` from the generic transport code.
- Parse Lean error messages from stdout+stderr.
- Emit typed graph edges for controlled tactics.
- Add strict JSON Schema validation to CI.

### v0.7.3: Structural features

- Implement structural expression serialization.
- Produce canonical boundary hashes excluding raw ids.
- Add alpha-normalization tests.
- Add theorem variants with renamed hypotheses to verify canonical equality.

### v0.8: Real tactic wrapper and hierarchical traces

- Replace manual source markers with a `proofnet_step` tactic or robust automatic source instrumenter.
- Recursively instrument nested tactic blocks.
- Trace `have`, `suffices`, `calc`, `case`, `by_cases`, `constructor`, `rcases`, `rw`, `simp`, and `apply`.

### v0.9: Proof-term / InfoTree enrichment

- Extract constants, local hypotheses, recursors, projections, constructors, rewrite lemmas, and typeclass instances.
- Mark edges as `proof_term_verified` only when they come from Lean objects.

### v1.0: Search experiment

- Implement one proof search loop.
- Compare state-only versus state+Boundary-Lens graph.
- Report duplicate expansions, solved theorems, wall-clock, candidate attempts, and proof lengths.

---

## 6. Updated research statement

The updated methodology should state:

> v0.7.1 demonstrates that same-session Lean state instrumentation can preserve open-goal identity for controlled proofs. The next methodological step is to turn these transported boundaries into typed cumulative proof graphs. Boundary-Lens records must separate identity, features, and provenance; must include explicit transport certificates; and must use canonical boundary hashes that exclude raw Lean identifiers. Only after these conditions hold should ProofNet graphs be used for pruning or large-scale training.

---

## 7. References

- Jean-Yves Girard, *Linear Logic*, Theoretical Computer Science, 1987.
- Dominic J. D. Hughes, *Unification nets: canonical proof net quantifiers*, arXiv:1802.03224.
- The Lean Language Reference, https://lean-lang.org/doc/reference/latest/.
- Kaiyu Yang et al., *LeanDojo: Theorem Proving with Retrieval-Augmented Language Models*, arXiv:2306.15626.
- Guillaume Lample et al., *HyperTree Proof Search for Neural Theorem Proving*, arXiv:2205.11491.
- Matěj Kripner, Michal Šustr, Milan Straka, *LeanTree: Accelerating White-Box Proof Search with Factorized States in Lean 4*, arXiv:2507.14722.
- Lean Liquid Tensor Experiment repository, https://github.com/leanprover-community/lean-liquid.
