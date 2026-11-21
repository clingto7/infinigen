# `workpiece:corner_desk` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：两块桌面上侧和前沿、支腿外侧；每块桌面分别扫描，内角和支腿接头处拆笔。
- 机器定位与处理：桌面底侧不在本轮范围。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 43–51，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:corner_desk`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌板侧面遗漏，腿部喷枪可能进入家具包络内部。 审查记录见 [`workpiece__corner_desk.json`](../../../reviews/trajectories/workpiece__corner_desk.json)（`b1534ea7`）。
- 根因：内部接缝与外缘混淆，腿的候选法向未优先外部方向。
- 修复：选完整外露桌板边并单行覆盖；腿优先从整体凸包外侧接近，记录包络诊断。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 23–24，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:corner_desk`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
