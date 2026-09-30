# Codex Prompt: Upgrade ProofNet Boundary-Lens v0.7.1 to v0.7.2

You are working on the ProofNet project: **The Geometry of Proof Search: Proof-Net Abstractions for Neural Theorem Proving**.

You have been given the package:

```text
proofnet_v071_boundary_lens_complete_20260704.zip
```

Your task is to upgrade it to **v0.7.2**, fixing schema, transport, graph-delta, failure-branch, and reproducibility issues. The goal is not to train a model yet. The goal is to produce a rigorous, reproducible, Lean-backed dataset generator for controlled examples and one small Mathlib pilot if feasible.

---

## 0. Non-negotiable principles

1. **Do not simulate Lean states.** Success records must come from actual Lean execution logs or a Lean-side JSON writer.
2. **Do not call source-derived frontier examples silver.** PFR / Lean Liquid / condensed-math plans remain `bronze_source_plan` unless their actual Lean project is built and traced.
3. **Do not use raw ids as model features.** `mvar_id`, `fvar_id`, `graph_node_id`, source line ids, theorem ids, and proof-body strings are identity/provenance only.
4. **Do not use graph hash alone for pruning.** The safe key is:

```text
PruningKey = (NormalizeLeanState(s_i), CanonicalBoundaryGraph(G_i -> Boundary(s_i)))
```

5. **Do not mark an edge as proof-term verified unless it is extracted from Lean proof terms, InfoTree, or kernel/environment data.**

---

## 1. First inspect and reproduce v0.7.1

Unzip the v0.7.1 package and inspect:

```text
ProofNet/Boundary/Capsule.lean
ProofNet/Boundary/Trace.lean
ProofNet/Boundary/TacticWrapper.lean
ProofNet/Examples/Controlled.lean
ProofNet/Examples/ControlledInstrumented.lean
scripts/run_actual_lean_boundary_lens.py
scripts/postprocess_actual_lean_logs.py
scripts/validate_actual_lean_boundary_lens.py
schemas/proofnet_lens_trace_step_schema_v0_7.json
data/actual_lean_boundary_lens_trace_steps.jsonl
data/actual_lean_failure_branches.jsonl
reports/ACTUAL_LEAN_RUN_REPORT.md
reports/FRONTIER_TRANSPORT_INVARIANT_REPORT.md
```

Run:

```bash
lake --version
lean --version
lake build
lake env lean ProofNet/Examples/Controlled.lean
lake env lean ProofNet/Examples/ControlledInstrumented.lean
python3 scripts/postprocess_actual_lean_logs.py
python3 scripts/validate_actual_lean_boundary_lens.py
```

If Lean/Lake is missing, install/activate the pinned Lean toolchain using `elan` if feasible. If impossible, stop and report exactly why. Do not fabricate results.

---

## 2. Fix the schema mismatch immediately

Current problem: actual records do not validate against the shipped JSON Schema.

Create a new schema:

```text
schemas/proofnet_lens_trace_step_schema_v0_7_2.json
schemas/proofnet_boundary_graph_schema_v0_7_2.json
```

The actual emitted records must validate against these schemas using `jsonschema`.

### Required top-level success record shape

```json
{
  "schema_version": "0.7.2",
  "record_type": "lens_trace_step",
  "quality_tier": "silver_controlled_tactic_state",
  "theorem_id": "...",
  "variant_id": "...",
  "step_index": 0,
  "formal_statement_header": "...",
  "model_input": {...},
  "identity_channel": {...},
  "feature_channel": {...},
  "provenance_channel": {...},
  "tactic": {
    "raw": "constructor",
    "kind": "constructor",
    "arguments": [],
    "source_span": {...}
  },
  "state_before": {...},
  "state_after": {...},
  "rho_before": {...},
  "rho_after": {...},
  "frontier_before": [...],
  "frontier_after": [...],
  "boundary_hash_raw_before": "sha256:...",
  "boundary_hash_raw_after": "sha256:...",
  "boundary_hash_canonical_before": "sha256:...",
  "boundary_hash_canonical_after": "sha256:...",
  "cumulative_graph_hash_before": "sha256:...",
  "cumulative_graph_hash_after": "sha256:...",
  "transport_certificate": {...},
  "graph_delta": {...},
  "lean_result": "success",
  "verification_status": "lean_transition_verified"
}
```

### Required failure record shape

