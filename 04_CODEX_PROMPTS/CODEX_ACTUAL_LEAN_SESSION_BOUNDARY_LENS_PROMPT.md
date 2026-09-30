# Codex Prompt: Run the Actual Lean Session and Complete the Next Step

You are working on the ProofNet project: **The Geometry of Proof Search: Proof-Net Abstractions for Neural Theorem Proving**.

Your task is to complete the next real engineering step:

> **Run an actual Lean 4 session and implement a working same-session Boundary-Lens extractor for controlled examples.**

This is not a design-only task. You must run Lean. You must produce real `state_before` / `state_after` records from Lean execution. Do not simulate proof states. Do not fabricate metavariable IDs. Do not label source-derived plans as Lean-state extracted.

The immediate goal is to produce a minimal but real **v0.7.1 same-session Boundary-Lens extractor**.

---

## 0. Context and high-level objective

Earlier versions produced:
- v0.5: Lean-emitted state markers for controlled examples;
- v0.7 reference package: Python repair of frontier transport, schemas, visualizations, and methodology.

Now you must implement the real Lean-side step.

The central object is:

```text
B_i = (s_i, G_i, ρ_i, ∂_i)
```

where:

```text
s_i = Lean tactic state
G_i = cumulative partial proof graph
ρ_i = persistent map from Lean metavariable goals to graph frontier nodes
∂_i = boundary map from normalized Lean goal capsules to open graph ports
```

For each tactic step, output:

```text
(s_i, G_i, ρ_i, ∂_i) --t_i-->
(s_{i+1}, G_{i+1}, ρ_{i+1}, ∂_{i+1})
```

with:

```text
G_{i+1} = G_i ∪ ΔG_i
```

The key invariant is:

```text
Every open Lean goal in state_after corresponds to exactly one open frontier graph node.
```

The most important regression test is sibling-goal preservation:

```lean
theorem cex_and_constructor_exact (p q : Prop) (h : p ∧ q) : q ∧ p := by
  proofnet_step "constructor"
  proofnet_step "exact h.right"
  proofnet_step "exact h.left"
```

After `constructor`, the graph has two open goals. After `exact h.right`, only the `q` goal is closed; the `p` goal must preserve the same graph node ID.

---

## 1. Absolute rule: run actual Lean

You must actually run Lean commands.

At minimum, run:

```bash
lake build
```

and at least one of:

```bash
lake env lean ProofNet/Examples/Controlled.lean
lake env lean ProofNet/Examples/ControlledInstrumented.lean
lake exe proofnet_boundary_lens_extract
```

If the environment lacks Lean/Lake, install or activate Lean through the project’s `lakefile.lean`, `lean-toolchain`, or `elan` if feasible. If installation is impossible, stop and report the exact blocker. Do not proceed by pretending results are Lean-extracted.

Your final report must include:
- exact commands run;
- stdout/stderr excerpts;
- whether `lake build` passed;
- whether each controlled theorem elaborated;
- where the emitted JSONL came from.

---

## 2. Input package

Start from the current project workspace. Inspect all of the following if present:

```text
proofnet_state_extractor_v05/
proofnet_v07_boundary_lens_nextstep/
proofnet_boundary_lens_v12/
```

If these are zip files, unzip them into a clean working directory.

The most likely implementation base is the v0.5 Lean extractor. Inspect:

```text
ProofNet/Extract/InfoTree.lean
ProofNet/Extract/State.lean
ProofNet/Extract/Expr.lean
ProofNet/Extract/Delta.lean
scripts/run_state_extractor.py
scripts/validate_state_extractor.py
```

Use the v0.7 reference package for schemas and algorithms:

```text
scripts/boundary_lens_core.py
scripts/repair_v05_frontier_transport.py
schemas/proofnet_lens_trace_step_schema_v0_7.json
schemas/proofnet_boundary_graph_schema_v0_7.json
reports/ENGINEERING_IMPLEMENTATION.md
reports/MATHEMATICAL_FORMALISM.md
```

---

## 3. Required implementation strategy

There are two acceptable implementation modes.

### Mode A: Lean-side `proofnet_step` wrapper

Preferred if feasible.

Implement a tactic:

```lean
proofnet_step "constructor"
proofnet_step "exact h.right"
proofnet_step "apply hqr"
```

