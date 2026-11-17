# CVPR 2027 Research Agent Guidelines

## 1. Project Goal

This repository supports a research pipeline targeting **CVPR 2027**.

The primary research direction is:

- Cross-View Geo-Localization
- UAV Visual Localization

The current primary research line is **text-enhanced multimodal cross-view geo-localization**, using GeoBridge as the baseline. The intended contribution remains in the visual/multimodal front end: representation, retrieval, cross-view alignment, textual disambiguation, and geometry-aware features. Research questions must come before implementation. Do not change a model merely to make the work appear novel.

## 2. Research Scope

Primary topics include:

- image retrieval
- feature extraction
- feature matching
- cross-view feature alignment
- text-enhanced cross-view representation
- vision-language alignment and textual disambiguation
- Vision Transformer (ViT) and Transformer architectures
- CLIP and multimodal representation
- DINOv2 and foundation-model visual features
- SAM2 and prompt-driven segmentation
- RoMa dense matching
- SuperPoint and LightGlue
- geometry-aware representation and feature learning

Traditional PnP, pose solvers, and UAV post-processing remain necessary evaluation components, but they are **not the preferred location for the main research contribution** unless later evidence clearly changes the research question. Prefer innovations in the visual front end rather than replacing a conventional solver without a demonstrated bottleneck.

## 3. Current Research Stage

The active GeoBridge research line is at **primary-source verification and baseline documentation**. Baseline reproduction, failure analysis, and method selection have not started. A final proposed method has **not** been formally selected.

### GeoBridge

GeoBridge is the designated baseline for the text-enhanced multimodal cross-view geo-localization research phase. Until the primary paper, official implementation, dataset protocol, checkpoint identity, and evaluation definitions are inspected, its task, mechanisms, and reported results must remain explicitly unverified.

Do not transfer AnyVisLoc or GAGeo task definitions, mechanisms, results, or failure explanations into GeoBridge without independent evidence.

### AnyVisLoc / UAV-AVL

Completed work recorded in the research summary includes experiments on Scene_16 covering:

- CAMP retrieval-only evaluation
- ground-truth reference to RoMa to P3P evaluation, isolating matching and geometry from retrieval
- the full CAMP to RoMa to P3P pipeline
- aerial versus satellite reference comparison
- yaw/pitch pose-prior ablation

The recorded results indicate that the aerial-reference pipeline with yaw/pitch prior achieves sub-meter median localization error, while satellite references and removal of yaw alignment cause substantial degradation. Treat exact metrics as **document-recorded evidence** until the corresponding commands, config snapshots, logs, per-sample outputs, and summary files have been restored and verified in the repository. Do not claim that locally missing result artifacts have been independently reproduced.

### GAGeo / CMA-Loc

Completed analysis recorded in the research summary covers the CMA-Loc `unseen_test` split with Point Prompt and 4,197 samples. Severe failure was defined as both `det_iou == 0` and `mask_iou == 0`. The recorded analysis found 196 severe failures (4.67%), concentrated in Ground and Small samples; Ground + Small was the strongest observed failure cluster.

The current repository contains grouped evaluation support, but a reproducible per-sample failure export, raw severe-failure list, qualitative visualization set, and complete failure-cause taxonomy are not yet established in the repository. These are current work, not completed conclusions.

### Evidence Boundary

When describing project status, distinguish among:

1. code-confirmed behavior;
2. result-file-confirmed experiments;
3. results recorded only in research notes or summaries;
4. hypotheses or interpretations that remain unverified.

Never silently promote an item from a weaker evidence level to a stronger one.

## 4. Current Verified Results

The following are the currently confirmed **research checkpoints**, not necessarily locally available model-weight checkpoint files. Their evidence level must remain explicit: the figures below are recorded in the uploaded research summary and are consistent with the inspected pipeline/evaluation code, but the corresponding raw local result artifacts are not currently present in this repository. Re-verify them from commands, config snapshots, logs, and per-sample outputs before using them as result-file-confirmed paper evidence.

### AnyVisLoc Scene_16

| Experiment | Recorded result | Current evidence status |
| --- | --- | --- |
| CAMP retrieval-only | R@1 68.47%; R@3 92.20%; R@5 95.25% | Summary-recorded; pipeline code inspected; raw local output missing |
| GT reference → RoMa → P3P | Mean ≈0.410 m; Median ≈0.319 m; SR@1m≈94.92%; SR@3/5m=100% | Summary-recorded; matching/geometry path inspected; raw local output missing |
| Full pipeline: Aerial + CAMP + RoMa + `yp` + P3P | Mean ≈0.474 m; Median ≈0.315 m; SR@1m≈89.83%; SR@3m≈99.66% | Summary-recorded; full pipeline inspected; raw local output missing |
| Reference ablation: Satellite + CAMP + RoMa + `yp` | Mean ≈94.683 m; Median ≈7.425 m; SR@1m≈5.42%; SR@3m≈20.68% | Summary-recorded; raw local output missing |
| Pose-prior ablation: Aerial + CAMP + RoMa + `p` | Mean ≈114.194 m; Median ≈2.141 m; SR@1m≈42.71%; SR@3m≈51.86% | Summary-recorded; raw local output missing |

