# 00 — GeoBridge Research Scope

## 1. Supervisor requirements

The active research phase is defined by the following requirements:

- investigate **text-enhanced multimodal cross-view geo-localization**;
- use **GeoBridge as the baseline**;
- begin with documentation, primary-source verification, and baseline
  understanding rather than method implementation;
- preserve the existing AnyVisLoc and GAGeo research histories;
- use the local Mac workspace for documentation, code inspection, and later
  lightweight verification;
- use the currently available remote compute environment, presently NSCC, for
  later GPU-intensive work without making core research code NSCC-specific.

These are **[Supervisor requirements]**. They do not establish what GeoBridge
implements or whether its reported results are reproducible.

## 2. Objective

Build a defensible research chain:

```text
primary-source verification
-> paper/task understanding
-> official code and protocol audit
-> baseline reproduction
-> per-sample failure analysis
-> bottleneck identification
-> falsifiable text-related hypothesis
-> novelty check
-> minimal controlled method experiment
```

The immediate objective is limited to the first step. No paper mechanism,
metric, dataset, result, or limitation has yet been verified locally.

## 3. In scope

- the exact GeoBridge task and evaluation protocol;
- provenance and semantics of text available during training and inference;
- visual encoder, text encoder, feature level, and multimodal interaction,
  after source verification;
- controlled visual-only and text-enhanced comparisons;
- robustness to missing, noisy, generic, shuffled, or conflicting text;
- cross-view ambiguity, hard negatives, geographic/domain generalization, and
  calibration;
- per-sample attribution of visual, textual, fusion, and data failures;
- compute, data, checkpoint, and protocol reproducibility;
- closest-work and novelty analysis around a measured bottleneck.

## 4. Research questions and hypotheses

The following are explicitly **hypotheses**, not conclusions or descriptions
of GeoBridge.

### H1 — Text may resolve visual ambiguity

When multiple locations or reference images are visually similar, informative
and test-time-available text may improve discrimination beyond a controlled
visual-only baseline.

**Falsifying evidence:** no reliable improvement on pre-registered ambiguous
cases, or gains disappear after controlling for backbone, parameters,
supervision, and leakage.

### H2 — Text benefit may be conditional rather than uniform

Text may help only particular view directions, scene types, geographic
regions, or failure categories.

**Falsifying evidence:** subgroup differences are unstable under matched
controls or are explained by sample count, annotation, or protocol changes.

### H3 — Text quality and provenance may determine utility

Natural, generated, templated, or externally retrieved text may produce
different gains and failure modes.

**Falsifying evidence:** controlled text-source and corruption tests show no
meaningful sensitivity, or the apparent benefit comes from label/location
leakage rather than multimodal reasoning.

### H4 — The active bottleneck may not be multimodal fusion

GeoBridge failures may instead originate in visual representation, retrieval
coverage, data construction, or evaluation assumptions.

**Falsifying evidence:** controlled diagnostics isolate a reproducible fusion
failure while the candidate, visual, and protocol prerequisites remain valid.

No architecture change follows from these hypotheses until the baseline and
failure population are verified.

## 5. Go / No-Go criteria

### Gate A — Enter baseline reproduction planning

**GO only if all are satisfied:**

- an authoritative paper/version is identified;
- the official task, inputs, outputs, datasets, splits, and metrics are clear;
- the official code/release identity and license/access conditions are known;
- required data and checkpoints are identifiable without substituting an
  undocumented protocol.

**NO-GO / PAUSE if any are true:**

- paper identity or official implementation cannot be established;
- essential data, pairing, checkpoint, or evaluation protocol is unavailable;
- reproducing the claimed setting would require inventing missing labels,
  splits, or metrics.

### Gate B — Enter full baseline evaluation

**GO only if all are satisfied:**

- a minimal smoke test preserves the official preprocessing and metric path;
- code revision, environment, command, config, seed, checkpoint identity, and
  output schema are recorded;
- sample identity and counts can be audited;
- outputs can support future per-sample failure analysis.

**NO-GO / REVISE if:** the smoke test silently drops samples, changes the
protocol, cannot load the declared checkpoint, or cannot preserve sufficient
provenance.

### Gate C — Enter a text-enhanced proposed-method experiment

**GO only if all are satisfied:**

- the verified baseline exposes a reproducible, text-relevant bottleneck;
- the hypothesis predicts a measurable change on a defined population;
- a visual-only control and leakage controls are available;
- closest related work has been checked from primary sources;
- success, failure, stop, and confounder criteria are frozen before training.

**NO-GO if:** gains can be explained by extra parameters, stronger pretraining,
location/identity leakage, changed data or metrics, or favorable aggregate
averages without mechanism evidence.

Numeric thresholds must be pre-registered only after the official metrics and
baseline variance are known. They must not be invented during this
documentation phase.

## 6. Scope exclusions at this checkpoint

- reproduction scripts, result directories, training, inference, or model
  implementation;
- downloading datasets, checkpoints, or external repositories;
- editing AnyVisLoc or GAGeo notes, results, code, or decisions;
- assuming GeoBridge shares the task or mechanisms of previous baselines;
- proposing a fusion block before paper/code verification and failure analysis;
- using text that leaks ground-truth location or test identity;
- changing evaluation definitions to obtain a favorable result;
- making PnP, pose post-processing, or server-specific engineering the main
  contribution without bottleneck evidence;
- broad experiment grids before a single decision-relevant question is fixed.

## 7. Evidence protocol

Every future claim must distinguish:

1. supervisor-defined direction;
2. primary-paper statement;
3. official-code behavior;
4. preserved result-file evidence;
5. locally reproduced evidence;
6. interpretation;
7. hypothesis or uncertainty.

The weakest available evidence level governs the claim. Missing provenance is
reported as missing evidence, not filled by analogy with AnyVisLoc, GAGeo, or
another multimodal method.

## 8. Immediate next decision

Do not create reproduction assets yet. First obtain and verify the GeoBridge
primary paper identity and freeze the source version to be read.
