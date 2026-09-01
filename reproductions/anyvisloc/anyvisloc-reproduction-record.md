# AnyVisLoc --- Reproduction Record

> Paper: **Exploring the Best Way for UAV Visual Localization under
> Low-altitude Multi-view Observation Condition: a Benchmark**\
> Purpose of this file: **my reproduction work only**. It intentionally
> avoids repeating a full paper-reading summary.

## 1. Reproduction Goal

The goal was not to blindly run every scene and every method in the
repository. The reproduction progressed in stages:

``` text
run the official code successfully
        ↓
understand the role of each script
        ↓
separate retrieval / matching / localization modules
        ↓
run controlled experiments
        ↓
compare major variables
        ↓
analyze failure modes
        ↓
identify front-end research questions
```

The main controlled scene was **Scene_16**, containing **295 query
images**.

This choice was made after early testing showed that larger scenes such
as Scene_01 (1846 queries) were expensive for repeated controlled
experiments.

------------------------------------------------------------------------

## 2. Computing Environment

Main environment:

``` text
Platform: NSCC
GPU: A100 compute node
Conda environment: anyvisloc_demo
Dataset root:
/home/users/ntu/wenyu003/scratch/datasets/AnyVisLoc
```

The working pattern became:

``` text
login node:
- inspect files
- modify YAML/config
- check results
- run lightweight retrieval-only tasks when appropriate

compute node / A100:
- local matching
- RoMa
- full end-to-end localization experiments
```

The dataset was uploaded, batch-extracted, and verified before formal
experiments.

------------------------------------------------------------------------

## 3. Script Roles Clarified During Reproduction

A major early source of confusion was that the repository contains
scripts that look similar but answer different experimental questions.

### `run_avl_retrieval_only.py`

Purpose:

``` text
Query
  ↓
retrieval
  ↓
Top-K candidates
  ↓
Recall / PDM evaluation
```

This isolates the coarse retrieval stage.

It does **not** represent the complete UAV localization pipeline.

### `run_avl_match_loc.py`

Purpose:

``` text
GT / oracle reference
       ↓
local matching
       ↓
2D-3D construction
       ↓
PnP
       ↓
localization
```

This is effectively an oracle/module test.

Because the correct reference region is supplied, it helps answer:

> if retrieval were not the bottleneck, how well can matching + geometry
> localize the UAV?

### `run_avl.py`

Purpose:

``` text
retrieval
  ↓
candidate selection / re-ranking
  ↓
matching
  ↓
2D-3D
  ↓
PnP
  ↓
final localization
```

This is the true end-to-end pipeline and is the main script for
system-level reproduction.

Understanding these three scripts was one of the most important
reproduction milestones.

------------------------------------------------------------------------

## 4. End-to-End Pipeline I Verified

After reading the code and running the modules, the pipeline was
understood as:

``` text
UAV query
    ↓
CAMP retrieval
    ↓
Top-K reference candidates
    ↓
RoMa or SP_LG_GIM 2D-2D matching
    ↓
reference pixel XY
    +
DSM elevation Z
    ↓
2D-3D correspondences
    ↓
PnP / P3P
    ↓
estimated UAV position
    ↓
localization error
```

The DSM is therefore not a matcher. It supplies elevation information so
matched reference pixels can become 3D reference points for pose
estimation.

------------------------------------------------------------------------

## 5. Core Experiment Set

The reproduction eventually covered the important controlled variables
rather than mechanically enumerating the entire benchmark.

Completed experiment categories:

1.  CAMP retrieval-only.
2.  GT-reference → RoMa → P3P oracle/module test.
3.  CAMP → RoMa → P3P full pipeline.
4.  CAMP + RoMa vs CAMP + SP_LG_GIM.
5.  Top1 vs Top5 / Top-N re-ranking behavior.
6.  Aerial vs Satellite reference.
7.  `yp` vs `p` pose-prior sanity check.

This moved the work from "repository execution" to a small **paper-level
reproduction study**.

------------------------------------------------------------------------

## 6. CAMP Retrieval-only Result

Setting:

