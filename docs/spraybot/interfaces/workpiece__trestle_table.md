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

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：底部部分路径位于整件包络内部，难以执行。 人工审查提交 `8c28cdc8`，详见 [`workpiece__trestle_table.json`](../../../reviews/trajectories/workpiece__trestle_table.json)。
- 根因：旧规划只以局部目标面与射线判定，底朝向面也被选入。
- 修复：排除底朝向腿面，并对腿部候选增加整件凸包外侧筛选；保留路径数量变化供人工复核。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 7–9，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:trestle_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
- 凸包外侧筛选使总笔画由上轮的 16–28 降至 7–9；这轮需优先确认腿部喷涂范围，不能以包络诊断为覆盖充分的证据。
