# Codex implementation prompt: audit and integrate Boundary-Lens into proof-graphs

You are working with two collaborators on a joint ProofNet research program. Implement the next **bounded, executable** integration step. Do not produce only another methodology document. Do not claim improvement in theorem proving until an appropriate experiment has been run.

## 0. Pins, ownership, and limits

Inspected reference commits:

- `fushanbobfan/proofnet-ir`: `261f2db26aac842534f4306da0f45d8c5e9b1c05`.
- `fushanbobfan/proof-graphs`: `8010d137af5af5040fcbcd9e98f910b01162263e`.
- User's earlier input: `proofnet_v071_boundary_lens_complete_20260704.zip`, SHA256 `d01d806f87ca6b0855b543c3a707e2424a84821ed9ea98c8fffd31a6ae064fb1`.

Work in a new local branch of `proof-graphs`. Do not push, rewrite history, delete artifacts, or modify the other collaborator's main branch. Inspect the current worktree and stop before overwriting uncommitted work. If HEAD differs, record the difference and preserve the baseline at the supplied pin. Use the existing dependency lock, even if it pins a different ProofNet-IR commit from the separately inspected head above.

This project is not “invent graph-based Lean search.” The baseline already has real extraction, structural goal identity, renamed goal reuse, and metavariable-coupled search. Add a typed evidence layer and fix confirmed fidelity defects. Keep all historical datasets, preregistrations, and reports frozen. If an experiment becomes invalid under a correction, add a new report/experiment, never silently rewrite the old result.

Do not launch expensive model inference or frontier builds without an explicitly approved compute budget. Do not upload source or credentials to external model endpoints. No new neural training is needed for this task.

## 1. Read the existing implementation first

Read:

```
ProofGraphs/Extract.lean
scripts/count_linearizations_v2.py
scripts/run_recount.py
scripts/export_graphs.py
scripts/lean_repl.py
scripts/goal_identity.py
scripts/search_faithful.py
scripts/common_draws.py
scripts/check_faithful_repl.py
HANDOFF.md
experiments/search-v0.8/README.md
experiments/extraction-audit-v0.2/README.md
```

Read the accompanying review package's `reports/METHODOLOGY.md`, `reports/REPOSITORY_COMPARISON.md`, `reports/EXPERIMENT_PLAN.md`, and `reference/boundary_guard.py`. The Python reference is a small model, not Lean code, and its coverage assumptions must not be copied as production facts.

Inspect the actual source of the pinned Lean version before choosing APIs. Do not guess field names from a different release. The older user artifact used Lean 4.31.0; the reviewed proof-graphs handoff specifies 4.32.0. Port fixtures explicitly rather than splicing incompatible `.olean` files.

## 2. Reproduce before changing behavior

Record environment, exact commits, toolchain, dependency manifest hash, commands, return codes, and stdout/stderr. Run the documented build and bounded checks:

```
lake build
lake build repl
python scripts/run_search_coupled.py --check-committed
python scripts/check_faithful_repl.py
```

Inspect prerequisites; fetch dependencies with the normal project tooling if authorized. The artifact check recomputes committed summaries; it is NOT a fresh model-search replication. `lake build ProofNetIR` and `python scripts/run_recount.py --check-committed` may be run when their prerequisites and budget are available. Do not edit frozen outputs to make the checks pass.

If Lean cannot run, preserve new tests and report the exact blocker. Mark actual integration unverified. Do not synthesize proof states, successful kernel checks, or theorem identities.

## 3. Audit targets: confirm or refute, do not assume

The inspected code raises these concrete questions:

