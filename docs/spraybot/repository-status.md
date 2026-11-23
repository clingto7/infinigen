# 仓库现状

## 当前状态（2026-11-23）

20 个工件接口批次（2026-11-20 启动）的轨迹工作已收尾：18 个活跃接口在第四轮人工复审后轨迹
`accepted`（机器全批审计 180/180 通过，规划源码 `72496fb1`）；`staggered_display_shelf` 与
`windsor_chair` 因结构过于复杂被人工主动 `deferred`（搁置）——区别于 `needs_fix`，不携带缺陷清单，
接口与审查历史保留，恢复须先重建机器证据。轨迹审查语义与 `deferred` 状态见
[接口工作流](interface-workflow.md) 第 5 节；各轮审查意见与整类修复规则沉淀在
[轨迹生成说明](trajectory-generation.md) 的轮次章节。

接口级结论语义在本轮确立：每接口 10 个审查 seed 代表接口状况，人工结论不落到单个 seed；
为展示或抽检额外生成的新 seed 不需逐笔复审。`armchair` seed 23、24 在展示抽样中规划失败，
根因（包围盒极值端点落在网格轮廓切线）与跨机不可复现限制已补录到
[接口经验记录](interfaces/workpiece__armchair.md)；"端点首命中预检"列入该规划器下次整类修复。
凸包/包络处理（当前仅为规划裁剪与人工复核线索）已确定为后续方向，待单独设计语义与阈值后再进
参数化契约或机器门禁。

spraybot 服务器（ModelArts 实例）的原 `/home/ma-user/ws/` 用户空间证据已被实例回收；
项目部署与后续证据统一放在共享盘 `/sfs/hqb/`：代码在 `/sfs/hqb/infinigen-spray`
（Git HEAD `fe3bc4b6`，与本仓库 origin/main 同步；实例无法直连 GitHub，用 rsync 从本机同步），
Python 环境在 `/sfs/hqb/envs/infinigen`（conda prefix，Python 3.11.18，按 Dockerfile 依赖
`pip install -e ".[dev]"` 安装，pip 走华为云镜像）。运行方式：
`/sfs/hqb/envs/infinigen/bin/python`，脚本类调用加 `PYTHONPATH=scripts`。
2026-11-23 冒烟通过：bpy 4.2.0 headless 导入、`coat_rack` seed 0 真实生成、
`spraybot_trajectory` 与审查模块导入均正常。生成不是跨平台位级可复现的，
证据哈希只对产出主机有效，见 [接口工作流](interface-workflow.md) 第 6 节。

轨迹生成结果的展示汇总（18 接口 × 5 新 seed × 参数化/轨迹八视角图）见飞书文档
"轨迹生成结果汇总"（wiki `EiwLwVY9Ci9Rf7k0fV3c1JQInAj`）。

## 当前状态（2026-10-26）

当前仓库位于 `main`，HEAD 为 `c45fbf6f`，与 `origin/main` 同步。本文后面的
10 月 18 日及 10 月 20 日记录保留为历史进度；其中分支名、类别计数和目录说明不代表当前状态。

当前代码保留两个生成入口：旧入口 `infinigen2.objects.spraybot.generate_workpiece`，以及按
工件类别注册的 `infinigen2.workpieces.generate`。后者已增加 D 档复杂壳体：G01–G30 候选中
人工筛选出 22 类，清单见 [complex-workpiece-available-set.md](complex-workpiece-available-set.md)。
最近的提交还修复了 `connected_drums` 的内孔连通，并在 D 档生成结果中写入逐面
`spray_visibility`。

逐面字段分工如下：`spray_part` 记录部件语义；`spray_target` 由材料和接口的喷涂任务策略决定，
不根据外部连通性自动推断；D 档 `spray_visibility` 记录 16 个确定性半球方向的射线逃逸比例。
自 2026-10-27 起，`valve_housing` 和 `tee_pipe` 的内部空腔及管道内壁显式标为非 target；
这类面仍可在几何上连通外部。`geometry_accessible` 与 `max_passable_radius_m` 继续描述几何，
不决定任务目标，也不证明轨迹覆盖、机器人可达性或涂层质量。
新增逐面 `spray_target_reason` 整数字段：`0=target`、`1=non_spray_material`、
`2=component_policy`、`3=internal_cavity`，用于区分玻璃等材料、部件策略和空腔策略排除。

第一轮接口已加入当前代码：`car_bumper`、`opus_chair` 和 `infinigen_chair`。它们保留源工厂
随机结构分支，并把源 `part_type` 映射到共享 `spray_part` 语义；可选生成记录通过
`WorkpieceResult.structure_priors` 返回。22 个 D 类已设置 0.5–1.5 的整体缩放范围。

