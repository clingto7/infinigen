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

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：底层板下表面无须喷涂；四根支架的长笔画被层板接头切碎。 人工审查提交 `8c28cdc8`，详见 [`workpiece__metal_shelving.json`](../../../reviews/trajectories/workpiece__metal_shelving.json)。
- 根因：规划未排除底面，并以单一支架面限制接头首命中。
- 修复：排除最低板底面；支架行在接头处贴合外侧实体并标注允许命中层板，每根支架保留两个长方向。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 31–37，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:metal_shelving`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。


## 2026-11-21：第四轮轨迹审查通过

- 用户确认本轮轨迹候选通过；正式记录见 [`workpiece__metal_shelving.json`](../../../reviews/trajectories/workpiece__metal_shelving.json)。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:metal_shelving`，规划源码提交 `8bb4440a`，全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。本结论绑定该模型、seed 和轨迹版本；实体机器人可达性与涂层质量尚未验证。
