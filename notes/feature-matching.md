# Feature Matching Notes

## Classical Pipeline
```text
Image Pair
    ↓
Feature Detection / Description
    ↓
Descriptor Matching
    ↓
Matching Filtering
    ↓
RANSAC / Geometric Verification
    ↓
Verified Correspondences
```

## Topics Studied
- SIFT
- SURF
- ORB
- BFMatcher
- FLANN
- KNN matching
- Lowe Ratio Test
- RANSAC
- Homography
- Essential Matrix
- Learned sparse matching
- Dense matching

## Key Understanding
Feature matching is not only about finding visually similar points. For localization, the correspondences must also be geometrically consistent.

Classical methods often separate:
1. feature extraction,
2. descriptor matching,
3. outlier filtering,
4. geometric verification.

Modern learned matchers may combine or replace some of these stages, but the geometric objective remains important.

## Connection to Geo-Localization
In a retrieval-to-localization pipeline:

```text
Retrieval → Candidate Image → Local Matching → Geometry → Pose
```

retrieval determines *where to search*, while feature matching determines *which local observations correspond*.
