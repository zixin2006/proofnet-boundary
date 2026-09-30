# Codex Prompt: Implement v0.7 Same-Session Boundary-Lens ProofNet Extractor

You are working on the ProofNet project: **The Geometry of Proof Search: Proof-Net Abstractions for Neural Theorem Proving**.

Your task is to implement **v0.7: a same-session Boundary-Lens extractor** for Lean 4. This is the next technical step after the v0.5 state extractor and the v1.2 Boundary-Lens methodology.

The purpose of v0.7 is to convert Lean tactic proofs into **Lean-certified partial proof-net-inspired frontier graphs** by recording tactic-state transitions in the same Lean execution session, maintaining persistent open-goal identity, and emitting graph deltas whose verified edges come only from accepted Lean transitions.

Do not implement neural training yet. This task is purely about **correct extraction, schemas, validation, and controlled examples**.

---

## 0. Project context

The key object is not merely a graph. It is a boundary-lens proof state:

```text
B_i = (s_i, G_i, ρ_i, ∂_i)
```

where:

```text
s_i  = Lean tactic state at step i
G_i  = cumulative partial proof graph
ρ_i  = persistent map from Lean metavariable goals to graph frontier nodes
∂_i  = boundary map from normalized Lean goal capsules to open graph ports
```

A tactic step should produce:

```text
(s_i, G_i, ρ_i, ∂_i) --t_i-->
(s_{i+1}, G_{i+1}, ρ_{i+1}, ∂_{i+1})
```

with:

```text
G_{i+1} = G_i ∪ ΔG_i
```

and:

```text
ΔG_i = ExtractLensDelta(s_i, t_i, s_{i+1}, G_i, ρ_i, ∂_i).
```

The central invariant is:

```text
Every open Lean goal in s_i corresponds to exactly one open frontier node in G_i.
```

A graph edge may be marked `"verified"` only if it comes from an accepted Lean tactic transition or from proof-term/kernel/environment inspection.

---

## 1. Main engineering objective

Implement a same-session extractor that can trace a Lean theorem proof step by step and output JSONL records of this form:

```json
{
  "schema_version": "1.2",
  "record_type": "lens_trace_step",
  "theorem_id": "...",
  "variant_id": "...",
  "step_index": 0,
  "state_before": {
    "goals": [...],
    "focused_goal": {...},
    "locals": [...],
    "boundary_capsules": [...]
  },
  "tactic": {
    "raw": "constructor",
    "kind": "constructor",
    "source_span": null,
    "arguments": []
  },
  "state_after": {
    "goals": [...],
    "focused_goal": {...},
    "locals": [...],
    "boundary_capsules": [...]
  },
  "frontier_before": [...],
  "frontier_after": [...],
  "rho_before": {...},
  "rho_after": {...},
  "boundary_before_hash": "...",
  "boundary_after_hash": "...",
  "graph_before_hash": "...",
  "graph_delta": {
    "nodes_added": [...],
    "edges_added": [...],
    "nodes_updated": [...],
    "frontier_updates": [...]
  },
  "graph_after_hash": "...",
  "lean_result": "success",
  "verification_status": "lean_transition_verified"
}
```

Failure records must also be generated:

```json
{
  "schema_version": "1.2",
  "record_type": "lens_trace_step",
  "theorem_id": "...",
  "variant_id": "...",
  "step_index": 0,
  "state_before": {...},
  "tactic": {
    "raw": "bad tactic",
    "kind": "unknown_or_candidate"
  },
  "state_after": null,
  "frontier_before": [...],
  "frontier_after": null,
  "rho_before": {...},
  "rho_after": null,
  "graph_before_hash": "...",
  "graph_delta": {
    "nodes_added": [...],
    "edges_added": [...],
    "nodes_updated": [],
    "frontier_updates": [],
    "candidate_delta_status": "ghost_rejected"
  },
  "graph_after_hash": null,
  "lean_result": "failure",
  "error_excerpt": "...",
  "failure_type": "...",
  "verification_status": "lean_rejected"
}
```