1. `goal_identity.py` serializes expressions to text, then normalizes metavariable-shaped tokens by regex. Does a quoted string literal containing `?[left]` or `?u.1` change and collide with a different literal?
2. A missing free-variable lookup is represented as `h?` after implementation-detail locals are skipped. Can distinct relevant locals collide, or can the declared coverage be incomplete?
3. Grouping sees directly mentioned term metavariables. Does it omit coupling through metavariable declaration types, assignments, local-definition values, or universe constraints?
4. `search_faithful.py` compares a carried goal tail with printed canonical text. Can a structural change evade that check?
5. `first`, `try`, and `repeat` can leave info nodes for failed alternatives. Which nodes represent committed transitions? Do not infer success from node presence.
6. How is an active goal removed: solved, assigned with open descendants, replaced, shelved, or suspended? Disappearance alone is not a closure certificate.

For each confirmed problem, add a minimal actual Lean regression. Include a report with the old behavior and corrected behavior. If a suspected case is unreachable or harmless under the baseline's documented restrictions, say so and retain the evidence; do not manufacture a bug report.

An expression-distinct merge is not automatically a merge of logically inequivalent propositions. Distinguish syntactic fidelity, logical equivalence, search completeness, and final theorem soundness. Final proof replay remains mandatory.

## 4. Implement a tagged Lean expression codec

Prefer additive modules such as:

```
ProofGraphs/Boundary/ExprJson.lean
ProofGraphs/Boundary/Capsule.lean
ProofGraphs/Boundary/Event.lean
ProofGraphs/Boundary/Export.lean
```

Use structural JSON tags for `Expr` and universe levels. Include all constructors supported by the pinned version. Keep string literals byte-for-byte; never regex-normalize serialized payloads. Encode local references and metavariable references as typed identities, not interpolated text.

Preserve:

- applications, constants and universe arguments;
- bound-variable indices and binder kinds;
- local declaration types, values, binder/instance status;
- relevant implementation-detail locals, or explicit unsupported coverage;
- shared-reference identity across goals, not merely per-goal pretty forms;
- term metavariable declaration types, local contexts, assignments and relevant kind/status;
- universe metavariables and the available universe-assignment/constraint information.

Keep pretty strings as debug metadata only. Unsupported expressions, missing local declarations, unknown constraints, or failed export must produce `coverage=partial/unknown` and disable strong identity/factorization claims. Do not fall back silently to a shared placeholder or to hard merges on a lossy printed key.

Use a full cryptographic digest as an index and compare the stored canonical payload before exact reuse. This still does not constitute a theorem about operational Lean-state equivalence.

## 5. Export boundaries with persistent identity and versions

Reuse the current live REPL and InfoTree pipeline. Do not create a third session driver or independent prefix-replay engine.

For each recorded checkpoint, store the ordered active goals and a dependency-closed reachable boundary. Include an explicit coverage summary. Unknown global/postponed effects should keep goals conservatively together, not declare them independent.

Maintain:

```
(session_id, raw_mvar_id) -> persistent_goal_node_id
persistent_goal_node_id -> capsule_version, content_hash
```

A raw goal identifier that remains active preserves node identity. Its instantiated target may still change when another goal assigns a shared unknown, so update the version. Changes outside the focused goal are permitted and must be recorded. Never assert locality purely from the tactic name.

Compute a transport receipt with preserved IDs, created IDs, no-longer-active IDs, and changed capsule versions. Add closure evidence separately from active-list changes.

## 6. Record transactions, not just linear tactic strings

An event must identify session, branch, parent event/transaction, tactic source, input snapshot, outcome, output snapshot, observed effects, and disposition. Store proposals separately from executed events.

Distinguish:

```
proposal: not executed
execution: success / error / timeout / unknown
transaction: committed / speculative / rolled_back
proof: incomplete / replay_passed / replay_failed
```

`refine` with holes can be an executed successful transition even though the proof is incomplete. A successful alternative can be rolled back. A failed alternative may have temporarily mutated state. Emit neither into the committed graph without transaction ancestry.

For nested tactics, choose and document extraction granularity. Do not double-count a parent container's effect and each child's effect as separate independent steps. Differentially compare the new projection with the corrected v0.2 derivation on supported cases; document genuine differences instead of forcing agreement with a known error.

