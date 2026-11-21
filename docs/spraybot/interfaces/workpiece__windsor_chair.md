# `workpiece:windsor_chair` 接口经验

## 2026-11-21：首轮轨迹候选

- 源码：`3961174e`；模型与参数化描述已通过本轮先行审核。
- 工艺范围和分段：座面上侧、椅背弧杆前后侧、竖向椅背杆及腿和横撑外侧；圆杆按生成轴线走纵向笔画。
- 机器定位与处理：初版最短长度规则漏掉弧杆分段；改为保留结构明确的短弧杆后，六段椅背均有轨迹。
- 尚需人工逐笔审查实际喷涂范围、路径自然程度和姿态；实体喷枪、机器人可达性及涂层质量另行验证。
- 机器复验：seed 0–9 均通过（10/10）；笔画数 22–32，小于 50 mm 的笔画合计 46 条，完全遮挡行 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-final-3961174e/workpiece:windsor_chair`；全批审计为 200/200 通过。

## 2026-11-21：第二轮轨迹修复

- 症状及证据：腿、横撑与弧形靠背路径需复查。 审查记录见 [`workpiece__windsor_chair.json`](../../../reviews/trajectories/workpiece__windsor_chair.json)（`b1534ea7`）。
- 根因：弧形和细杆的离散取样可能出现急转、遗漏。
- 修复：曲面整笔平滑，立腿外侧走笔、横撑外侧接近，窄边加密取样。 实现提交 `c98a211d`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 26–36，小于 50 mm 的笔画合计 46 条，完全遮挡行诊断合计 0 行。配对证据位于 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-20-review4-b19008cd/workpiece:windsor_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-20-b19008cd.json` 为 200/200 通过。轨迹仍待人工逐笔审查；机器人可达性和实体涂层质量尚未验证。

## 2026-11-21：第三轮人工审查与轨迹修复

- 症状及证据：back 与 slat 的部分圆杆路径过短、过碎。 人工审查提交 `8c28cdc8`，详见 [`workpiece__windsor_chair.json`](../../../reviews/trajectories/workpiece__windsor_chair.json)。
- 根因：固定径向接近角在相邻构件旁被遮挡，长杆因此拆段。
- 修复：沿圆杆轴每 15° 搜索径向接近角，选最长的连续可见路径。 实现提交 `23a38bad`。
- 复验：seed 0–9 机器门禁 10/10 通过，笔画数 26–38，短于 50 mm 的笔画合计 18 条。配对证据在 spraybot 服务器 `/home/ma-user/ws/spray-review/trajectories-19-review5-23a38bad/workpiece:windsor_chair`；全批审计 `/home/ma-user/ws/spray-review/batch-audit-19-23a38bad.json` 为 190/190 通过。轨迹仍待人工逐笔审查；机器人可达性与实体涂层质量未验证。
- 剩余 18 条短笔画均来自原长约 55–65 mm 的独立 `back` 圆杆，沿杆各只有一笔；长 `slat` 的碎段已消除。这些短杆是否值得单独喷涂仍由人工审查决定。


## 2026-11-21：第四轮暂缓

- 人工审查提交 `c07283ec` 记录用户决定暂停该复杂接口的后续轨迹工作；`8bb4440a` 将其从活跃批量生成和审计清单移出。
- 已注册接口、模型、参数化描述与既有轨迹审查历史均保留；本轮没有新轨迹产物，也不宣称修复或接受。
