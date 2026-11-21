# `workpiece:bar_chair` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：座面上侧、靠背前后主面、腿和横撑的可见外侧；座背按相连扫掠面扫描，杆件沿长轴。
- 机器定位与处理：初版扫掠采样有急转，整笔平滑后导出检查通过。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 21–31，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:bar_chair`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：部分路径扭曲，横撑喷枪位置偏向包络内部。 审查记录见 [`workpiece__bar_chair.json`](../../../reviews/trajectories/workpiece__bar_chair.json)（`b1534ea7`）。
- 根因：曲面离散点跳变，横撑沿上方接近使喷头进入家具内部。
- 修复：曲面整笔平滑，横撑从外侧接近；只在射线、运动和转角均合格时合并 S 形。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 25–41，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:bar_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