### GAGeo / CMA-Loc

The currently recorded checkpoint is CMA-Loc `unseen_test` with Point Prompt:

- 4,197 evaluated samples;
- severe failure definition: `det_iou == 0` and `mask_iou == 0`;
- 196 severe failures, or 4.67% overall;
- Ground: 190/2,180 = 8.72%;
- Drone: 6/2,017 = 0.30%;
- Small: 118/1,399 = 8.43%;
- Large: 24/1,399 = 1.72%;
- Ground + Small: 114/727 = 15.68%, the strongest currently recorded failure cluster.

These subgroup counts are summary-recorded and compatible with the repository's grouped evaluation dimensions. The per-sample export and raw severe-failure dataset are still missing, so causal explanations remain hypotheses rather than verified conclusions.

## 5. Research Workflow

Follow this sequence unless there is a documented reason to deviate:

```text
Literature Survey
→ Baseline Reproduction
→ Failure Analysis
→ Bottleneck Identification
→ Research Hypothesis
→ Novelty Check
→ Minimal Validation Experiment
→ Method Implementation
→ Ablation
→ Full Evaluation
→ Paper-level Analysis
```

Do not jump from an interesting idea directly to large-scale implementation. First identify the failure or limitation, express a falsifiable hypothesis, check related work, and design the smallest controlled experiment capable of changing the next research decision.

Research questions should target mechanisms with plausible **cross-model or cross-scene relevance**. A failure isolated to one baseline, scene, split, or implementation may motivate diagnosis, but do not repeatedly design bespoke modules around isolated failures unless evidence supports a broader mechanism and a transferable evaluation plan.

## 6. Experiment Rules

Every experiment must record the following fields:

- **Research question:** What uncertainty or bottleneck does the experiment address?
- **Hypothesis:** What outcome is expected, and why?
- **Baseline:** Which exact method, checkpoint, code revision, and result is the comparison point?
- **Changed variable:** What single factor or clearly defined factor set changes?
- **Dataset / split:** Which dataset, scene, task direction, prompt type, subset, and sample count are used?
- **Command:** The exact executable command, including relevant environment variables.
- **Config:** The config path plus a preserved config snapshot or immutable reference.
- **Metric:** Which primary and diagnostic metrics answer the research question?
- **Result:** Raw and summarized outcomes, including failures and missing samples.
- **Interpretation:** What the evidence supports and what it does not support.
- **Next decision:** Continue, reject, revise, scale up, or request more evidence.

Additional rules:

- Do not run large experiment grids without a clear research question.
- Prefer controlled experiments that change one interpretable variable at a time.
- Start with a smoke test or a small representative subset before expensive evaluation.
- Preserve per-sample outputs when failure analysis is an objective.
- Report mean together with median, success rates, distributions, and failure counts when outliers matter.
- Record sample counts and exclusions; never hide failed or skipped samples.
- Separate retrieval-only, oracle/GT-reference, matching-and-geometry, and full-pipeline conclusions.
- Do not rerun expensive baselines when existing artifacts can be verified and reused.
- A successful run is not automatically a useful experiment; it must answer the stated question.
- Explicitly distinguish text used only as **training supervision** from text provided as an **inference-time input**. Before proposing a text ablation, verify the model's actual training and inference interfaces; do not remove, add, shuffle, corrupt, or substitute inference-time text when that operation is incompatible with the verified model interface.

## 7. Coding Rules

- Do not break, overwrite, or delete the original baseline.
- Implement new research ideas in independent, modular components whenever practical.
- Prefer config-controlled behavior over hard-coded experimental forks.
- Design every method change so that it can be disabled for a clean baseline comparison and ablation.
- Before modifying code, explain:
  - the research purpose;
  - the hypothesis being tested;
  - the files to be changed;
  - why each change is necessary;
  - how the change will be validated.