Important: failure records may contain **ghost candidate deltas**, but those deltas must not be marked verified.

---

## 2. Existing code to inspect first

Inspect the current package before writing code. In particular, inspect the v0.5 files:

```text
ProofNet/Extract/InfoTree.lean
ProofNet/Extract/State.lean
ProofNet/Extract/Expr.lean
ProofNet/Extract/Delta.lean
scripts/run_state_extractor.py
scripts/validate_state_extractor.py
data/extracted_trace_steps.jsonl
```

Also inspect the v1.2 methodology package if it exists in the workspace:

```text
schemas/proofnet_boundary_graph_schema_v1_2.json
schemas/proofnet_lens_trace_step_schema_v1_2.json
reports/EUREKA_BOUNDARY_LENS_METHOD.md
reports/ENGINEERING_ALGORITHM.md
reports/MATHEMATICAL_FORMALISM.md
data/example_controlled_and_partial_ai.jsonl
```

Use v0.5 as the implementation base, but correct its main conceptual flaw:

```text
v0.5 tends to consume all frontier goals at each tactic step.
v0.7 must consume only the focused goal for ordinary focused tactics
and must preserve unchanged sibling goals through ρ-transport.
```

---

## 3. Required architecture

Create or update the following Lean modules:

```text
ProofNet/Boundary/Capsule.lean
ProofNet/Boundary/Expr.lean
ProofNet/Boundary/Graph.lean
ProofNet/Boundary/Lens.lean
ProofNet/Boundary/Trace.lean
ProofNet/Boundary/TacticWrapper.lean
ProofNet/Boundary/Main.lean
```

The exact file names may vary if the existing package structure requires it, but keep the architecture logically separated.

Create or update the following Python scripts:

```text
scripts/run_boundary_lens_extractor.py
scripts/validate_boundary_lens_dataset.py
scripts/render_boundary_graph_examples.py
```

Create or update data/report outputs:

```text
data/boundary_lens_trace_steps.jsonl
data/boundary_graphs.jsonl
data/failure_branches.jsonl

reports/BOUNDARY_LENS_EXTRACTOR_IMPLEMENTATION.md
reports/CONTROLLED_TEST_RESULTS.md
reports/KNOWN_LIMITATIONS.md
```

---

## 4. Same-session extraction requirement

The most important technical requirement is same-session extraction.

Do not implement v0.7 as independent prefix replay where every step is run in a fresh Lean process. Prefix replay loses stable metavariable identity and makes frontier transport unreliable.

Preferred implementation:

1. Define a tracing tactic wrapper, for example:

```lean
proofnet_step "constructor"
proofnet_step "exact h.right"
proofnet_step "exact h.left"
```

or, if feasible:

```lean
by
  proofnet_trace
    constructor
    exact h.right
    exact h.left
```

2. The wrapper should:
   - capture state before the tactic;
   - execute the tactic in the current session;
   - capture state after the tactic;
   - update persistent extractor state;
   - emit one JSON object.

3. If direct parsing of arbitrary tactic strings is hard, implement a controlled subset first using tactic-specific wrappers:

```lean
pn_constructor
pn_exact h.right
pn_assumption
pn_intro x
pn_rcases h with ...
pn_have ...
pn_rw [...]
pn_simp [...]
```

The final report must clearly state which mode was implemented:
- arbitrary tactic string wrapper;
- tactic-specific wrappers;
- Python source transformer inserting wrappers;
- or a hybrid.

A controlled subset is acceptable, but it must be honest and robust.

---

## 5. Boundary capsules

Implement a `BoundaryCapsule` data structure.

Each open Lean goal should yield one capsule:

