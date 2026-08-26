# Multi-View Geometry Notes

## Coordinate Systems
The main coordinate systems studied are:
- World coordinate system
- Camera coordinate system
- Image plane
- Pixel coordinate system

## Camera Projection
A 3D world point is transformed into the camera coordinate system using camera extrinsics and then projected into the image using camera intrinsics.

Conceptually:

```text
3D World Point
    ↓  [R | t]
Camera Coordinates
    ↓  K
Image / Pixel Coordinates
```

## Camera Parameters
### Intrinsics
Describe the internal camera projection, such as focal length and principal point.

### Extrinsics
Describe camera pose relative to the world:
- Rotation `R`
- Translation `t`

## Topics Studied
- Perspective projection
- Homogeneous coordinates
- Camera intrinsic/extrinsic matrices
- Homography
- Essential matrix
- Relative pose estimation
- SVD
- PnP
- P3P
- 2D-2D correspondences
- 2D-3D correspondences

## Connection to Localization
A common localization path is:

```text
Image Feature (2D)
        ↕
Known Map Point (3D)
        ↓
PnP / P3P
        ↓
Camera Pose
```

This is directly related to the geometric back-end used in UAV visual localization pipelines.
