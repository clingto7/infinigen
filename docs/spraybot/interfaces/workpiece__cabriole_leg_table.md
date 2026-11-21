# `workpiece:cabriole_leg_table` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：桌面上侧和前沿、雕花腿各可见外侧、围裙外侧；桌面逐行，腿按生成分段走连续可见面。
- 机器定位与处理：桌腿上段接头只剩短可见区；保留至少 30 mm 的独立笔画，小于 50 mm 的笔画作为人工审查重点。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 56–57，小于 50 mm 的笔画合计 16 条，完全遮挡行 80 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:cabriole_leg_table`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：桌板四个窄侧面不对称；每条腿被切成多段密集双行。 审查记录见 [`workpiece__cabriole_leg_table.json`](../../../reviews/trajectories/workpiece__cabriole_leg_table.json)（`b1534ea7`）。
- 根因：窄板被多行栅格化，曲腿每个短面独立分段。
- 修复：桌板四个外露窄边各用单行；四条腿各沿正面与两侧规划三条长笔画。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 21–21，小于 50 mm 的笔画合计 0 条，完全遮挡行诊断合计 40 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:cabriole_leg_table`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。


## 2026-11-21：第四轮轨迹审查通过

- 用户确认本轮轨迹候选通过；正式记录见 [`workpiece__cabriole_leg_table.json`](../../../reviews/trajectories/workpiece__cabriole_leg_table.json)。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-18-review6-8bb4440a/workpiece:cabriole_leg_table`，规划源码提交 `8bb4440a`，全批审计 `/home/ma-user/ws/spray-review/batch-audit-18-8bb4440a.json` 为 180/180 通过。本结论绑定该模型、seed 和轨迹版本；实体机器人可达性与涂层质量尚未验证。
