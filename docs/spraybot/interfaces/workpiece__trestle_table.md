# `workpiece:trestle_table` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：桌面上侧、支架和横撑外侧；小支架面与长梁分区，接头拆笔。
- 机器定位与处理：上部支架存在不足一喷幅的短可见段；保留至少 30 mm 的有效笔画，同一面其他笔画已覆盖的缺行单独记录。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 40–56，小于 50 mm 的笔画合计 4 条，完全遮挡行 40 行，同面其他笔画已覆盖的缺行 1 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:trestle_table`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌板边和支架短密集行需复查。 审查记录见 [`workpiece__trestle_table.json`](../../../reviews/trajectories/workpiece__trestle_table.json)（`b1534ea7`）。
- 根因：通用行数与内部接缝选择造成重复和碎段。
- 修复：窄面单行、外露边补齐，安全的邻行合并，内部接缝不喷。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 16–28，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 20 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:trestle_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
