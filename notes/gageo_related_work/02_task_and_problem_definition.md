# 02 — Task and Problem Definition

## Formal interface

```text
(query image, query-side prompt, paired reference image)
                         ↓
             reference-domain localization
```

- **Query image**：Ground 或 Drone 观察图。
- **Prompt**：定义在 query 像素坐标系中，指定要找的 object instance。
- **Reference image**：主 benchmark 中为 georeferenced Satellite crop。
- **Localization output**：reference 像素坐标系中的 target bbox / mask；另有 query-camera position / rotation。

模型不是在全球图库中检索 reference。CMA-Loc evaluator 已给定成对 query/reference，因此它是 paired、object-level localization，而不是 global image retrieval。

## View definitions

| View | Typical content | Main benchmark role |
| --- | --- | --- |
| Ground | street-level monocular view；facade、occlusion、强透视 | query |
| Drone | oblique aerial view；roof + facade + neighborhood | query |
| Satellite | nadir/top-down roof、footprint 与布局；带地理参考 | reference |

主 evaluation JSON 同时包含 Ground→Satellite 和 Drone→Satellite。Ground→Drone 只出现在论文的 zero-shot triplet evaluation 中，不属于六个 CMA-Loc 主结果 JSON。

## Prompt modalities

| Prompt | Query-side information | Model encoding |
| --- | --- | --- |
| Point | 一个目标内部点 | sparse prompt token；发布实现还添加 SAM-style padding token |
| BBox | query target 的 `(x, y, w, h)` | 两个角点 sparse tokens |
| Mask | query target 的 binary region | dense 37×37 prompt embedding |

Point、BBox、Mask 是三种输入条件，不是三种 output task，也不是三套 checkpoint。

## Output tasks

一次 point/bbox/mask evaluation 均产生：

1. **Detection**：reference target bbox；
2. **Segmentation**：reference target model mask；
3. **Position**：query camera 在 reference image 中的 normalized 2D position；
4. **Rotation**：query camera 相对 reference coordinate frame 的 3×3 rotation matrix，另导出 yaw/pitch/roll。

所以：

```text
point prompt 也产生 detection + segmentation metrics
mask prompt 也产生 detection + segmentation metrics
```

“point 属于 detection”“mask 属于 segmentation”都是错误分类。Prompt 描述输入；detection/segmentation 描述输出与评估。

## Coordinate systems

- query point/bbox/mask 在 query 像素坐标系；
- predicted bbox/mask 在 resized reference（默认 518×518）坐标系；
- bbox head 内部输出 normalized `(cx, cy, w, h)`，evaluator 转为 absolute `xyxy` 后计算 IoU；
- predicted position 是 `[0,1]` normalized reference coordinate，`pos_err_px` 再乘 `img_size`；
- rotation error 比较两个 SO(3) rotation matrices。

这些坐标不能因为都写成 `(x,y)` 就互换。
