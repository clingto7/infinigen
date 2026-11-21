# `workpiece:hairpin_leg_table` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：桌面上侧和前沿、发夹形圆杆腿的可见外侧；杆件沿各生成直段的轴线。
- 机器定位与处理：桌底及小端面不在本轮范围。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 18–20，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:hairpin_leg_table`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌面窄侧面与细腿路径需复查。 审查记录见 [`workpiece__hairpin_leg_table.json`](../../../reviews/trajectories/workpiece__hairpin_leg_table.json)（`b1534ea7`）。
- 根因：窄面行数过多，细腿需按外露表面而非整体包络取向。
- 修复：窄板单行、补齐外露边，细腿沿可见外侧规划。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 13–13，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:hairpin_leg_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