```json
{
  "mvar_id": "?m.123",
  "graph_node_id": "goal.main.0",
  "target_pretty": "q ∧ p",
  "target_structural_hash": "...",
  "local_context": [
    {
      "fvar_id": "...",
      "user_name": "h",
      "type_pretty": "p ∧ q",
      "type_structural_hash": "...",
      "binder_info": "default",
      "is_implementation_detail": false
    }
  ],
  "typeclass_instances": [],
  "universe_context": [],
  "boundary_hash": "..."
}
```

At minimum, capture:

```text
mvar_id
target expression
target pretty string
target structural hash or normalized string hash
local declarations
local declaration types
local declaration stable local IDs if available
```

If true structural hashing is too hard, implement a clearly marked MVP:

```text
target_structural_hash = sha256(pretty-printed target after alpha-normalizing local names as much as possible)
```

But isolate this in one function so it can later be replaced by real Lean expression hashing.

Do not use theorem family labels, manually assigned graph labels, expected equivalence classes, or node IDs as model features.

---

## 6. Persistent frontier transport

Implement:

```text
ρ_i : MVarId → GraphNodeId
```

For each tactic transition:

1. Capture goals before:
   ```text
   goals_before : List MVarId
   focused_before : first goal, if any
   ```

2. Capture goals after:
   ```text
   goals_after : List MVarId
   ```

3. Transport frontier:
   - If an old metavariable ID remains in `goals_after`, map it to the same graph node ID.
   - If the focused goal disappears, mark its node closed/decomposed/transformed depending on tactic kind.
   - If new metavariable IDs appear, create new open goal nodes.
   - If an old sibling goal remains but changes position in the goal list, preserve its graph node ID.
   - For ordinary focused tactics, do not consume sibling goals.

Pseudo-code:

```python
def transport_frontier(rho_before, goals_before, focused_before, goals_after, tactic_kind):
    rho_after = {}

    old_goal_set = set(goals_before)
    new_goal_set = set(goals_after)

    preserved = old_goal_set & new_goal_set
    closed_or_replaced = old_goal_set - new_goal_set
    newly_created = new_goal_set - old_goal_set

    for mvar in preserved:
        rho_after[mvar] = rho_before[mvar]

    for mvar in newly_created:
        rho_after[mvar] = fresh_goal_node_id(mvar)

    if tactic_is_focused(tactic_kind):
        consumed = {focused_before} if focused_before in closed_or_replaced else set()
        untouched_closed = closed_or_replaced - consumed
        assert not untouched_closed or tactic_kind in MULTIGOAL_TACTICS
    else:
        consumed = closed_or_replaced

    return rho_after, consumed, preserved, newly_created
```

This is the central fix. Implement tests specifically for this.

---

## 7. Tactic-specific graph deltas

Implement at least these tactics for v0.7 controlled tests:

```text
intro / intros
constructor
exact
assumption
apply
refine
left
right
rcases
cases
have
rw
simp
rfl
linarith
omega
ring
aesop
```

It is acceptable to support some of these at a coarse level. The minimum required reliable subset is:

```text
intro
constructor
exact
assumption
apply
refine
left
right
have
rcases
rw
rfl
simp
linarith
```

For each tactic, emit graph deltas as follows.

### intro / intros

State effect:
```text
Π / ∀ / → goal introduces local variable or hypothesis.
```

Graph:
```text
Goal --introduces_hypothesis/introduces_variable--> Local/Hypothesis
Goal --frontier_transformed--> NewGoal
```

Reliability:
```text
High if local context diff is captured.
```

### constructor

State effect:
```text
One focused goal becomes multiple constructor subgoals.
```

Graph:
```text
FocusedGoal --decomposes--> TacticStep
TacticStep --creates_subgoal--> NewGoal1
TacticStep --creates_subgoal--> NewGoal2
NewGoal1 --sibling_independent--> NewGoal2, when no shared new metavariables/dependencies are detected
```

Reliability:
```text
High for ordinary conjunction/existential/product constructor goals.
Lower when typeclass search/coercions obscure constructor choice.
```

### exact

State effect:
```text
Focused goal closes if term has required type.
```