``` text
Scene: Scene_16
Queries: 295
Reference: aerial
Pose prior: yp
Retrieval: CAMP
K: 1, 3, 5
```

Results:

  Metric       Result
  ---------- --------
  Recall@1     68.47%
  Recall@3     92.20%
  Recall@5     95.25%
  PDM@1        0.9624
  PDM@3        0.9446
  PDM@5        0.9166

The important observation was the large jump from Top1 to Top3/Top5.

This means a substantial fraction of queries for which the first
retrieved reference is not sufficient still have a useful reference
among the next few candidates.

That directly motivates candidate re-ranking / geometric verification
after retrieval.

------------------------------------------------------------------------

## 7. GT-reference + RoMa + P3P Module Test

To isolate matching/localization from retrieval, I ran the
oracle/GT-reference module.

Result on Scene_16:

``` text
Mean localization error   ≈ 0.410 m
Median localization error ≈ 0.319 m
Success @ 1 m             ≈ 94.92%
Success @ 3 m             = 100%
Success @ 5 m             = 100%
```

Interpretation:

> when the correct reference is already known, RoMa + DSM + P3P can
> localize very accurately on this scene.

This was important because it showed that the complete system's large
errors cannot simply be blamed on PnP. Retrieval/candidate quality and
cross-view matching are critical upstream factors.

------------------------------------------------------------------------

## 8. Full Aerial Baseline

A main full-pipeline run used:

``` text
Scene_16
Reference: aerial
Retrieval: CAMP
Matcher: RoMa
Pose prior: yp
PnP: P3P
Strategy: Top-N / Top5-style re-ranking
```

A retained result was:

``` text
295 / 295 localization attempts successful
Mean error   ≈ 0.4738 m
Median error ≈ 0.3146 m
SR@1m        ≈ 0.8983
SR@3m        ≈ 0.9966
```

This established the main working baseline for later comparisons.

The sub-meter median also confirmed that the pipeline was not merely
"running without crashing"; it was producing meaningful localization on
Scene_16.

------------------------------------------------------------------------

## 9. RoMa vs SP_LG_GIM

The matcher comparison was designed to represent a dense/strong matching
approach versus a sparse-style alternative available in the repository.

Main observed trend:

> **RoMa was substantially more stable for precise cross-view
> localization.**

The difference was especially visible in:

-   1 m / 3 m localization accuracy,
-   PnP stability,
-   catastrophic matching failures.

SP_LG_GIM produced more cases in which the correspondence set was not
reliable enough for stable PnP.

This result helped separate two concepts that initially seemed similar:

``` text
many matches ≠ geometrically useful matches
```

For localization, correspondence quality and spatial/geometric
consistency matter more than simply producing a large match count.

------------------------------------------------------------------------

## 10. Top1 vs Top5 / Re-ranking

One of the most useful reproduction findings was understanding what Top5
re-ranking actually does.

It is tempting to think:

``` text
Top5 = every sample becomes slightly more accurate
```

but the experiments suggested a different interpretation.

The major benefit is:

> **Top5 can rescue some catastrophic Top1 retrieval failures.**

Pipeline intuition:

``` text
Top1:
query → first retrieval → matcher → PnP

Top5:
query → several retrieval candidates
             ↓
        matching / geometric evidence
             ↓
       choose a better candidate
             ↓
             PnP
```

Therefore Top-N is not just "retrieval with a larger K." The downstream
matching/geometric evidence becomes a second decision mechanism.

This was one of the clearest signs that retrieval and matching should
not be treated as completely isolated stages.

------------------------------------------------------------------------

## 11. Aerial vs Satellite Reference Experiment

To study the effect of reference modality, the rest of the pipeline was
kept similar while changing the reference source.

Satellite run:

``` text
Scene_16
Reference: satellite
Retrieval: CAMP
Matcher: RoMa
Pose prior: yp
```

Result:

``` text
295 / 295 processed
Mean error   ≈ 94.683 m
Median error ≈ 7.425 m
SR@1m        ≈ 0.0542
SR@3m        ≈ 0.2068
SR@5m        ≈ 0.3288
```

This is dramatically worse than the aerial-reference baseline.