The tactic must:
1. capture the Lean tactic state before;
2. execute the tactic string in the same tactic session;
3. capture the Lean tactic state after;
4. emit a JSON record containing before/after state;
5. preserve raw Lean metavariable IDs in the emitted data.

If arbitrary tactic-string execution is hard, implement controlled wrappers for the core tactics:

```lean
pn_constructor
pn_exact h.right
pn_intro hp
pn_apply hqr
pn_left
pn_right
pn_assumption
pn_rfl
pn_rw [h]
pn_simp
```

Then write controlled examples using these wrappers. Be honest in the report.

### Mode B: same-session source instrumentation

Acceptable for v0.7.1 if Mode A is too hard.

Implement a source transformer that turns:

```lean
constructor
exact h.right
exact h.left
```

into:

```lean
proofnet_state "before:0"
constructor
proofnet_state "after:0"

proofnet_state "before:1"
exact h.right
proofnet_state "after:1"

proofnet_state "before:2"
exact h.left
proofnet_state "after:2"
```

Then run the instrumented Lean file once through:

```bash
lake env lean ProofNet/Examples/ControlledInstrumented.lean
```

This is acceptable only if:
- Lean runs the whole proof in one actual session;
- before/after states are captured from the actual Lean run;
- Python postprocessing performs persistent `ρ`-transport using the real metavariable IDs emitted by Lean;
- the report clearly says that v0.7.1 uses source instrumentation rather than a general tactic-string wrapper.

Do not use independent prefix replay as the final method for v0.7.1.

---

## 4. Required Lean state capture

For every captured state, record all open goals.

Each goal record must include:

```json
{
  "mvar_id": "?m.123",
  "target_pretty": "...",
  "target_hash": "...",
  "local_context": [
    {
      "fvar_id": "...",
      "user_name": "h",
      "type_pretty": "p ∧ q",
      "type_hash": "...",
      "binder_info": "...",
      "is_implementation_detail": false
    }
  ]
}
```

At minimum, implement:
- metavariable ID;
- target pretty string;
- target hash;
- local hypothesis names and types;
- local context hash.

If true structural expression hashing is not completed, implement MVP hashing:

```text
sha256(pretty-printed expression with lightweight alpha-normalization)
```

But isolate it behind a function named something like:

```lean
structuralHashMVP
```

or:

```python
structural_hash_mvp
```

and document that it is not final.

---

## 5. Boundary capsules

A boundary capsule is the normalized Lean interface of an open goal.

For every open goal, emit:

```json
{
  "mvar_id": "?m.123",
  "graph_node_id": "goal.abc",
  "target_pretty": "...",
  "target_structural_hash": "...",
  "local_context": [...],
  "boundary_hash": "..."
}
```

In v0.7.1, `graph_node_id` may be assigned during Python postprocessing, but it must be stable under frontier transport.

The boundary hash must not include:
- theorem family labels;
- manual graph labels;
- tactic source text;
- graph node IDs;
- expected equivalence-class labels.

---

## 6. Persistent frontier transport

Implement Python postprocessing or Lean-side state update:

```text
ρ_i : MVarId → GraphNodeId
```

Algorithm:

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
        rho_after[m] = fresh_goal_node_id(m)

    if tactic_is_focused(tactic_kind):
        consumed = {focused_before} if focused_before in disappeared else set()
        accidental = disappeared - consumed
        if accidental:
            raise FrontierTransportError(
                f"Focused tactic {tactic_kind} unexpectedly consumed sibling goals: {accidental}"
            )
    else:
        consumed = disappeared

    return rho_after, consumed, preserved, created