第二轮已接入逐面 `geometry_accessible` 与 `max_passable_radius_m`，并覆盖两套生成入口。
实现以每个网格最长边 96 个体素做自由空间外连通与通路净空估计；属于离散几何近似，窄于体素的
开口可能被误判关闭。`scripts/spraybot_validate_one.py` 新增三字段着色图和图例，20 种子验证器
会要求 `face_fields.png`，contact sheet 另生成逐面字段拼图。`stepped_cavity` 与旧入口
`slat_back_chair` 的 seed 0 冒烟生成已通过；全量 20 种子复验尚未运行。

2026-10-26 验证批次已完成：22 个 D 类各生成 20 个种子（440/440），三个原生接口各生成 20 个
种子（60/60）。最终统一批次共 500/500 个样本，全部通过基础几何、喷涂字段检查；每接口 20 个
种子的归一化形状均有变化。25 个类别的拼图位于 `outputs_scratch/phase1-20261026/contact_sheets/`。
Infinigen Chair 还保留了每个部件的中心线先验和源脚本的 Z 旋转匹配；20 个种子都记录了 9–13 条
中心线，所有记录均有旋转匹配。
为运行原生工厂，本机 `.venv` 补装了项目 `infinigen1` 可选依赖组中已声明的 `gin-config`、
`networkx`、`scikit-learn`、`psutil`；未修改项目依赖声明。

本次项目工作区另有未跟踪目录 `draft_e4186e6d_folder/`，应在后续操作中保留。

### 已确定的生成扩展安排

- 第一轮接入 Spraybot 原生 `CarBumper`、`OpusChair`、Infinigen `ChairFactory`，分别使用
  `car_bumper`、`opus_chair`、`infinigen_chair` 接口 ID，并保留这三个来源的原生离散分支随机性；
  这是一次例外，不改变其他类别锁定结构分支的约定，见 [ADR 0001](../adr/0001-preserve-spraybot-native-generators.md)。
- 同轮对 22 个 D 档几何工件使用 0.5–1.5 的整体等比例缩放因子。接口交付人工审核前，对每类做
  20 种子外形与尺寸检查并生成模型拼图。
- 第二轮新增几何可达性面属性：与外部空间连通状态、通道最大可通过半径；不纳入通路长度。
  字段定义、分辨率限制及可视化要求见 [兼容契约](compatibility-contract.md)。

---

## 历史状态记录

日期：2026-10-18。以下为当时记录的生成与审查方式。类别清单本身不在这里重复。

本仓库是 Infinigen 2 的 Spraybot fork。生成几何和面上的 `spray_part`、`spray_target` 归本 fork；轨迹、PaintDS 和训练格式归 Spraybot。两边通过导出的网格和标签对接，不互相 import。字段约定见 [compatibility-contract.md](compatibility-contract.md)。

当前可生成的工件分成两套，类别 ID 不重叠：

| | 旧工件 | 新工件 |
| --- | --- | --- |
| 数量 | 36 | 57 |
| 入口 | `infinigen2.objects.spraybot.generate_workpiece` | `infinigen2.workpieces.generate` |
| 名单 | `spraybot.CATEGORY_IDS` | `workpieces.CATEGORY_IDS` |
| 清单 | [adopted-workpiece-categories.csv](adopted-workpiece-categories.csv) | [workpiece-expansion-candidates.md](workpiece-expansion-candidates.md) |
| 编号 | 每个类别一份本地图例，写在 `spraybot.LEGENDS` | 全库一张共享表，写在 `src/infinigen2/util/spray.py` |
| 代码位置 | `src/infinigen2/objects/spraybot.py` 调用原有生成器 | `src/infinigen2/workpieces/`，按 A/B/C 档，再按坐具、桌台、柜架、床具、门窗、其他分目录 |

同一 ID 若两边都有，命令行工具走旧入口。目前没有这样的 ID。

本地分支是 `spraybot-workpieces`，基于远端 `main`（`f41960ab`），扩展工件在提交 `50367c43`。旧生成器以远端实现为准；新类别只在调用时追加可选参数，或在进入新接口之后把远端的本地编号改写成共享部件名。默认不传这些参数时，旧类别的随机序列和图例不变。

## 生成

在仓库根目录执行，使用本机虚拟环境。下面是 PowerShell。

```powershell
$env:PYTHONPATH = "src"
```

### 旧工件

```python
import numpy as np
from infinigen2.objects.spraybot import generate_workpiece

result = generate_workpiece("slat_back_chair", np.random.default_rng(0))
result.mesh          # 带面属性的网格
result.part_legend   # 该类别自己的编号，例如 {0: "seat", 1: "slat_back", 2: "straight_base"}
```