- After modifying code, run the smallest relevant verification first: import check, unit test, synthetic check, or limited-sample smoke test.
- Scale up only after the minimal verification passes.
- Do not perform large refactors unrelated to the active research question.
- Keep data loading, model definition, evaluation, analysis, and visualization responsibilities separated.
- Preserve backward compatibility with baseline configs when reasonably possible.
- Make output directories, seeds, checkpoints, configs, and run identifiers explicit.
- Do not encode experimental conclusions in code comments before the evidence exists.
- Never change evaluation definitions merely to improve reported performance. If a metric or protocol must change, retain and report the original protocol alongside it.

## 8. Git / GitHub Rules

Git history is part of the scientific record.

- Do not force-push.
- Do not delete or rewrite existing research history.
- Do not push to `main` by default.
- Do not push to `main` without the user's explicit request.
- Do not push anything without the user's explicit instruction.
- Do not create a Pull Request without the user's explicit request.
- Do not merge a Pull Request without the user's explicit request.
- Prefer a dedicated branch for each confirmed research method or substantial experiment track.
- Use branch names that identify the research question or method, not vague labels.
- Commit messages must reflect the research purpose, for example: `Add per-sample CMA-Loc export for Ground-Small failure analysis`.
- Do not commit datasets, large checkpoints, model weights, caches, generated dependency folders, or large temporary outputs.
- Keep secrets, account details, cluster credentials, private keys, and machine-specific environment files out of Git.
- Before committing, inspect `git diff` and confirm that unrelated user changes are preserved.
- Do not combine unrelated research changes in one commit.
- After important code changes, update the relevant experiment or research notes with the hypothesis, command, config, result location, and decision.
- A code commit without corresponding experimental context is incomplete for research-critical changes.

## 9. Compute Environment Rules

- Use the local Mac/Codex environment primarily for code reading, code modification, lightweight analysis, documentation, and smoke tests that fit the available local resources.
- Run large-scale GPU experiments and data-intensive evaluation in the **currently available remote compute environment**.
- NSCC is the main remote compute environment currently in use, but it is not a permanent project dependency. It may later be replaced by another laboratory server, HPC cluster, or cloud GPU environment.
- Do not design the project around NSCC-specific assumptions, commands, directory layouts, schedulers, modules, or storage behavior.
- Do not assume that dataset locations, checkpoint locations, CUDA versions, PyTorch builds, conda/virtual environments, GPU types, storage limits, scheduler policies, or filesystem paths are identical across servers.
- Configure dataset paths, checkpoint paths, output paths, devices, cache locations, worker counts, and other environment-dependent settings through config files, command-line arguments, or environment variables whenever practical.
- Do not hard-code any specific server's absolute paths into reusable research code.
- Keep server-specific launch scripts or environment templates separate from general model, dataset, evaluation, and analysis modules.
- Before a large experiment, confirm the active compute environment's:
  - GPU model, count, memory, and availability;
  - CUDA driver/runtime and PyTorch compatibility;
  - dataset location and expected split/version;
  - checkpoint location and checkpoint identity;
  - available storage and scratch policy;
  - scheduler or job-submission requirements;
  - output, logging, cache, and temporary-file paths.
- Record the active compute environment in the experiment notes so that a run can be interpreted and reproduced later.
- Keep the project compute-environment agnostic so that experiments can migrate between servers without modifying core research logic.

## 10. Research Integrity

- Do not fabricate papers, citations, datasets, methods, experiments, or results.
- Verify bibliographic information from primary sources before adding it to research notes or a paper.
- Do not state that an experiment was reproduced when only a README, summary, or third-party report is available.
- Do not write a hypothesis as a conclusion.
- Do not cherry-pick only favorable samples or metrics.
- Clearly label uncertainty, inference, missing evidence, confounders, and alternative explanations.
- Distinguish correlation from causation, especially in subgroup analysis.
- Keep paper-reported results, repository-reported results, and locally reproduced results separate.
- When exact provenance is missing, say so and prioritize recovering it before building on the result.

## 11. Teaching / Explanation Preference

The user is still developing research and engineering expertise. For complex changes, do not provide only final code. Explain at an appropriate technical level:

- how the original method works;
- where the current bottleneck is believed to occur;
- what the new design is intended to solve;
- how images, prompts, features, tokens, correspondences, and tensors flow through the method;
- relevant tensor shapes and coordinate systems;
- how the pipeline changes before versus after the modification;
- which parameters are frozen, trained, added, or reused;
- what result would support or falsify the hypothesis;
- what limitations and confounders remain.

Use diagrams, compact pseudocode, or before/after data-flow descriptions when they materially improve understanding. Explain unfamiliar terminology rather than assuming it is already known.

## 12. Current Priority

GeoBridge is the active primary research line. Work in the following order unless new evidence or an explicit user instruction changes it:

### GeoBridge A. Primary-source verification