The event log is append-only. Current graph snapshots are computed using `Apply(graph, delta)` with version/status updates, not only set union.

## 7. Typed edges and evidence

A minimal supported subset includes `intro`, `constructor`, `exact`, `apply`, `refine`, `rw`, `have`, and `cases`. Automation may remain an opaque bundle.

Every edge has its own evidence reference:

- source-observed argument;
- observed Lean transition;
- observed metavariable assignment;
- derived extractor annotation;
- full kernel replay receipt.

Do not mark `uses_lemma` as kernel-certified merely because the tactic string mentions it. Do not mark siblings independent merely because `constructor` created them. Do not equate `available_in_context` with `used_by_proof`. No `sorry`, `admit`, added axiom, or target self-reference may enter accepted test proofs.

## 8. Additive dataset compatibility

Keep `datasets/proof-graphs-v0.2.jsonl.gz` intact. Generate a new sidecar keyed by source commit/module/declaration/event provenance. A conversion of an old row cannot invent target expressions or state transitions. The supplied `reference/import_graph_rows.py` is deliberately only a lossless metadata adapter; it does not enrich semantics.

Use `joint-sidecar/0.1.0` or a new explicit schema version. A schema change must update the producer, validator, examples, and version together. Trace validation must check references and replay consistency, not just field presence. Do not encode proof IDs, theorem families, or manually named graph nodes in model features.

Separate audit-only full proofs from prefix-available policy inputs and future labels. Correctness fixtures may use theorem names as provenance, never as a shortcut feature.

## 9. Required actual Lean regressions

Implement and run cases for:

- conjunction sibling persistence;
- identical raw goal ID with changed instantiated target;
- shared existential witness across two obligations;
- local-definition values and instance/binder distinction;
- bound-variable and local-variable alpha renaming without capture;
- shared versus distinct metavariable aliases;
- quoted strings that look like term or universe metavariables;
- missing or implementation-detail locals;
- transitive dependencies through metavariable types;
- shared universe information, or a conservative unknown result;
- nested `have`, `simpa ... using`, and `calc`;
- failed alternatives in `first`, `try`, and `repeat`;
- export failure with no unsafe printed-key merge;
- attempted candidate failure leaves the committed snapshot unchanged;
- final proof replay against the correct source-prefix environment.

Use metaprogram-generated states where necessary; label them controlled fixtures. A fixture need not be a frontier theorem to expose a real semantic problem.

## 10. Acceptance gates and output

Deliver:

```
ProofGraphs/Boundary/*.lean
fixtures/BoundaryRegression.lean
scripts/export_boundary_sidecar.py
scripts/validate_boundary_sidecar.py
scripts/check_boundary_repl.py
schemas/joint_event_schema.json
reports/boundary-integration/BASELINE_REPRODUCTION.md
reports/boundary-integration/CONFIRMED_AND_REFUTED_FINDINGS.md
reports/boundary-integration/IMPLEMENTATION.md
reports/boundary-integration/TEST_RESULTS.json
reports/boundary-integration/LIMITATIONS.md
```

Adapt names to the repository if needed, but document actual entry points. Provide a machine-readable source manifest and a bounded reproduction command. Produce trace examples only from actual runs, with log/event references.

Required completion:

- Lean code built and controlled tests executed, or exact incomplete status;
- old artifact checks preserved;
- tagged codec has no token substitution inside literals;
- frontier identity and capsule versioning verified;
- incomplete boundary coverage cannot authorize factorization or hard merge;
- transaction rollback behavior tested;
- schema, reference-integrity, and actual replay checks pass;
- no new theorem-proving speedup is claimed from this integration alone.

Stop here before graph learning or open-fragment transport. The next prompt is the gated closed-fragment reuse experiment. A small additive PR with reproducible semantic guarantees is the desired result.