Graph:
```text
Term/Hypothesis/Lemma --constructs/closes--> FocusedGoal
```

Reliability:
```text
High if Lean accepts. Term dependency extraction may be coarse until proof-term enrichment.
```

### assumption

State effect:
```text
Focused goal closes using a matching local hypothesis.
```

Graph:
```text
Hypothesis --closes--> FocusedGoal
```

Reliability:
```text
High if local hypothesis can be matched by type to target.
```

### apply

State effect:
```text
Focused goal is reduced to premises of applied lemma/function.
```

Graph:
```text
Lemma --applies_lemma--> TacticStep
FocusedGoal --reduced_by_apply--> TacticStep
TacticStep --creates_subgoal--> PremiseGoal_i
```

Reliability:
```text
Medium from tactic state alone; high after proof-term dependency extraction.
```

### refine

State effect:
```text
Creates metavariable holes from a partial term.
```

Graph:
```text
PartialTerm --constructs_partial--> FocusedGoal
PartialTerm --creates_hole--> NewGoal_i
```

Reliability:
```text
Medium; exact hole correspondence may require syntax/proof-term inspection.
```

### left / right

State effect:
```text
Chooses one side of a disjunction/sum/existential-like constructor.
```

Graph:
```text
FocusedGoal --chooses_constructor--> LeftGoal/RightGoal
```

Reliability:
```text
High for ordinary disjunction goals.
```

### have

State effect:
```text
Creates intermediate claim; may create an auxiliary proof goal and then add a new hypothesis.
```

Graph:
```text
MainGoal --creates_intermediate_claim--> ClaimGoal
ClaimGoal --once_closed_introduces--> Hypothesis
Hypothesis --available_for--> MainGoal
```

Reliability:
```text
Medium; robust if same-session local context diff captures new hypothesis.
```

### rcases / cases

State effect:
```text
Eliminates hypothesis or variable into cases/witnesses.
```

Graph:
```text
Hypothesis --case_splits/destructs--> TacticStep
TacticStep --introduces_witness/hypothesis--> NewLocals
TacticStep --creates_case_goal--> CaseGoal_i
```

Reliability:
```text
Medium-high for local context diff; exact pattern structure from syntax is heuristic.
```

### rw

State effect:
```text
Rewrites target or hypothesis using equality lemma.
```

Graph:
```text
RewriteLemma --rewrites--> Goal
OldTarget --normalizes_to/rewrite_to--> NewTarget
```

Reliability:
```text
Medium from before/after target diff; higher with rewrite lemma parsed and proof-term enrichment.
```

### simp

State effect:
```text
Simplifies target/hypotheses using simp set.
```

Graph:
```text
AutomationBundle(simp) --rewrites/simplifies--> Goal
```

Reliability:
```text
Coarse verified. Detailed simp lemma extraction is future work unless easy via Lean tracing.
```

### rfl

State effect:
```text
Closes definitional equality.
```

Graph:
```text
DefinitionalEquality --closes--> Goal
```

Reliability:
```text
High if Lean accepts.
```

### linarith / omega / ring / aesop

State effect:
```text
Automation closes or transforms goal.
```

Graph:
```text
AutomationBundle(kind) --uses--> relevant locals if identifiable
AutomationBundle(kind) --closes/transforms--> Goal
```

Reliability:
```text
Coarse verified only. Do not pretend to expose internal proof search unless extracted.
```

---

## 8. Speculative partial-AI branches

Implement a data representation for candidate tactics that are proposed but not yet accepted.

The extractor should support a mode where candidate tactics are tried from the current state, and each candidate yields either:

```text
accepted verified delta
```

or:

```text
rejected ghost delta
```

Do not pollute the cumulative verified graph with rejected ghost deltas.

A failure branch should include:

