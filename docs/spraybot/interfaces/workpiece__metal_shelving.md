# `workpiece:metal_shelving` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：层板上下主面、前沿以及立柱外侧；宽板逐行，立柱纵向分笔。
- 机器定位与处理：重叠立柱造成的整行遮挡单列为 fully_occluded_rows，不能把可见但未规划的行混入其中。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 176–234，小于 50 mm 的笔画合计 0 条，完全遮挡行 80 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:metal_shelving`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：细立柱和层板边缘笔画过密。 审查记录见 [`workpiece__metal_shelving.json`](../../../reviews/trajectories/workpiece__metal_shelving.json)（`b1534ea7`）。
- 根因：平面栅格没有按面宽收敛，4 mm 腿翼不适合独立喷涂。
- 修复：窄面居中单行并在可行时连成 S 形；排除极薄腿翼的独立笔画。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 64–78，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:metal_shelving`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。
