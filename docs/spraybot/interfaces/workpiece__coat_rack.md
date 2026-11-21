# `workpiece:coat_rack` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：中心立柱外侧、三根斜脚、四个挂钩水平段和短竖端；圆杆沿生成轴线走笔。
- 机器定位与处理：初版长度过滤漏掉挂钩；短构件按结构保留后，每个挂钩都有独立轨迹。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 19–27，小于 50 mm 的笔画合计 40 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:coat_rack`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：用户初看未发现明显问题，作为本轮对照。 审查记录见 [`workpiece__coat_rack.json`](../../../reviews/trajectories/workpiece__coat_rack.json)（`b1534ea7`）。
- 根因：本轮没有确认新的结构性缺陷。
- 修复：保留原轨迹笔画，重建配对证据并参加整批机器审计。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 19–27，小于 50 mm 的笔画合计 40 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:coat_rack`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