`spray_part` 的整数只在该类别的 `LEGENDS` 里有意义。柜体的 `0` 是柜体，餐桌的 `0` 是桌面，不要拿去和新工件的共享表对照。玻璃等不喷涂的面留在网格里，`spray_target` 为假。

单件抽查：

```powershell
.venv\Scripts\python scripts\spraybot_probe.py slat_back_chair 0 outputs_scratch\probe-old
```

`probe` 先查旧名单，再查新名单。

### 新工件

```python
import numpy as np
from infinigen2.workpieces import generate

result = generate("backed_bench", np.random.default_rng(0))
result.part_legend   # 共享表里的名字，例如 {0: "seat", 1: "back", 4: "leg_base"}
```

`generate` 会删掉面积小于 `1e-7` 的退化面，并检查实际出现的部件名是该类 `allowed_parts` 的子集。缺某个部件可以，多出一个未声明的部件会报错。

共享编号：

| 编号 | 名称 | 编号 | 名称 |
| --- | --- | --- | --- |
| 0 | seat | 11 | drawer_front |
| 1 | back | 12 | headboard |
| 2 | slat | 13 | frame |
| 3 | arm | 14 | handle |
| 4 | leg_base | 15 | outer_frame |
| 5 | top | 16 | mullion |
| 6 | carcass | 17 | sash |
| 7 | shelf | 18 | louver |
| 8 | back_panel | 19 | casing |
| 9 | door_frame | 20 | glass |
| 10 | door_panel | 21 | drawer_box |

`handle`、`glass`、`drawer_box` 不作为本体喷涂目标。门窗类里，百叶和棂条若和外框写在同一块网格上，审查时看几何，不要只凭部件名判断百叶是否存在。

每个新类别一个模块，例如 `src/infinigen2/workpieces/a/seating/backed_bench.py`。模块锁定结构分支、声明允许的部件，几何仍调用 `src/infinigen2/objects/` 里的函数。

单件抽查：

```powershell
.venv\Scripts\python scripts\spraybot_probe.py backed_bench 0 outputs_scratch\probe-new
```

## 审查

自动检查只证明能生成、网格可用、类内有变化。它不决定这是不是一个合格喷涂类别。人工审查用 [manual-review-template.md](manual-review-template.md)，不能用自动标签代替。

两类共用同一套脚本。`--category` 在旧名单里时前缀是 `spraybot:`，只在新名单里时前缀是 `workpiece:`。

```powershell
.venv\Scripts\python scripts\spraybot_validate.py outputs_scratch\<类别>-validate --category <类别 ID> --seeds 20
.venv\Scripts\python scripts\spraybot_contact_sheets.py outputs_scratch\<类别>-validate
```

每个种子目录里有 `model.blend`、`view_0.png`、`view_1.png` 和 `result.json`。拼图在该次输出的 `contact_sheets/`。同一输出目录不能改种子列表再续跑；要换种子就换一个输出目录，或使用 `--start-seed` 另开一段。

然后把人工审查模板复制进该次验证目录，对照拼图和若干单件填写。要看的是：

- 20 个种子是否保持该类的结构判据，类内是否仍有可见的几何差异。
- 主要外露表面是否可喷涂；玻璃、布艺、陶瓷是否被排除在 `spray_target` 之外。
- `spray_part` 是否对得上该入口自己的图例。旧类对 `spraybot.LEGENDS`，新类对共享表和该模块的 `allowed_parts`。
- 可喷外露面积是否够用。边界情况写进记录，不改写成已经通过。

轨迹、机器人可达性和真实涂层质量不在这次审查里。它们记为下游未验证项。

### 旧工件现在审到哪

36 类的采用状态和批次写在 [adopted-workpiece-categories.csv](adopted-workpiece-categories.csv)，批次说明在 [README.md](README.md) 的 “Current furniture baseline”。试点类是 `slat_back_chair`、`straight_leg_desk`、`open_cell_shelf`、`legged_solid_headboard_bed`、`door_with_handle`、`window_rectangular_frame`。正式可用要同时通过生成、20 种子自动检查、拼图、人工审查和兼容导出。

这 36 类的几何和默认图例以远端 `main` 为准。接入新工件时没有改它们的默认抽样。`door_with_handle` 在开启喷涂标签时曾引用不存在的 `body_style`，现已按该函数自己的说明写成“全部门面都是喷涂目标”，编号仍是 0 框、1 芯板、2 把手。若要正式确认这一处修复，对 `door_with_handle` 重跑 20 个种子即可。

### 新工件现在审到哪

