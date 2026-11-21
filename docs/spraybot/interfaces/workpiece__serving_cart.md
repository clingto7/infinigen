# `workpiece:serving_cart` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：三层托盘上侧及前沿、外侧框架、向外的车轮圆盘面和长圆杆；板面与圆杆分别规划。
- 机器定位与处理：车轮短侧壁和向内轮面不在本轮接近方向内。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 63–98，小于 50 mm 的笔画合计 0 条，完全遮挡行 80 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:serving_cart`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：板边、杆件和相邻密集行需复查。 审查记录见 [`workpiece__serving_cart.json`](../../../reviews/trajectories/workpiece__serving_cart.json)（`b1534ea7`）。
- 根因：窄面按通用栅格分行，外露边与内部连接面需区分。
- 修复：外露窄边居中单行，安全的面内行合并，内部连接面不喷。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 37–54，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 40 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:serving_cart`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：部分托盘边框与板边形成过密平行笔画。 人工审查提交 `8c28cdc8`，详见 [`workpiece__serving_cart.json`](../../../reviews/trajectories/workpiece__serving_cart.json)。
- 根因：框架侧面和托盘窄边被当成独立喷涂行。
- 修复：对共面、近距且面积相近的框架与板边只保留一组。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 30–48，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:serving_cart`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。

## 2026-11-21：第四轮人工审查与轨迹修复

- 症状及证据：托盘边与框架仍有间距约 21 mm 的同向平行笔画。 人工审查提交 `c07283ec`，详见 [`workpiece__serving_cart.json`](../../../reviews/trajectories/workpiece__serving_cart.json)。
- 根因：框架与板边面积比恰在旧去重阈值边界，重复行被保留。
- 修复：扩大同面近距边的面积比容差，保留托盘边的一道轨迹。 实现提交 `8bb4440a`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 29–42，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:serving_cart`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
- seed 0–9 的长平行笔画中未再发现同向且中点距离小于 40 mm 的重复对。


## 2026-11-21：第四轮轨迹审查通过

- 用户确认本轮轨迹候选通过；正式记录见 [`workpiece__serving_cart.json`](../../../reviews/trajectories/workpiece__serving_cart.json)。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:serving_cart`，规划源码提交 `8bb4440a`，全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。本结论绑定该模型、seed 和轨迹版本；实体机器人可达性与涂层质量尚未验证。
