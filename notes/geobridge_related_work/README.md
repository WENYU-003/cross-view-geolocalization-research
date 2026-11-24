# GeoBridge Research Line

This directory records the evidence chain for the new GeoBridge baseline and
the broader text-enhanced multimodal cross-view geo-localization direction.
The paper-reading skeleton is in
[`papers/geobridge.md`](../../papers/geobridge.md). No reproduction directory,
script, result, dataset, checkpoint, or method implementation has been created
for GeoBridge at this stage.

## Current research objective

Establish what GeoBridge actually studies, how text enters its cross-view
pipeline, which claims are supported by the primary paper and official code,
and whether it provides a reproducible baseline for diagnosing the value and
failure modes of textual information in cross-view geo-localization.

The objective is evidence recovery and baseline understanding before method
design. It is not to assume that text is beneficial or to retrofit a proposed
method onto an unverified baseline.

## Relationship to previous work

- **AnyVisLoc / UAV-AVL** remains a preserved, frozen prior research line with
  its own task, evidence, and NO-GO decision boundaries.
- **GAGeo / CMA-Loc** remains a separate prior research line with its own
  prompt-conditioned object-localization setting and provenance limits.
- Their analysis practices may inform GeoBridge's evidence protocol, but their
  results, failure mechanisms, task definitions, and conclusions do not
  transfer automatically.
- Existing AnyVisLoc and GAGeo files must not be rewritten to make them appear
  part of the GeoBridge baseline.

## Present research stage

**Phase 0 — documentation and primary-source recovery: IN PROGRESS.**

**Research progress — Limitation 1: Cross-View Semantic Observability.**
Status: **NO-GO for direct method development**, because GeoBridge++ has
substantial problem and method overlap through modality-aware and shared fact
supervision. The evidence and causal boundary are archived in
[`01_limitation_analysis.md`](01_limitation_analysis.md). Next stage:
**Cross-Paper Shared Assumption Analysis**.

Current facts are limited to the supervisor-defined research direction and
baseline choice. The local repository does not yet contain a verified paper
PDF, official code snapshot, immutable config, checkpoint identity, dataset
protocol, or GeoBridge result artifact.

Consequently:

- paper identity is provisional until checked against a primary source;
- method and experimental sections remain placeholders;
- no baseline reproduction claim exists;
- no research bottleneck or proposed method has been selected.

## Planned milestones

1. **Primary-source verification** — verify title, authors, venue/version,
   paper URL, project page, and official repository.
2. **Paper understanding** — record the exact task, modalities, text source,
   data flow, supervision, inference path, datasets, metrics, and claims.
3. **Paper-code-protocol mapping** — map each claimed component and result to
   an official file, config, checkpoint, and evaluation path.
4. **Reproduction readiness audit** — confirm licensing/access, compute,
   dataset versions, checkpoint identity, storage, and NSCC compatibility.
5. **Minimal baseline reproduction** — begin with a smoke test, then reproduce
   the smallest decision-relevant baseline under the original protocol.
6. **Per-sample failure analysis** — preserve outputs needed to separate
   visual, textual, fusion, data, and evaluation effects.
7. **Hypothesis and novelty gate** — formulate a falsifiable text-related
   hypothesis only after a measured bottleneck and closest-work check.
8. **Minimal method experiment** — implement only the smallest controlled
   change capable of supporting or falsifying that hypothesis.

Milestones 3–8 are plans, not completed work.

## File index

- [`00_research_scope.md`](00_research_scope.md): supervisor requirements,
  hypotheses, Go/No-Go gates, and exclusions.
- [`../../papers/geobridge.md`](../../papers/geobridge.md): paper-reading and
  source-verification skeleton.

## Evidence and reproducibility standards

Use these labels consistently:

- **[Supervisor requirement]**: direction or constraint explicitly supplied
  for this research phase; not a paper claim.
- **[Paper]**: directly supported by an identified primary-paper version.
- **[Official code]**: directly supported by a named official repository and
  immutable revision.
- **[Result-file-confirmed]**: recomputed or directly inspected from preserved
  outputs with known schema and sample count.
- **[Locally reproduced]**: generated from a recorded command, config,
  checkpoint identity, environment, and code revision.
- **[Interpretation]**: evidence-bounded explanation that is not directly
  measured.
- **[Hypothesis]**: falsifiable statement awaiting controlled evidence.
- **[Uncertainty]**: missing, conflicting, or version-dependent information.

For every future claim, record:

```text
Claim
-> evidence label
-> primary source / code revision / artifact
-> dataset, split, direction, and sample count
-> command and immutable config when experimental
-> alternative explanations and missing measurements
-> decision enabled
```

Do not describe paper-reported or repository-reported results as locally
reproduced. Do not use text-derived location leakage as evidence of improved
cross-view reasoning. Preserve per-sample outputs whenever failure analysis is
an objective.
