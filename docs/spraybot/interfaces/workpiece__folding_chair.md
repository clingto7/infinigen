# `workpiece:folding_chair` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：座板上侧及前沿、靠背前后主面、折叠腿的外侧；按独立板件和铰接部位分笔。
- 机器定位与处理：铰接处不跨构件连接喷涂笔画。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 56–56，小于 50 mm 的笔画合计 0 条，完全遮挡行 40 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:folding_chair`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：窄面双行、外露板边及碎段需复查。 审查记录见 [`workpiece__folding_chair.json`](../../../reviews/trajectories/workpiece__folding_chair.json)（`b1534ea7`）。
- 根因：通用平面行间距和边缘选择不足以表达窄构件。
- 修复：窄面单行、板件外露边补齐，安全的邻行连成 S 形。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 29–29，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 40 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:folding_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：下部椅腿部分喷枪路径进入整件外包络。 人工审查提交 `8c28cdc8`，详见 [`workpiece__folding_chair.json`](../../../reviews/trajectories/workpiece__folding_chair.json)。
- 根因：腿面仅按局部面法向筛选。
- 修复：对腿部候选增加整件凸包外侧筛选。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 21–21，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:folding_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
