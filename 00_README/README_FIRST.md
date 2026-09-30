# ProofNet Master Handoff — 2026-09-30

This archive collects the current ProofNet research artifacts into one handoff package.

## Recommended reading / execution order

1. `02_JOINT_RESEARCH/proofnet_joint_integration_20260930/paper/Executive_Brief.pdf`
   - Fast overview of how ProofNet-IR, proof-graphs, and the Boundary-Lens work fit together.

2. `02_JOINT_RESEARCH/proofnet_joint_integration_20260930/paper/Joint_Research_Plan.pdf`
   - Current joint research direction and division of technical responsibilities.

3. `02_JOINT_RESEARCH/proofnet_joint_integration_20260930/reports/REPOSITORY_COMPARISON.md`
   - Detailed comparison between the two GitHub repositories and the Boundary-Lens contribution.

4. `03_CURRENT_AUDIT_AND_METHOD_UPDATE/proofnet_v071_audit_update/reports/PROOFNET_V071_AUDIT_AND_METHOD_UPDATE.md`
   - Audit of the current v0.7.1 extractor/dataset and the caveats that should be fixed next.

5. `04_CODEX_PROMPTS/CODEX_JOINT_INTEGRATION_PROMPT.md`
   - Recommended immediate Codex task: integrate the Boundary-Lens audit/semantics work with `proof-graphs`
     rather than continuing a parallel standalone extractor.

6. `04_CODEX_PROMPTS/CODEX_CLOSED_FRAGMENT_REUSE_PROMPT.md`
   - Follow-on experiment after the integration/audit layer is correct: checked proof-fragment reuse.

## Current dataset

`01_CURRENT_DATASET/proofnet_v071_boundary_lens_complete_20260704.zip`

This is the newest uploaded Boundary-Lens dataset/extractor package in this conversation. Keep it frozen as an
input/provenance artifact while doing integration work.

## Current joint research instruction

The present recommended direction is:

- treat `proofnet-ir` as the verified restricted-logic reference;
- treat `proof-graphs` as the shared Lean extraction/search/dataset foundation;
- refine the Boundary-Lens contribution into:
  1. semantic audit and adversarial correctness tests,
  2. typed boundary/event records with explicit evidence/provenance,
  3. checked transport/reuse of completed proof fragments across compatible contexts,
  4. controlled experiments against both whole-state/coupled-goal search and a conventional typed cache.

Do **not** claim that graph hashing alone can merge more states than an exact normalized-state key.
Do **not** duplicate the existing InfoTree/REPL/goal-coupling machinery unless a concrete missing capability is proven.
Do **not** promote source-derived frontier examples to Lean-state-extracted data without running the corresponding Lean project.

## Archive layout

- `01_CURRENT_DATASET/`: frozen newest dataset ZIP.
- `02_JOINT_RESEARCH/`: current paper, executive brief, comparison, and joint research ZIP.
- `03_CURRENT_AUDIT_AND_METHOD_UPDATE/`: v0.7.1 audit, schemas, and next-method update.
- `04_CODEX_PROMPTS/`: canonical Codex prompts for the actual next engineering work.
- `05_PRIOR_METHOD_PACKAGES/`: earlier milestones retained for provenance; they are not the current plan.

## Source repositories reviewed

- https://github.com/fushanbobfan/proofnet-ir
- https://github.com/fushanbobfan/proof-graphs

Pin exact repository commits in any experiment or paper artifact before running new results.
