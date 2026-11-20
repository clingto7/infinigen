# `workpiece:staggered_display_shelf` 接口经验

## 2026-11-20：移除不可喷涂的窄夹层

- 症状：旧模型的全宽低层横板与右侧横板之间，在 seed 0–3、5–9 出现约 2–10 cm 的狭窄夹层；seed 4 两板近乎相交，目视不见夹层。
- 范围与根因：所有 seed 均有这两块板；低层高度随机取 `mid * 0.42–0.58`，右侧板固定在 `mid * 0.55`，两者相互独立，因而形成窄缝或相交。
- 修复：在生成器中移除冗余右侧横板，保留低层全宽板、左侧中层板和高层全宽板。源码提交 `b4ec2575`；旧模型审查证据随之失效。
- 重验：服务器以 `b4ec2575` 重生 seed 0–9，用户确认新模型和参数化描述可通过；另生成 seed 0–19，独立参数化几何门禁与捕获不变性门禁均通过。新证据位于服务器 `/home/ma-user/ws/spray-review/pretrajectory-20seed-b4ec2575`，正式模型结论在 `reviews/interfaces/workpiece__staggered_display_shelf.json`。
- 尚未验证：喷涂轨迹、机器人可达性和涂层质量。