Verify the official paper identity, version, task, inputs, outputs, datasets, splits, metrics, text provenance, project page, and official code repository. Explicitly determine whether each text signal is used as training supervision, provided during inference, or both. Do not infer missing mechanisms or results from the method name.

### GeoBridge B. Paper-code-protocol mapping

Map each paper component and experimental claim to an official code revision, config, checkpoint, data path, and evaluation entry point. Record unavailable or conflicting provenance explicitly.

### GeoBridge C. Reproducible baseline

Begin with the smallest protocol-preserving smoke test. Preserve commands, config snapshots, checkpoint identity, environment information, sample counts, and per-sample outputs before scaling evaluation.

### GeoBridge D. Failure analysis and bottleneck identification

Separate visual, textual, multimodal-fusion, retrieval, data-construction, and evaluation failures. Include visual-only controls and tests for missing, generic, shuffled, noisy, or conflicting text only when those interventions are compatible with the verified training and inference interfaces.

### GeoBridge E. Hypothesis and novelty gate

Select a method change only after a reproducible text-relevant bottleneck, falsifiable hypothesis, leakage controls, closest-work check, and pre-registered Go/No-Go criteria have been established. Prefer hypotheses with plausible cross-model or cross-scene relevance over modules tailored to an isolated GeoBridge failure.

### Deferred previous-line priorities

The AnyVisLoc and GAGeo priorities below remain part of the scientific record but are paused unless explicitly resumed. Do not rewrite their existing results or evidence boundaries.

### A. Reproducible GAGeo per-sample failure dataset

Export stable sample identifiers, task direction, size/shape categories, prompt type, predictions, detection IoU, mask IoU, relevant pose metrics, and artifact paths. Preserve enough information to regenerate all subgroup statistics and severe-failure lists.

### B. Ground + Small failure analysis

Determine whether failures are associated with target size in patch units, prompt quality, target/background ratio, cross-view ambiguity, crop/annotation quality, feature resolution, or loss of target signal across intermediate layers.

### C. AnyVisLoc error attribution

Align per-sample retrieval rank and scores, matching statistics, correspondence coverage, DSM validity, PnP inliers, candidate selection, and final localization error. Keep retrieval, matching, geometry, and pose-prior effects separate.

### D. Failure taxonomy

Create a reproducible taxonomy with explicit labeling criteria and representative visual examples. Avoid vague categories that cannot be consistently assigned.

### E. Literature and related-work expansion

Expand the survey around the verified bottleneck, prioritizing primary papers and official implementations in cross-view localization, small-object representation, prompt-conditioned alignment, multimodal priors, feature reuse, and geometry-aware matching.

### F. Novelty matrix

Compare candidate ideas against the closest methods by research problem, supervision, backbone, feature level, alignment mechanism, geometry use, computational cost, datasets, and evaluation protocol. Mark uncertain comparisons until verified.

### G. First minimal method experiment

Select the smallest method change supported by the failure analysis and novelty check. Define the expected mechanism, controlled baseline, ablations, stop criteria, and falsifying outcome before implementation.

## 13. Default Decision Policy

When choosing what to do next:

1. prefer evidence recovery over rerunning expensive experiments;
2. prefer diagnosis over architecture changes;
3. prefer a falsifiable hypothesis over a broad idea;
4. prefer a minimal controlled test over a full training run;
5. prefer reproducibility and per-sample traceability over a single headline metric;
6. stop and report uncertainty when the available artifacts cannot support a conclusion.

## 14. Repository Structure Rules

- Treat the repository's actual structure as authoritative over any recommended template.
- Do not rename, duplicate, or rebuild existing directories merely to match a template.
- Prefer reusing existing research areas, including:
  - `papers/`
  - `notes/`
  - `reproductions/`
  - `ideas/`
  - `results/`, when it exists in the relevant repository or baseline area
- Before creating a directory, first check whether an existing directory already provides an equivalent function.
- Do not create directories with duplicate semantics, such as:
  - `papers/` and `literature/`
  - `notes/` and `research_notes/`
  - `reproductions/` and `baselines/`
- Do not move existing research history unless the user explicitly requests it.
- When directory naming is inconsistent, document an explicit mapping before considering structural changes; prefer mapping documentation over refactoring.
- Treat any recommended repository structure as a long-term reference, not a mandatory schema.
- Create future directories such as `analysis/`, `experiments/`, `novelty/`, `src/`, and `tests/` incrementally, only when an active research responsibility requires them.
- Reserve `src/` for our future proposed-method code. Do not use it to relocate or duplicate existing reproduction code.
- Create a new directory only when the existing structure cannot clearly carry the new research responsibility.