```json
{
  "schema_version": "0.7.2",
  "record_type": "lens_trace_step",
  "quality_tier": "search_branch_replay_failure",
  "theorem_id": "...",
  "variant_id": "...",
  "step_index": 0,
  "candidate_tactic": {
    "raw": "exact h.left",
    "kind": "exact",
    "arguments": ["h.left"]
  },
  "state_before": {...},
  "state_after": null,
  "rho_before": {...},
  "rho_after": null,
  "frontier_before": [...],
  "frontier_after": null,
  "graph_after_hash": null,
  "lean_result": "failure",
  "lean_error_excerpt": "...",
  "failure_type": "type_mismatch | apply_failed | unsolved_goals | unknown_identifier | tactic_failed | lean_error",
  "graph_delta": {
    "delta_status": "ghost_rejected",
    "edges_added": [],
    "frontier_updates": []
  },
  "verification_status": "lean_rejected"
}
```

---

## 3. Add explicit `rho` maps and transport certificates

Every trace step must include:

```json
"rho_before": {
  "raw_mvar_id": "graph_node_id"
},
"rho_after": {
  "raw_mvar_id": "graph_node_id"
}
```

Every success step must also include:

```json
"transport_certificate": {
  "tactic_modality": "focused | all_goals | branch_generating | context_only | unknown",
  "focused_before_mvar": "...",
  "goals_before_mvars": [...],
  "goals_after_mvars": [...],
  "preserved_mvars": [...],
  "consumed_mvars": [...],
  "created_mvars": [...],
  "preserved_graph_nodes": [...],
  "consumed_graph_nodes": [...],
  "created_graph_nodes": [...],
  "checked_frontier_invariant": true,
  "checked_focused_tactic_did_not_consume_siblings": true
}
```

Use the actual raw Lean mvar ids emitted by `proofnet_state`. Do not invent raw ids.

### Transport algorithm

```python
def transport_frontier(rho_before, goals_before, goals_after, focused_before, tactic_kind):
    old = set(goals_before)
    new = set(goals_after)

    preserved = old & new
    disappeared = old - new
    created = new - old

    rho_after = {}
    for m in preserved:
        rho_after[m] = rho_before[m]
    for m in created:
        rho_after[m] = fresh_engineering_goal_node_id()

    modality = tactic_modality(tactic_kind)
    if modality == "focused":
        consumed = {focused_before} if focused_before in disappeared else set()
        accidental = disappeared - consumed
        if accidental:
            raise FrontierTransportError(
                f"Focused tactic consumed non-focused goals: {sorted(accidental)}"
            )
    else:
        consumed = disappeared

    return rho_after, certificate
```

The conjunction regression must still pass.

---

## 4. Remove hardcoded graph node ids

Current v0.7.1 has a special case for `cex_and_constructor_exact` targets `q` and `p`. Remove theorem-specific id generation.

Graph node ids should be engineering ids such as:

```text
g.000001
g.000002
```

They may be stable within a run, but they must not be model features and must not enter canonical hashes.

The sibling preservation test should check transport via raw mvar preservation and node identity, not hardcoded names like `G_q` / `G_p`.

---

## 5. Separate identity, feature, and provenance channels

Each record must clearly separate:

```text
identity_channel:
  raw_mvar_id, raw_fvar_id, graph_node_id, rho maps, source positions for audit

feature_channel:
  alpha-normalized goal and local-context features, no raw ids, no graph ids, no theorem ids

provenance_channel:
  source file, command, log file, proof body for audit only, not for training
```

The validator must fail if `model_input` or `feature_channel` contains any of:

```text
mvar_id
raw_mvar_id
fvar_id
raw_fvar_id
graph_node_id
capsule_id
full_declaration_source
proof_body_source
:= by
```

---

## 6. Implement typed graph deltas

Current `edges_added` are empty. v0.7.2 must emit typed edges for controlled tactics.

### constructor

For a focused goal that becomes multiple subgoals:

```json
{
  "nodes_added": [
    {"id": "step.0", "type": "TacticStep", "label": "constructor"},
    {"id": "g.1", "type": "OpenGoal", "target_feature_hash": "..."},
    {"id": "g.2", "type": "OpenGoal", "target_feature_hash": "..."}
  ],
  "edges_added": [
    {"source": "g.0", "target": "step.0", "type": "decomposes", "verification": "lean_transition_verified"},
    {"source": "step.0", "target": "g.1", "type": "creates_subgoal", "verification": "lean_transition_verified"},
    {"source": "step.0", "target": "g.2", "type": "creates_subgoal", "verification": "lean_transition_verified"}
  ],
  "frontier_updates": [
    {"action": "consume", "node": "g.0"},
    {"action": "create", "node": "g.1"},
    {"action": "create", "node": "g.2"}
  ],
  "delta_status": "verified"
}
```