当前正式登记 54 类，可以生成。合并前的 57 个接口已完成 1140 个样本的 20 种子自动检查，
全部通过几何、类内变化和语义字段检查；每个接口的 seed 0 兼容导出探针也全部通过。
后续按相似实现合并并复核注册表后，`plant_stand` 与 `step_stool` 合为
`stepped_platform`；该合并接口和基线柜体合并接口均另做了 20 种子生成及语义检查。
完整验证产物位于 `outputs_scratch/review-expansion-20seed-complete-20261018/`，其中
`contact_sheets/` 含 57 张按接口命名的拼图；兼容导出位于
`outputs_scratch/review-expansion-probe-20261018/`。自动检查通过也不替代人工审查，
所有新类在人工审查记录完成前仍不计入已验收的 80 类。

验证器对生成源网格检查 `spray_part`/`spray_target`，对修改器评估网格检查几何。
部分上游门窗和柜体修改器会在评估副本中保留旧的本地部件编号，不能拿它和扩展接口的
共享 legend 直接比较；导出接口使用源网格。

### 2026-10-20 结构连通复审

第一批 contact sheet 人工反馈“部分结构悬空”后，对 20261018 全量 1140 个样本做了
连通岛审查（`scripts/spraybot_island_audit.py`）：把合并网格按边连通拆件，包围盒
间隙 ≤1 mm 的件并岛，门窗抽屉等活动件按设计间隙豁免。结论是 5 个类别存在真实的
悬空子装配，已修复并按 20 种子复验清零：

| 类别 | 悬空部件 | 修复 |
| --- | --- | --- |
| `bunk_bed` | 床尾爬梯（距床架 10 cm）、上层两条护栏（距立柱 7.7 cm，两端够不到立柱） | 爬梯移入床架端面内；护栏加长到插入立柱 |
| `hairpin_leg_table` | 全部四个 V 形腿，弯头顶点停在桌面下 5 cm，桌面完全悬空 | 顶点伸入桌板底面 |
| `high_chair` | 两侧围挡与前围挡整体悬在座面上方约 1 cm | 侧围挡下延插入座面，前围挡加宽与侧围挡搭接 |
| `crib` | 床板四周缩进 3 cm，够不到角柱 | 床板放大到插入角柱 |
| `wardrobe` | 挂衣杆两端距侧板 4–6 cm，顶部搁板缩进 2.5 cm 部分种子悬空 | 挂衣杆伸入侧板，搁板缩进减到 1.2 cm |

另有 9 个柜体/长凳类别存在约 2 mm 的腿-柜体装配间隙，低于可见阈值，按设计间隙
记录，未改动。其余 43 类连通岛审查干净。用户指出的 `armchair`、
`ladder_back_chair`、`louvered_cabinet` 渲染悬空感确认为渲染表现：几何包围盒
真实重叠。审查的同时重写了审查图渲染：448 px、浅灰蓝背景、场景地面接触阴影和
cavity 描边（`scripts/spraybot_validate_one.py`），并用新渲染重跑了全量
57 类 × 20 种子，产物在 `outputs_scratch/review-expansion-20seed-20261020/`。
此前 20261018 的黑色背景目录保留作对照。

上述修复后的代码已于 2026-10-21 同步到 `sentry` 的
`/home/simulator/ws/infinigen-spray`（该目录不是 git 仓库，用 rsync 同步；同步前的
src/scripts 已打包为远端 `infinigen-spray-code-backup-20261021.tar.gz`）。四个
10000 批（open_cell_shelf、slat_back_chair、solid_back_chair、wheeled_dining_chair）
已全部完成且零失败；batch_2 剩余三类 storage_cabinet_single_door、
storage_drawer_cabinet、storage_shelf_on_base 已按 3 类 × 2 workers、CPU-only 的
既定策略在 tmux（`prod-<类别>`）续跑，double_door_with_handle 排在下一批。

待定项 T05、C05、C06、W04 和候选文档里的备选没有实现。

早期原生接口是否算工件，用的是另一套流程，见 [manual-review-sop.md](manual-review-sop.md) 和 `interface-review-worksheet.csv`。那是分类阶段，不是这两套固定入口的验收。

## 相关文档

| 文档 | 用途 |
| --- | --- |
| [README.md](README.md) | 80 类目标和旧工件的标准验证命令 |
| [adopted-workpiece-categories.md](adopted-workpiece-categories.md) | 旧工件的家族、锁定条件和计数口径 |
| [workpiece-expansion-candidates.md](workpiece-expansion-candidates.md) | 新工件的结构判据、实现路径和复核状态 |
| [compatibility-contract.md](compatibility-contract.md) | 导出给 Spraybot 的字段 |
| [manual-review-template.md](manual-review-template.md) | 每类人工审查记录 |
