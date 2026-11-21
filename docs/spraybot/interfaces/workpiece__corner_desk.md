# `workpiece:corner_desk` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：两块桌面上侧和前沿、支腿外侧；每块桌面分别扫描，内角和支腿接头处拆笔。
- 机器定位与处理：桌面底侧不在本轮范围。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 43–51，小于 50 mm 的笔画合计 0 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:corner_desk`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌板侧面遗漏，腿部喷枪可能进入家具包络内部。 审查记录见 [`workpiece__corner_desk.json`](../../../reviews/trajectories/workpiece__corner_desk.json)（`b1534ea7`）。
- 根因：内部接缝与外缘混淆，腿的候选法向未优先外部方向。
- 修复：选完整外露桌板边并单行覆盖；腿优先从整体凸包外侧接近，记录包络诊断。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 23–24，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:corner_desk`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：部分桌腿路径的喷枪位置落入整件外包络内部。 人工审查提交 `8c28cdc8`，详见 [`workpiece__corner_desk.json`](../../../reviews/trajectories/workpiece__corner_desk.json)。
- 根因：旧凸包只作诊断，没有约束候选路径。
- 修复：桌腿候选按整件凸包筛除明显位于内部的喷枪路径，保留外侧方向。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 19–21，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:corner_desk`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。

## 2026-11-21：第四轮人工审查与轨迹修复

- 症状及证据：一根在凸包内的桌腿其实可由开放转角斜向喷涂。 人工审查提交 `c07283ec`，详见 [`workpiece__corner_desk.json`](../../../reviews/trajectories/workpiece__corner_desk.json)。
- 根因：前轮只按轴向喷枪位置的凸包外侧比例筛选，误排除了开放转角的自由空间。
- 修复：对轴向候选均落在凸包内的腿搜索水平斜向接近角，以目标面首命中、喷枪净空及运动校验选入两面轨迹。 实现提交 `8bb4440a`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 21–23，短于 50 mm 的笔画合计 0 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:corner_desk`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
- 新增转角腿两笔的喷枪位置仍处于整件凸包内，但均由开放角斜向接近，逐笔保持至少 50 mm 实体净空；该凸包提示留给人工判断。
