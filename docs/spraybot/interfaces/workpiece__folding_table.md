# `workpiece:folding_table` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：桌面上侧及前沿、圆杆折叠腿可见侧；桌面按幅宽逐行，圆杆沿轴线。
- 机器定位与处理：桌底及铰链短圆面未宣称完整喷涂。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 19–29，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:folding_table`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：窄面双行、桌板边及可合并行需复查。 审查记录见 [`workpiece__folding_table.json`](../../../reviews/trajectories/workpiece__folding_table.json)（`b1534ea7`）。
- 根因：平面栅格把窄板分成相邻密集行。
- 修复：窄面单行、外露边补齐；同面安全时连成 S 形。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 11–13，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:folding_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第四轮人工审查与轨迹修复

- 症状及证据：叉形板状支架与折叠椅一样缺少两侧面覆盖。 人工审查提交 `c07283ec`，详见 [`workpiece__folding_table.json`](../../../reviews/trajectories/workpiece__folding_table.json)。
- 根因：原规则只保留朝外主面；圆杆型结构没有板状侧面。
- 修复：对板状斜支撑增加两侧斜向笔画，圆杆型 seed 保持沿杆规划。 实现提交 `8bb4440a`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 11–29，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:folding_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
- 仅板状叉形结构补侧面轨迹；圆杆结构的 seed 保持原沿杆路径。交叉接头处的侧面按遮挡拆笔。


## 2026-11-21：第四轮轨迹审查通过

- 用户确认本轮轨迹候选通过；正式记录见 [`workpiece__folding_table.json`](../../../reviews/trajectories/workpiece__folding_table.json)。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:folding_table`，规划源码提交 `8bb4440a`，全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。本结论绑定该模型、seed 和轨迹版本；实体机器人可达性与涂层质量尚未验证。
