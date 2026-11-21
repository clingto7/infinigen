# `workpiece:ladder_shelf` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：五层层板的上下主面和前沿，左右斜架外侧；长板按喷幅逐行，斜架沿面长轴分笔。
- 机器定位与处理：梯架与层板的接头只保留可见连续段。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 48–60，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:ladder_shelf`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：窄板重复平行笔画，部分邻行可连续。 审查记录见 [`workpiece__ladder_shelf.json`](../../../reviews/trajectories/workpiece__ladder_shelf.json)（`b1534ea7`）。
- 根因：通用平面规划把窄面当成需多行覆盖。
- 修复：窄面用居中单行，外露板边补齐；同面且路径安全时连接成 S 形。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 28–42，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:ladder_shelf`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
