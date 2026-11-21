# `workpiece:backless_bench` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：座面上侧和前沿、支承框架外侧；板面扫描与扫掠支承件长轴笔画组合。
- 机器定位与处理：座底不在本轮声明的喷涂范围。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 9–10，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:backless_bench`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：U 型腿覆盖局部，座板窄侧面覆盖不全。 审查记录见 [`workpiece__backless_bench.json`](../../../reviews/trajectories/workpiece__backless_bench.json)（`b1534ea7`）。
- 根因：连通 U 件被当单根杆，边缘采样与窄面分行不稳定。
- 修复：按 U 型两端规划外侧腿；座板侧边加密取样并按外露方向覆盖。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 13–13，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:backless_bench`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：U 型腿底横梁漏喷，腿部覆盖不足。 人工审查提交 `8c28cdc8`，详见 [`workpiece__backless_bench.json`](../../../reviews/trajectories/workpiece__backless_bench.json)。
- 根因：U 型件被当成两根竖直立柱，未沿底部横梁规划。
- 修复：在两侧立腿之外增加底部横向长笔画，保持整件首命中和移动校验。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 13–15，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:backless_bench`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。


## 2026-11-21：第四轮轨迹审查通过

- 用户确认本轮轨迹候选通过；正式记录见 [`workpiece__backless_bench.json`](../../../reviews/trajectories/workpiece__backless_bench.json)。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:backless_bench`，规划源码提交 `8bb4440a`，全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。本结论绑定该模型、seed 和轨迹版本；实体机器人可达性与涂层质量尚未验证。