Add `sibling_independent` only when dependency support is demonstrably disjoint or mark it as heuristic:

```json
{"type": "sibling_independent", "verification": "heuristic_boundary_disjoint"}
```

### exact

For a focused goal that closes:

```json
{
  "nodes_added": [
    {"id": "step.1", "type": "TacticStep", "label": "exact"},
    {"id": "term.1", "type": "Term", "label": "h.right", "source": "tactic_argument_observed"}
  ],
  "edges_added": [
    {"source": "term.1", "target": "step.1", "type": "constructs", "verification": "tactic_argument_observed"},
    {"source": "step.1", "target": "g.focus", "type": "closes", "verification": "lean_transition_verified"}
  ]
}
```

### intro

Emit `introduces_hypothesis` / `introduces_variable` based on local-context diff.

### apply

Emit `applies_lemma`, `reduces_goal`, and `creates_subgoal`.

### rw

Emit `rewrite_rule`, `rewrites_to`, and before/after target hashes. Preserve rewrite direction.

### have

Emit `creates_intermediate_claim`, `introduces_hypothesis`, and if internal proof is not traced, mark `subproof_trace_status = "not_instrumented"`.

### left/right

Emit `chooses_constructor` and `creates_subgoal`.

### rfl/assumption

Emit `closes` with appropriate source.

### simp/linarith/omega/ring/aesop

Emit `AutomationBundle` nodes only. Do not claim internal proof-search dependencies unless extracted.

---

## 7. Fix failure branch parsing

Lean errors in v0.7.1 appear in `.stdout`, not `.stderr`. Parse combined stdout+stderr.

For each failure record, fill:

```json
"lean_error_excerpt": "logs/...: error: Type mismatch ...",
"failure_type": "type_mismatch"
```

Classification rules:

```text
contains "Type mismatch"             -> type_mismatch
contains "Tactic `apply` failed"      -> apply_failed
contains "unsolved goals"             -> unsolved_goals
contains "unknown identifier"         -> unknown_identifier
contains "tactic failed" or "failed"  -> tactic_failed
otherwise                              -> lean_error
```

Also add:

```json
"reason_to_prune_or_penalize": "candidate term has type p but focused target is q"
```

when this can be extracted safely from the error text.

---

## 8. Add structural expression serialization MVP

Replace identity pretty-string normalization with a structural serializer.

Implement in Lean if feasible:

```lean
def serializeExprFeature (e : Expr) : MetaM Json := ...
```

At minimum encode:

```text
sort
const
fvar, but alpha-renamed by local-context ordinal, not raw id
mvar, but only when needed and canonicalized
bvar
app
lam
forallE
letE
lit
proj
mdata stripped or recorded separately
```

If this is too much for v0.7.2, implement it in Python over a Lean-emitted expression tree, but do not rely only on pretty strings for canonical hashes.

The feature hash must be insensitive to local hypothesis names. Add tests with renamed variables/hypotheses.

---

## 9. Add strict validators

Create:

```text
scripts/validate_v072_schema_and_invariants.py
```

It must run:

```bash
python3 scripts/validate_v072_schema_and_invariants.py
```

and check:

```text
1. every JSONL record validates against v0.7.2 schema;
2. every success record has state_before/state_after;
3. every failure record has state_after = null;
4. every success record has rho_before/rho_after;
5. every frontier node has exactly one boundary capsule;
6. every open Lean goal maps to exactly one frontier node;
7. focused tactics do not consume sibling goals;
8. typed graph edges are nonempty for constructor/exact/intro/apply/rw/have/left;
9. graph edges marked lean_transition_verified occur only on accepted transitions;
10. ghost deltas occur only on rejected candidates;
11. feature_channel/model_input contain no raw ids and no proof body;
12. canonical hashes do not contain theorem ids, raw mvar ids, raw fvar ids, or graph node ids;
13. failure records have nonempty error excerpts and useful failure_type.
```

---

## 10. Improve instrumentation path

v0.7.2 may still use source instrumentation, but it must be generated automatically.

Create or improve:

```text
scripts/instrument_controlled_lean.py
```

Requirements:

- input: an ordinary Lean file with proofs;
- output: an instrumented Lean file with `proofnet_state before/after` markers;
- recursively instrument nested tactic blocks when possible;
- emit a machine-readable tactic schedule file:

```text
data/instrumentation_schedule.json
```

with theorem id, step index, tactic raw text, source span, nesting path, and whether the tactic is an outer or nested tactic.

