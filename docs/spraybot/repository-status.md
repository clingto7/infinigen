# 仓库现状

日期：2026-10-18。本文说明当前 fork 里两套工件怎么生成、怎么审查。类别清单本身不在这里重复。

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

57 类都已注册，可以生成。候选文档里各类写的“20 个种子已通过自动检查”是并入远端之前、针对当时本地生成器的结果，状态仍是待人工复核。并入之后柜体、桌台和门窗的编号做了改写，正式审查要在当前分支上按上面的命令重跑，再填人工模板。通过之前不要把这些类计入已验收的 80 类。

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