```json
{
  "candidate_tactic": "exact h.left",
  "lean_result": "failure",
  "error_excerpt": "...",
  "failure_type": "type_mismatch",
  "candidate_graph_delta": {
    "status": "ghost_rejected",
    "predicted_effect": "close_focused_goal",
    "verified": false
  },
  "reason_to_prune_or_penalize": "candidate term type does not match focused target"
}
```

Use failure branches for controlled tests:
- wrong projection;
- wrong disjunction side;
- `rfl` on non-definitional equality;
- `linarith` without sufficient hypotheses;
- `rw` with wrong rewrite lemma or direction.

---

## 9. Required controlled test theorems

Add a controlled Lean test file, for example:

```text
ProofNet/Examples/Controlled.lean
```

Include at least these theorems.

### 9.1 Conjunction constructor transport

```lean
theorem cex_and_constructor_exact (p q : Prop) (h : p ∧ q) : q ∧ p := by
  proofnet_step "constructor"
  proofnet_step "exact h.right"
  proofnet_step "exact h.left"
```

Expected:
```text
constructor creates two subgoals;
exact h.right closes only q;
p subgoal keeps the same graph node identity;
exact h.left closes p.
```

### 9.2 Disjunction branch choice

```lean
theorem cex_or_left (p q : Prop) (hp : p) : p ∨ q := by
  proofnet_step "left"
  proofnet_step "exact hp"
```

Expected:
```text
left chooses left disjunct;
new goal p is closed by hp.
```

### 9.3 Intro and assumption

```lean
theorem cex_imp_trans (p q r : Prop) (hpq : p → q) (hqr : q → r) : p → r := by
  proofnet_step "intro hp"
  proofnet_step "apply hqr"
  proofnet_step "apply hpq"
  proofnet_step "exact hp"
```

Expected:
```text
intro introduces hp;
apply hqr reduces r to q;
apply hpq reduces q to p;
exact hp closes p.
```

### 9.4 Equality rewrite

```lean
theorem cex_rw_eq {α : Type} (a b : α) (h : a = b) : b = a := by
  proofnet_step "rw [h]"
```

If this exact example fails due to orientation, use a correct controlled rewrite such as:

```lean
theorem cex_rw_eq2 {α : Type} (a b c : α) (h1 : a = b) (h2 : b = c) : a = c := by
  proofnet_step "rw [h1]"
  proofnet_step "exact h2"
```

Expected:
```text
rw records rewrite lemma h1 and target change;
exact h2 closes final equality.
```

### 9.5 Have intermediate claim

```lean
theorem cex_have (p q : Prop) (hp : p) (hpq : p → q) : p ∧ q := by
  proofnet_step "have hq : q := by exact hpq hp"
  proofnet_step "constructor"
  proofnet_step "exact hp"
  proofnet_step "exact hq"
```

Expected:
```text
have creates intermediate claim q;
the new hypothesis hq is available to the main goal;
constructor splits;
each branch closes independently.
```

### 9.6 Arithmetic automation

```lean
theorem cex_linarith (a b c : ℤ) (h1 : a ≤ b) (h2 : b ≤ c) : a ≤ c := by
  proofnet_step "linarith"
```

Expected:
```text
linarith closes the focused goal using automation bundle.
```

If `linarith` imports are unavailable in this package, mark the test as optional and document the missing import.

---

## 10. Frontier pilot examples

Do not attempt full PFR or Lean Liquid extraction unless their dependencies build in the environment.

Instead, implement a **frontier pilot interface**:

```text
ProofNet/Examples/FrontierPilot.lean
```

Use one of these options:

### Option A: source-derived bronze only

If frontier projects are unavailable, create records labeled:

```text
extraction_tier = "bronze_source_plan"
verification_status = "not_lean_state_extracted"
```

Use examples inspired by:
- Bolzano–Weierstrass;
- compactness/subsequence extraction;
- PFR-style obtain/have/refine proof skeleton;
- Liquid Tensor source schedule.

Do not claim silver/gold status.

### Option B: local Mathlib theorem