If arbitrary recursive instrumentation is too hard, support the current controlled examples and document unsupported syntax.

---

## 11. Optional but preferred: `proofnet_step` wrapper

If feasible, implement a real Lean tactic wrapper:

```lean
proofnet_step constructor
proofnet_step exact h.right
proofnet_step apply hqr
```

But do not block v0.7.2 on arbitrary tactic syntax if source instrumentation is working. The priority is correct data.

---

## 12. First Mathlib pilot

If Mathlib is available or can be added without excessive build cost, add one small theorem.

Criteria:

```text
- builds in the environment;
- uses at least two of have/rw/apply/constructor/exact/rcases;
- emits actual Lean state records;
- is labeled silver_mathlib_tactic_state.
```

If Mathlib is not available, write:

```text
reports/MATHLIB_PILOT_STATUS.md
```

stating that no Mathlib theorem was traced and explaining the blocker.

Do not attempt full PFR or Lean Liquid in this step.

---

## 13. Output files

Produce:

```text
schemas/proofnet_lens_trace_step_schema_v0_7_2.json
schemas/proofnet_boundary_graph_schema_v0_7_2.json

data/actual_lean_boundary_lens_trace_steps_v0_7_2.jsonl
data/actual_lean_boundary_graph_snapshots_v0_7_2.jsonl
data/actual_lean_failure_branches_v0_7_2.jsonl
data/instrumentation_schedule.json

scripts/postprocess_actual_lean_logs_v072.py
scripts/validate_v072_schema_and_invariants.py
scripts/instrument_controlled_lean.py

reports/V072_IMPLEMENTATION_REPORT.md
reports/V072_SCHEMA_VALIDATION_REPORT.md
reports/V072_FRONTIER_TRANSPORT_REPORT.md
reports/V072_TYPED_DELTA_REPORT.md
reports/V072_FAILURE_BRANCH_REPORT.md
reports/V072_KNOWN_LIMITATIONS.md
reports/MATHLIB_PILOT_STATUS.md
```

Also update the zip package.

---

## 14. Acceptance criteria

v0.7.2 is complete only if:

```text
[ ] lake build passes, or exact Lean/Lake blocker is reported.
[ ] Controlled instrumented Lean session runs.
[ ] At least 15 success records are regenerated from actual Lean logs.
[ ] At least 5 failure records are regenerated from actual Lean failures.
[ ] All records validate against v0.7.2 JSON Schema.
[ ] Every trace record has rho_before/rho_after or null after maps for failures.
[ ] Every success record has a transport_certificate.
[ ] The conjunction sibling-preservation regression passes without hardcoded q/p graph ids.
[ ] edges_added is nonempty for constructor, exact, intro, apply, rw, have, left/right when applicable.
[ ] Failure records contain nonempty Lean error excerpts and nontrivial failure_type.
[ ] model_input and feature_channel contain no raw ids and no proof body.
[ ] Canonical hashes exclude raw ids and graph ids.
[ ] Reports honestly describe what is still heuristic.
```

---

## 15. Final console summary

Print:

```text
ProofNet v0.7.2 Boundary-Lens upgrade complete.

Lean build: PASS/FAIL
Controlled Lean run: PASS/FAIL
Trace records: ...
Failure records: ...
Strict schema validation: PASS/FAIL
Frontier invariant: PASS/FAIL
Sibling preservation without hardcoded ids: PASS/FAIL
Typed graph deltas: PASS/FAIL
Failure classification: PASS/FAIL
Proof leakage check: PASS/FAIL
Canonical hash raw-id exclusion: PASS/FAIL
Mathlib pilot: silver_mathlib_tactic_state / not attempted / failed
Known limitations:
  ...
```

---

## 16. Scientific framing for the report

Write the final report with this distinction:

```text
Existing work:
  proof nets motivate reducing proof-order bureaucracy;
  Lean gives kernel-checked tactic transitions;
  LeanDojo gives precedent for Lean data extraction and hard negatives;
  LeanTree motivates factoring independent branches.

ProofNet original contribution:
  Boundary-Lens records with rho-transport and transport certificates;
  typed cumulative partial proof graphs over Lean-certified boundaries;
  graph-based redundancy reduction that is safe only fiberwise over normalized Lean state.

Current v0.7.2 contribution:
  controlled Lean-state extraction with strict schemas, explicit rho maps,
  typed graph deltas, and auditable failure branches.

Future work:
  InfoTree/proof-term enrichment, actual search loop, Mathlib/PFR/Liquid scaling.
```

Be precise and do not overclaim.