```

This must be tested on the conjunction theorem.

---

## 7. Tactic delta rules to implement now

Implement typed graph-delta rules for at least:

```text
constructor
exact
intro
apply
left
right
assumption
rfl
rw
have
linarith or omega if available
simp if available
```

Minimum acceptable controlled reliable subset:

```text
constructor
exact
intro
apply
left
right
assumption
rfl
rw
have
```

Graph-delta examples:

### constructor

```json
{
  "nodes_added": [
    {"id": "step.0", "type": "TacticStep", "label": "constructor"},
    {"id": "goal.1", "type": "OpenGoal", "label": "q"},
    {"id": "goal.2", "type": "OpenGoal", "label": "p"}
  ],
  "edges_added": [
    {"source": "goal.0", "target": "step.0", "type": "decomposes", "verification": "lean_transition_verified"},
    {"source": "step.0", "target": "goal.1", "type": "creates_subgoal", "verification": "lean_transition_verified"},
    {"source": "step.0", "target": "goal.2", "type": "creates_subgoal", "verification": "lean_transition_verified"},
    {"source": "goal.1", "target": "goal.2", "type": "sibling_independent", "verification": "heuristic_boundary_disjoint"}
  ]
}
```

### exact

```json
{
  "nodes_added": [
    {"id": "step.1", "type": "TacticStep", "label": "exact h.right"},
    {"id": "term.1", "type": "Term", "label": "h.right"}
  ],
  "edges_added": [
    {"source": "term.1", "target": "step.1", "type": "constructs", "verification": "lean_transition_verified"},
    {"source": "step.1", "target": "goal.1", "type": "closes", "verification": "lean_transition_verified"}
  ],
  "frontier_updates": [
    {"action": "close", "node_id": "goal.1"},
    {"action": "preserve", "node_id": "goal.2"}
  ]
}
```

### apply

```json
{
  "edges_added": [
    {"source": "lemma.hqr", "target": "step.2", "type": "applies_lemma", "verification": "tactic_argument_observed"},
    {"source": "goal.r", "target": "step.2", "type": "reduced_by_apply", "verification": "lean_transition_verified"},
    {"source": "step.2", "target": "goal.q", "type": "creates_subgoal", "verification": "lean_transition_verified"}
  ]
}
```

### rw

```json
{
  "edges_added": [
    {"source": "hyp.h1", "target": "step.rw", "type": "rewrite_rule", "verification": "tactic_argument_observed"},
    {"source": "old_target", "target": "new_target", "type": "rewrites_to", "verification": "lean_transition_verified"}
  ]
}
```

For automation:
- use `AutomationBundle`;
- mark details as `coarse_verified`;
- do not claim extracted internal proof search unless it is actually extracted.

---

## 8. Controlled examples that must run in Lean

Create:

```text
ProofNet/Examples/Controlled.lean
```

or:

```text
ProofNet/Examples/ControlledInstrumented.lean
```

Include at least five examples.

### Example 1: conjunction sibling preservation

```lean
theorem cex_and_constructor_exact (p q : Prop) (h : p ∧ q) : q ∧ p := by
  constructor
  exact h.right
  exact h.left
```

### Example 2: disjunction

```lean
theorem cex_or_left (p q : Prop) (hp : p) : p ∨ q := by
  left
  exact hp
```

### Example 3: implication chain

```lean
theorem cex_imp_trans (p q r : Prop) (hpq : p → q) (hqr : q → r) : p → r := by
  intro hp
  apply hqr
  apply hpq
  exact hp
```

### Example 4: equality rewrite

Use a theorem that actually works in Lean. For example:

```lean
theorem cex_rw_eq2 {α : Type} (a b c : α) (h1 : a = b) (h2 : b = c) : a = c := by
  rw [h1]
  exact h2
```

If orientation causes problems, fix the theorem/proof but keep the rewrite example.

### Example 5: intermediate claim

```lean
theorem cex_have (p q : Prop) (hp : p) (hpq : p → q) : p ∧ q := by
  have hq : q := by
    exact hpq hp
  constructor
  exact hp
  exact hq
```

### Optional Example 6: arithmetic automation

If Mathlib/tactic imports are available:

```lean
import Mathlib

theorem cex_linarith (a b c : ℤ) (h1 : a ≤ b) (h2 : b ≤ c) : a ≤ c := by
  linarith
```

If unavailable, skip and document.

---

## 9. Failure branch examples

Create controlled candidate failures.

Examples:

```lean
-- wrong projection:
-- in goal q, candidate exact h.left should fail if h.left : p

-- wrong exact:
-- in goal p ∨ q, candidate exact hp should fail because hp : p

-- wrong rfl:
theorem cex_bad_rfl {α : Type} (a b : α) (h : a = b) : b = a := by
  -- candidate rfl should fail
  exact h.symm
