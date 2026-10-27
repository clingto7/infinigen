# 本机交互式工件生成器

该本机 Web 界面可选择已注册接口、输入随机种子并生成工件。三栏 A 布局同时展示生成控件、可交互的 3D 网格和逐面描述数据。

## 启动

在仓库根目录执行：

```bash
uv run python scripts/spraybot_generator_ui_server.py
```

浏览器打开 <http://127.0.0.1:8765/>。默认监听回环地址，只供本机访问。自定义端口：

```bash
SPRAYBOT_UI_PORT=9000 uv run python scripts/spraybot_generator_ui_server.py
```

然后打开 `http://127.0.0.1:9000/`。停止服务按 `Ctrl-C`。

界面用 Three.js 的 jsDelivr CDN 模块渲染 3D 网格，浏览器需能访问该 CDN。生成器继续使用项目当前 Python 环境和 Blender 依赖。

## 使用

1. 在“生成接口”中选 `Workpieces` 或 `Spraybot` 接口。
2. 输入非负随机种子，点“生成模型”。接口列表来自当前代码注册表。
3. 在模型上拖动可旋转视角，滚轮缩放，点“重置视角”恢复取景。
4. 用“面字段”选择默认材质色、`spray_target`、`spray_target_reason`、`geometry_accessible`、`max_passable_radius_m` 或 `spray_part` 着色。点一个三角面可查看该面的部件、目标状态及原因、外部连通状态和最大通路半径。
5. 右侧结果栏显示网格规模、可达面数、半径 p95、部件图例和 `structure_priors`。

字段颜色说明：

- `spray_target`：灰为非目标，红为目标。
- `spray_target_reason`：绿为目标，黄为非喷涂材料，紫为部件策略排除，蓝为内部空腔/流道排除。点击面可查看稳定类别名。
- `geometry_accessible`：橙为邻接自由空间不连通外部，青为连通。
- `max_passable_radius_m`：蓝到红对应 0 到该模型半径 p95；高于 p95 的值按红色显示。点击面可读取原始米制数值。
- `spray_part`：不同颜色区分语义部件编号；具体名称见右侧图例。

`spray_target` 由接口的喷涂任务策略和材料标签决定，不从外部连通性推断。例如 `valve_housing`、`tee_pipe` 内腔和管道内壁设为非目标；它们仍可能 `geometry_accessible=True`，可达性与目标意图分别表达。

每个面都带 `spray_target_reason`：`0=target`、`1=non_spray_material`、`2=component_policy`、`3=internal_cavity`。目前玻璃、把手和封闭抽屉盒分别按材料或部件策略排除；阀壳和三通管内壁按内腔策略排除。布料等材质由类别生成器显式标注为非目标后，使用同一 `non_spray_material` 原因码；该字段不会仅凭几何或外观猜测材质。

每次生成在临时目录中运行 Blender worker，返回网格和面字段后删除临时文件。结果保存在浏览器内存中；关闭或刷新页面后需重新生成。
