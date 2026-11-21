# `workpiece:workbench` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：工作台面上侧、下层搁板可见主面和前沿、框架与腿外侧；板面逐行，结构交接处拆笔。
- 机器定位与处理：首轮有支腿路径误命中邻近框架；接头附近留间隙后重验。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 69–72，小于 50 mm 的笔画合计 0 条，完全遮挡行 80 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:workbench`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌板边、支撑与碎段需复查。 审查记录见 [`workpiece__workbench.json`](../../../reviews/trajectories/workpiece__workbench.json)（`b1534ea7`）。
- 根因：窄面多行及连接处的分段策略过细。
- 修复：窄面单行、外露板边补齐；只在同面安全时合并往复行。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 43–45，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 40 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:workbench`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：底板下表面无需喷涂；四腿各两条长轨迹被接缝拆断。 人工审查提交 `8c28cdc8`，详见 [`workpiece__workbench.json`](../../../reviews/trajectories/workpiece__workbench.json)。
- 根因：底面仍被选入，腿部与层板接缝按单独部件阻断。
- 修复：排除底板下表面；接头显式允许邻接目标部件首命中，使四腿各有两条贯通轨迹。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 28–29，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:workbench`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