```

How to implement failure generation:

Option A:
- Have a Python script create temporary Lean files with candidate tactics inserted at marked states.
- Run `lake env lean`.
- Capture error excerpts.
- Emit `failure_branches.jsonl`.

Option B:
- If feasible, implement Lean-side candidate evaluation in `try` mode.
- Candidate failure must not modify the verified cumulative graph.

Each failure branch must include:
- state_before;
- candidate_tactic;
- lean_result = failure;
- error_excerpt;
- failure_type;
- ghost candidate delta;
- reason_to_prune_or_penalize.

---

## 10. Required output files

Produce:

```text
data/actual_lean_boundary_lens_trace_steps.jsonl
data/actual_lean_boundary_graph_snapshots.jsonl
data/actual_lean_failure_branches.jsonl

reports/ACTUAL_LEAN_RUN_REPORT.md
reports/CONTROLLED_TRACE_RESULTS.md
reports/FRONTIER_TRANSPORT_INVARIANT_REPORT.md
reports/KNOWN_LIMITATIONS.md

scripts/run_actual_lean_boundary_lens.py
scripts/postprocess_actual_lean_logs.py
scripts/validate_actual_lean_boundary_lens.py
```

If you implement Lean modules, produce:

```text
ProofNet/Boundary/Capsule.lean
ProofNet/Boundary/Trace.lean
ProofNet/Boundary/TacticWrapper.lean
ProofNet/Boundary/Main.lean
ProofNet/Examples/Controlled.lean
ProofNet/Examples/ControlledInstrumented.lean
```

If you use source instrumentation mode, also produce:

```text
scripts/instrument_controlled_lean.py
```

---

## 11. Validation requirements

Your validator must check:

```text
1. every success record comes from actual Lean logs;
2. every success record has non-null state_before and state_after;
3. every failure record has state_before and null state_after;
4. no model-input statement contains ':= by';
5. every state_after open goal has exactly one frontier_after node;
6. every frontier_after node has one boundary capsule;
7. sibling goal preservation passes on cex_and_constructor_exact;
8. graph deltas marked lean_transition_verified occur only on accepted Lean transitions;
9. rejected candidate deltas are marked ghost_rejected;
10. JSONL records satisfy the schema.
```

The sibling preservation report must explicitly show:

```text
After constructor:
  frontier = [G_q, G_p]

After exact h.right:
  consumed = [G_q]
  preserved = [G_p]
  G_p after exact h.right has the same graph_node_id as after constructor.

After exact h.left:
  consumed = [G_p]
  frontier = []
```

---

## 12. Frontier/condensed-math pilot

Do not try to fully build Lean Liquid or PFR unless the environment already supports it.

But add one frontier pilot report:

```text
reports/FRONTIER_PILOT_PLAN.md
```

It must say one of the following:

### If only controlled examples were run:

```text
No frontier theorem was Lean-state extracted in this run.
Lean Liquid/PFR examples remain bronze_source_plan.
Reason: dependencies not available / not built / not attempted.
```

### If a real Mathlib or Lean Liquid theorem was run:

Then include:
- exact import;
- theorem name;
- exact command run;
- number of trace records;
- state_before/state_after excerpts;
- extraction tier = `silver_tactic_state`.

Do not overclaim.

---

## 13. Final console summary

At the end, print:

```text
v0.7.1 actual Lean Boundary-Lens extraction complete.

Lean build: PASS/FAIL
Lean session run: PASS/FAIL
Controlled theorems traced: ...
Success trace records: ...
Failure branch records: ...
Frontier invariant: PASS/FAIL
Sibling preservation: PASS/FAIL
Schema validation: PASS/FAIL
Proof leakage check: PASS/FAIL
Extraction tier achieved:
  controlled examples: silver_tactic_state / failed
  frontier examples: bronze_source_plan / silver_tactic_state
Known limitations:
  ...
```

---

## 14. Critical success condition

The project only counts as successful if the extracted records come from an actual Lean run.

If the final result is only Python-simulated or source-derived, mark it as:

```text
NOT COMPLETED: actual Lean session extraction was not achieved.
```

Do not hide this. Honesty is mandatory.

---

## 15. Final instruction

Make the smallest real system that proves the key idea:

> Real Lean tactic transitions can be converted into partial proof-net boundary graphs while preserving open-goal identity.

Do not chase breadth. Do not attempt huge Mathlib/PFR/Liquid builds before the controlled examples are correct.

A correct trace for five small Lean theorems is the required milestone.