If Mathlib is available, trace a small real Mathlib theorem using imports that build quickly. Prefer a compactness or sequence theorem with `have`, `obtain`, `rw`, `exact`, and `apply`.

Output must clearly say:

```text
frontier_pilot_status = "actual_lean_state_extracted"
```

only if state_before/state_after were truly extracted from Lean.

---

## 11. Schema validation

Implement JSON Schema validation in Python.

Validate:

```text
data/boundary_lens_trace_steps.jsonl
data/boundary_graphs.jsonl
data/failure_branches.jsonl
```

Against:

```text
schemas/proofnet_lens_trace_step_schema_v1_2.json
schemas/proofnet_boundary_graph_schema_v1_2.json
```

Fix the v0.5 issue where failure records had:

```json
"graph_after_hash": null
```

while the schema expected only string. The schema should allow `null` for failure records, or use `oneOf` with success/failure variants.

The validator must check at least:

```text
1. every success record has state_before and state_after;
2. every failure record has state_before and null state_after;
3. every open goal in state_after appears exactly once in frontier_after;
4. every frontier_after node has a corresponding boundary capsule;
5. sibling goals preserved across focused tactic steps keep the same graph node ID;
6. no model_input field contains proof body or ':= by';
7. graph deltas marked verified occur only on successful Lean transitions;
8. ghost deltas occur only on candidate/failure branches;
9. hashes are deterministic across reruns when Lean pretty-printing is stable.
```

---

## 12. Output reports

Write the following reports.

### `reports/BOUNDARY_LENS_EXTRACTOR_IMPLEMENTATION.md`

Include:
```text
implemented architecture;
exact Lean modules;
how same-session extraction works;
whether arbitrary tactic strings or tactic-specific wrappers are used;
how ρ is stored and updated;
how boundary capsules are computed;
how graph deltas are constructed;
what is verified and what is heuristic.
```

### `reports/CONTROLLED_TEST_RESULTS.md`

Include:
```text
all controlled theorem names;
number of trace records;
success/failure counts;
frontier invariant checks;
multi-goal transport result;
example graph deltas;
known failed tests.
```

### `reports/KNOWN_LIMITATIONS.md`

Include:
```text
expression normalization limitations;
tactic parsing limitations;
automation opacity;
lack of full proof-term enrichment;
limitations of pretty-string hashing;
typeclass inference caveats;
frontier project availability;
what remains bronze/silver/gold.
```

---

## 13. Acceptance criteria

The task is complete only if all of the following are true.

### Required

```text
[ ] Same-session extraction is implemented or an honest controlled same-session wrapper is implemented.
[ ] At least five controlled theorems produce JSONL trace records.
[ ] The conjunction example preserves sibling goal identity after the first exact step.
[ ] Success and failure records are both generated.
[ ] Frontier invariant validation passes.
[ ] Schema validation passes.
[ ] No model-input statement contains ':= by' or proof body leakage.
[ ] Reports are written.
```

### Strongly preferred

```text
[ ] Tactic kind classification works for intro, constructor, exact, apply, have, rw, simp, rfl, linarith.
[ ] Graph deltas include typed edges rather than generic state-diff edges only.
[ ] Boundary capsules include local context and target hashes.
[ ] Failure branches include ghost candidate deltas.
[ ] There is a small Mathlib/frontier pilot clearly labeled by extraction tier.
```

---

## 14. Do not overclaim

Use the following tier labels honestly:

```text
bronze_source_plan:
  source-derived only; no real Lean state transitions.

silver_tactic_state:
  real Lean state_before/state_after transitions; graph deltas from tactic effects.

gold_proof_term_enriched:
  silver plus proof-term/kernel/environment dependencies.

search_branch:
  positive and negative candidate tactics from actual search attempts.
```

Do not call PFR, Liquid Tensor, or any frontier theorem “silver” unless the extractor actually ran inside the corresponding Lean project and emitted real `state_before` / `state_after`.