The experiment showed that "PnP succeeded" does not necessarily mean the
estimated location is correct. A geometrically solvable set of
correspondences can still correspond to the wrong physical structure.

Likely system-level difficulties include:

-   stronger modality/domain gap,
-   temporal change,
-   resolution differences,
-   viewpoint differences,
-   georeferencing limitations,
-   DSM/reference quality.

For my research direction, this experiment is strong evidence that
reference-domain robustness is a front-end problem worth studying.

------------------------------------------------------------------------

## 12. Pose-prior Dependence: `yp` vs `p`

A further sanity check removed the yaw component of the prior.

Setting:

``` text
Scene_16
Reference: aerial
Retrieval: CAMP
Matcher: RoMa
Prior: p
```

Result:

``` text
295 / 295 processed
Mean error   ≈ 114.194 m
Median error ≈ 2.141 m
SR@1m        ≈ 0.4271
SR@3m        ≈ 0.5186
```

Compared with the `yp` setting, localization degraded sharply.

This was important because it showed:

> the current visual front-end is not fully invariant to large
> orientation/viewpoint changes.

The result should be described as a **prior-dependence sanity check**,
not as a strict reproduction of the paper's entire prior-noise curve.

------------------------------------------------------------------------

## 13. What the Controlled Experiments Tell Me

The experiments isolate several different failure sources.

### Retrieval bottleneck

Recall@1 is much lower than Recall@5.

Therefore:

``` text
correct/useful area may exist in candidate set
but not at rank 1
```

### Matching bottleneck

GT-reference + RoMa is extremely accurate, while weaker matching can
produce unstable PnP.

Therefore:

``` text
candidate is correct
does not guarantee
correspondences are good
```

### Reference-domain bottleneck

Satellite reference is dramatically worse than aerial.

Therefore:

``` text
same localization framework
+
different reference modality
=
very different difficulty
```

### Prior-dependence bottleneck

Removing yaw information produces a large degradation.

Therefore:

``` text
current visual representation/matching
still benefits strongly from orientation alignment
```

------------------------------------------------------------------------

## 14. Important Failure Types Identified

The reproduction produced a useful failure taxonomy for future analysis.

### Type A --- Retrieval failure

``` text
Top1 reference wrong
but useful candidate appears in Top-K
```

Potential research relevance: retrieval representation / re-ranking.

### Type B --- Matching failure

``` text
reference reasonable
but correspondences unreliable
→ PnP failure or bad pose
```

Potential research relevance: robust cross-view matching.

### Type C --- Satellite-domain failure

``` text
matching/PnP may technically succeed
but localization error remains very large
```

Potential research relevance: domain/viewpoint/temporal robustness.

### Type D --- Prior-dependence failure

``` text
weaker orientation prior
→ large localization degradation
```

Potential research relevance: rotation/viewpoint-stable representation
and region selection.

------------------------------------------------------------------------

## 15. Result Directory Structure Learned

Typical result structure:

``` text
Result/AnyVisLoc/
├── <timestamp>_1scenes/
│   └── aerial/
│       └── aerial-CAMP-Roma-yp/
│           └── scene_success_stats/
│               └── Scene_16/
│                   └── summary.json
```

Retained experiment batches included runs corresponding to:

``` text
aerial + CAMP + RoMa + Top5
aerial + CAMP + SP_LG_GIM + Top5
aerial + CAMP + RoMa/SP_LG_GIM + Top1
satellite + CAMP + RoMa
aerial + CAMP + RoMa + p
```

Useful inspection commands:

``` bash
ls -lt Result/AnyVisLoc | head -10
```

``` bash
find Result/AnyVisLoc -path "*Scene_16/summary.json" -print
```

``` bash
python -m json.tool <path-to-summary.json>
```

These commands became the standard way to move from "terminal logs" to
paper-style metric inspection.

------------------------------------------------------------------------

## 16. Example Full-pipeline Command Pattern

A representative matching/localization configuration used parameters
such as:

``` bash
python run_avl_match_loc.py \
  --dataset_root /home/users/ntu/wenyu003/scratch/datasets/AnyVisLoc \
  --yaml config_selectable_matchers.yaml \
  --save_dir ./Result/AnyVisLoc_match_loc \
  --reference_mode aerial \
  --matching_methods SP_LG_GIM \
  --pose_priori yp \
  --PnP_method P3P \
  --match_keypoints 3000 \
  --min_matches 5 \
  --device cuda
```

The exact script must be interpreted according to its role:
`run_avl_match_loc.py` is the GT-reference/module test, while the
end-to-end experiment uses `run_avl.py`.

------------------------------------------------------------------------

## 17. What Counts as "Reproduced"

I should not claim that every paper table was exactly reproduced.

The accurate description is:

> **core paper-level reproduction completed on Scene_16, with major
> system trends reproduced through controlled experiments.**

Why the qualification matters:

-   my main controlled subset is Scene_16,
-   the paper's main tables may use a different evaluation subset/full
    benchmark,
-   therefore absolute numbers should not be compared as if the sample
    sets were identical.

The reproduction is valuable because it verifies the major trends and
failure modes, not because one Scene_16 number happens to be higher or
lower than a paper-table number.

------------------------------------------------------------------------

## 18. Research Conclusions Derived From the Reproduction

The reproduction suggests that the most promising front-end questions
are not in PnP itself.

The strongest evidence points toward:

1.  **viewpoint-stable retrieval/representation**, because Top1
    retrieval and yaw dependence remain weak points;
2.  **retrieval-to-matching information reuse**, because Top-K matching
    can rescue retrieval errors;
3.  **coarse-to-fine matching**, because robust dense matching is
    valuable but computationally expensive;
4.  **stable-region / sparse-guided selective dense matching**, where
    coarse correspondences or token reliability determine where dense
    refinement should be spent;
5.  **reference-domain robustness**, especially for satellite
    references.

A possible research chain under exploration is:

``` text
shared DINO/ViT-style features
        ↓
retrieval / candidate selection
        ↓
reuse patch/token features
        ↓
coarse or sparse geometry anchors
        ↓
ROI / reliable-token selection
        ↓
selective dense refinement
        ↓
high-quality correspondences
        ↓
PnP
```

The intended innovation remains in the **front-end**: representation,
feature reuse, candidate/region selection, and correspondence
generation. PnP and UAV post-processing are not the main innovation
target.

------------------------------------------------------------------------

## 19. Current Reproduction Status

``` text
Environment setup                         DONE
Dataset preparation                       DONE
Script-role understanding                 DONE
CAMP retrieval-only                       DONE
GT-reference + RoMa + P3P                 DONE
CAMP + RoMa full pipeline                 DONE
RoMa vs SP_LG_GIM                         DONE
Top1 vs Top5 behavior                     DONE
Aerial vs Satellite                       DONE
yp vs p prior sanity check                DONE
Core failure analysis                     DONE
Satellite correspondence diagnostics      DONE
Solver correspondence provenance          DONE
Satellite consistency method direction    NO-GO / FROZEN
Mechanical all-scene enumeration          NOT necessary at this stage
```

This research line is now checkpointed. The recovered evidence does not
support turning cross-reference Agreement, match count, simple coverage,
or solver-subset filtering into the next front-end proposed method. The
active satellite correspondence-consistency direction is therefore
**NO-GO / frozen** rather than moving directly into method development.

UAV-AVL remains valuable as an external validation / secondary benchmark
for a future front-end method selected from an independently supported
research question.

------------------------------------------------------------------------

## 20. Reproduction Takeaway

The most important outcome of this reproduction is not a single accuracy
number.

It is the experimentally supported understanding that:

``` text
retrieval quality
      +
cross-view correspondence quality
      +
reference modality
      +
pose/viewpoint robustness
```

jointly determine localization performance.

On Scene_16, RoMa with aerial references and useful pose priors can
achieve very accurate localization, while satellite references and
weaker orientation priors expose large system-level weaknesses. The
later raw correspondence and solver-provenance audits show that these
weaknesses cannot all be reduced to one clean front-end subset mechanism.
The reproduction is complete, the current method hypothesis is frozen,
and the benchmark is retained for future controlled validation.
