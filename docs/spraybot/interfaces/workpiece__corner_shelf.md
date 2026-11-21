# `workpiece:corner_shelf` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：三角层板上下主面、前沿与角架外侧；板面逐行，框架在层板交接处留 15 mm 间隙拆笔。
- 机器定位与处理：首轮导出检查发现框架路径在层板接缝误命中；按其他构件包围盒避让后，问题 seed 1、4、6、7 的机器复测通过。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 32–52，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:corner_shelf`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：立柱双密集行且被层板切碎。 审查记录见 [`workpiece__corner_shelf.json`](../../../reviews/trajectories/workpiece__corner_shelf.json)（`b1534ea7`）。
- 根因：窄面行数由面积栅格决定，层板交点把连续立柱误分段。
- 修复：立柱改为两个外侧方向的长笔画；在层板交点容许命中相邻实体，并保留逐笔射线与运动校验。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 32–42，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:corner_shelf`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：三角隔板的斜侧边漏喷。 人工审查提交 `8c28cdc8`，详见 [`workpiece__corner_shelf.json`](../../../reviews/trajectories/workpiece__corner_shelf.json)。
- 根因：侧面选择只检查单个水平轴分量，斜边法向未达阈值。
- 修复：按水平法向长度选入斜边，并用同一目标面射线校验。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 35–46，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:corner_shelf`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