Do not call graph edges proof-term verified unless they were obtained by proof-term/kernel/environment inspection.

Do not use manual theorem-family labels as model features.

Do not use graph hash alone as pruning key. The safe key is:

```text
PruningKey = (NormalizeLeanState(s_i), CanonicalizeBoundaryGraph(G_i → Boundary(s_i))).
```

---

## 15. Suggested implementation strategy

Proceed in phases.

### Phase 1: stabilize data types

Implement Lean/Python data types for:

```text
BoundaryCapsule
LocalDeclCapsule
GraphNode
GraphEdge
GraphDelta
LensTraceStep
ExtractorState
```

### Phase 2: implement capture

Port the v0.5 `proofnet_state` mechanism into a richer `captureBoundary` function.

Capture:

```text
goals;
focused goal;
target;
local context;
metavariable ID;
pretty strings;
hashes.
```

### Phase 3: implement persistent ρ

Maintain extractor state across steps.

If Lean-side persistent state is hard, use a same-session wrapper that emits before/after states with raw mvar IDs, then perform ρ-transport in Python in the same run. This is acceptable for v0.7 if the report is explicit.

### Phase 4: implement tactic wrappers

Start with:

```text
proofnet_step "constructor"
proofnet_step "exact h.right"
proofnet_step "exact h.left"
```

If arbitrary tactic strings are hard, implement named wrappers first.

### Phase 5: graph delta construction

Construct deltas using before/after state and tactic kind.

Do not rely on source parsing alone for verified edges.

### Phase 6: validation and reports

Run controlled examples, validate schemas, write reports.

---

## 16. Final deliverables

At the end, produce:

```text
ProofNet/Boundary/*.lean
ProofNet/Examples/Controlled.lean
ProofNet/Examples/FrontierPilot.lean

scripts/run_boundary_lens_extractor.py
scripts/validate_boundary_lens_dataset.py
scripts/render_boundary_graph_examples.py

data/boundary_lens_trace_steps.jsonl
data/boundary_graphs.jsonl
data/failure_branches.jsonl

schemas/proofnet_lens_trace_step_schema_v1_2.json
schemas/proofnet_boundary_graph_schema_v1_2.json

reports/BOUNDARY_LENS_EXTRACTOR_IMPLEMENTATION.md
reports/CONTROLLED_TEST_RESULTS.md
reports/KNOWN_LIMITATIONS.md
```

Also produce a final short console summary:

```text
v0.7 Boundary-Lens extractor complete.

Trace records: ...
Success records: ...
Failure records: ...
Controlled theorems traced: ...
Frontier invariant: PASS/FAIL
Schema validation: PASS/FAIL
Sibling goal preservation test: PASS/FAIL
Proof leakage check: PASS/FAIL
Extraction tiers:
  bronze_source_plan: ...
  silver_tactic_state: ...
  gold_proof_term_enriched: ...
Known limitations:
  ...
```

---

## 17. One crucial regression test

The most important test is this.

For:

```lean
theorem cex_and_constructor_exact (p q : Prop) (h : p ∧ q) : q ∧ p := by
  proofnet_step "constructor"
  proofnet_step "exact h.right"
  proofnet_step "exact h.left"
```

The trace must show:

```text
Step 0:
  frontier_before = [G0]
  frontier_after  = [G1, G2]
  G1 target = q
  G2 target = p

Step 1:
  tactic = exact h.right
  consumed = [G1]
  preserved = [G2]
  frontier_after = [G2]
  G2 has the same graph_node_id as in Step 0

Step 2:
  tactic = exact h.left
  consumed = [G2]
  frontier_after = []
```

If this fails, v0.7 has not solved the main caveat.

---

## 18. Final instruction

Focus on correctness, honesty, and traceability.

A small extractor that correctly handles five controlled examples with persistent frontier transport is much more valuable than a large extractor that emits shallow or misleading graph records.

Implement the smallest robust v0.7 system that proves the Boundary-Lens idea works.
