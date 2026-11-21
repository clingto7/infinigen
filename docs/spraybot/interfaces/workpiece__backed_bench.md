# `workpiece:backed_bench` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：座面上侧、靠背前后主面、四腿外侧及座下横撑上侧；相连扫掠曲面合成座背往复行，杆件沿长轴走笔。
- 机器定位与处理：初版座面最近点采样产生急转；沿用 Armchair 对整笔的平滑，保持所有采样点后复测。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 16–34，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:backed_bench`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：部分立腿漏喷，U 型腿整体误判；座背窄侧面缺笔画。seed 2 的 8 根独立立腿仅规划了 4 根。 审查记录见 [`workpiece__backed_bench.json`](../../../reviews/trajectories/workpiece__backed_bench.json)（`b1534ea7`；补充发现 `6ccfc53a`、`a366e2f1`）。
- 根因：腿语义 storage_grid_legs 未映射，U 型件需按两端拆分；边缘偏置采样会把可喷的整笔筛掉。
- 修复：映射腿语义、拆 U 型支撑，立腿沿外露面中心采样；座背窄边加密取样，安全的面内往复行合并。 实现提交 `c98a211d`；backed_bench 腿部补修 `8f2fbe82`、`b19008cd`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 17–59，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:backed_bench`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
