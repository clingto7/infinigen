# `workpiece:ladder_back_chair` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：扫掠座面上侧、板状靠背前后主面、横档可见面、腿与横撑外侧；面扫描与长轴笔画组合。
- 机器定位与处理：窄横档的喷涂范围与座底保持分开。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 27–30，小于 50 mm 的笔画合计 0 条，完全遮挡行 58 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:ladder_back_chair`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：腿、横撑与靠背路径需复查外部接近和窄面覆盖。 审查记录见 [`workpiece__ladder_back_chair.json`](../../../reviews/trajectories/workpiece__ladder_back_chair.json)（`b1534ea7`）。
- 根因：杆件中心线及靠背取样容易产生偏向内部或碎段。
- 修复：腿沿外侧面中心走笔，横撑向外接近；靠背曲面和窄边按同面可喷性平滑。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 28–30，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 29 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:ladder_back_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
