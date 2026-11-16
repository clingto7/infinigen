# 本机交互式工件生成器

该 Web 界面可加载已有审查样本，也可选择已注册接口、输入随机种子现场生成。三栏布局分别放置样本入口、可交互的 3D 视图和审查数据。模型与参数化描述叠层有独立显示开关，默认只显示模型。

## 启动

在仓库根目录执行：

```bash
uv run python scripts/spraybot_generator_ui_server.py
```

浏览器打开 <http://127.0.0.1:8765/>。默认监听回环地址，只供本机访问。自定义端口：

```bash
SPRAYBOT_UI_PORT=9000 uv run python scripts/spraybot_generator_ui_server.py
```

要把本轮生成结果集中保存为可复查的 review root，并在下次启动时直接加载已有结果：

```bash
uv run python scripts/spraybot_generator_ui_server.py \
  --review-root outputs_scratch/review-20261112 \
  --trajectory-root outputs_scratch/trajectory-review
```

该目录由 `review_manifest.json` 和按接口分组的 `interfaces/*/episodes/seed_*` 组成。模型、面字段、结构先验和参数化描述都保存在 episode 的
`model.json` 中；生成过程不会覆盖已有完整 seed。界面左栏的“加载已有审查样本”读取
同一目录，与“现场生成新样本”分开；两处接口选择都支持搜索，标签格式为 `id - 工件名`。
机器门禁通过后，用 `scripts/spraybot_interface_state.py machine-pass <interface-id> <machine-check.json>`
将该接口记为 `awaiting_review`，并提交生成的 `reviews/interfaces/*.json`。审查结论由 Web 写入该仓库文件；Git 提交后才正式生效。review root 只保存样本和机器证据，可任意指定，不保存权威审查状态。
若生成几何、参数曲面、目标面策略或导出契约发生影响产物的改动，先执行
`python scripts/spraybot_interface_state.py invalidate <interface-id> '<原因>'` 并提交，再重跑该接口的机器门禁与人工审查。

轨迹工作区按 `<trajectory-root>/<interface-id>/seed_0000000000.json` 放置与审查样本配对的轨迹视图数据。加载同一接口和 seed 后，打开“显示轨迹”才读取轨迹，并在模型上叠加、于右栏逐笔查看喷向及中点射线异常。所有工件共用这一入口；尚无配套轨迹时右栏会说明。接口专属轨迹程序位于本仓库 `scripts/spraybot_trajectory/`，规划要求见[轨迹生成流程](trajectory-generation.md)；轨迹结论独立于生成接口的 `ready`。

本轮 radar 审查服务可通过笔记本 SSH 转发访问：

```bash
ssh -N -L 18765:127.0.0.1:8765 radar
```

随后打开 <http://127.0.0.1:18765/>。统一审查目录位于 radar 的
`/home/sentry/ws/infinigen-spray-parametric-v2-output/web-review-current-20261115`，轨迹目录为
`/home/sentry/ws/infinigen-spray-parametric-v2-output/web-trajectory-root-20261115`。

若使用上面的本机自定义端口 9000，则打开 <http://127.0.0.1:9000/>。停止服务按 `Ctrl-C`。

界面用 Three.js 的 jsDelivr CDN 模块渲染 3D 网格，浏览器需能访问该 CDN。生成器继续使用项目当前 Python 环境和 Blender 依赖。

## 使用

1. 从“加载已有审查样本”选接口和 seed；选中 seed 后自动加载，逐个查看一个接口的十个样本。额外抽样时再用“现场生成新样本”。
2. 在模型上拖动旋转、滚轮缩放，点“重置视角”恢复取景。用“显示模型”与“显示参数化描述”分别切换网格和参数叠层，可单独看其中之一，也可叠加比较。
3. 用“面字段”选择默认外观、`spray_target`、`spray_target_reason`、`geometry_accessible`、`max_passable_radius_m` 或 `spray_part` 着色。显示模型时点击三角面，可看该面的部件、目标状态、排除原因、外部连通状态及通路半径。
4. 参数叠层显示采样点与线；`csg_trimmed_face` 的闭合彩线标示裁剪边界和孔洞边界。它是人工概览，不代替独立机器门禁的精确几何与法向检查。
5. 右侧滚动栏分别展示样本统计、逐面字段、参数化描述、部件图例、可选的 `structure_priors` 与接口级审查。`structure_priors=null` 表示此接口没有专用结构先验，不代表 `parametric` 缺失。
6. 审查结论以接口为单位，填写审查人并选“待审查”“通过”或“需要修复”。在对应字段的文本框写当前 seed 的问题，保存时自动关联 seed；再次加载该 seed 可修改或清空反馈。未解决问题存在时不能标记通过。结果写入仓库的 `reviews/interfaces/*.json`，界面会标出尚未 Git 提交的结论。
7. 打开“显示轨迹”后，若该接口和 seed 有配套轨迹，右栏“喷涂轨迹”可切换笔画、显示全部笔画，并跳到下一个异常。

字段颜色说明：

- `spray_target`：灰为非目标，红为目标。
- `spray_target_reason`：绿为目标，黄为非喷涂材料，紫为部件策略排除，蓝为内部空腔/流道排除。点击面可查看稳定类别名。
- `geometry_accessible`：橙为邻接自由空间不连通外部，青为连通。
- `max_passable_radius_m`：蓝到红对应 0 到该模型半径 p95；高于 p95 的值按红色显示。点击面可读取原始米制数值。
- `spray_part`：不同颜色区分语义部件编号；具体名称见右侧图例。

`spray_target` 由接口的喷涂任务策略和材料标签决定，不从外部连通性推断。例如 `valve_housing`、`tee_pipe` 内腔和管道内壁设为非目标；它们仍可能 `geometry_accessible=True`，可达性与目标意图分别表达。

每个面都带 `spray_target_reason`：`0=target`、`1=non_spray_material`、`2=component_policy`、`3=internal_cavity`。目前玻璃、把手和封闭抽屉盒分别按材料或部件策略排除；阀壳和三通管内壁按内腔策略排除。布料等材质由类别生成器显式标注为非目标后，使用同一 `non_spray_material` 原因码；该字段不会仅凭几何或外观猜测材质。

每次现场生成在临时目录中运行 Blender worker；启用 review root 时，完整结果会在返回浏览器前写入该目录，
因此可重复加载并交给后续 contact-sheet 导出。未启用 review root 时仍保持原来的临时内存模式。
