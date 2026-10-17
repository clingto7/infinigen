# Spraybot 工件生成扩展

本 fork 用于开发和验证 Spraybot 的程序化工件生成器。目标是在本机做出并少量验证 80+ 个有喷涂结构差异的工件类别，不限于家具；大规模实例生成留给服务器。规划文档中的时间节点不作为当前约束。类别与喷涂任务的定义见 [CONTEXT.md](../../CONTEXT.md)。

类别应覆盖多个结构家族，不预设各家族配额。每开发出一个类别，就要抽样验证其几何、生成侧喷涂结构信息、稳定性和类内多样性；达到可批量生成的标准后才计入 80+。先用跨家族样例打通 Spraybot 轨迹与 PaintDS 数据链，再逐类扩展和验收。不同类别允许复用喷涂策略。独立喷涂的部件可以计入类别。

每个拟计入 80+ 的类别都须有明确、可调用的生成接口，能够用不同种子或参数快速批量生成同类实例。类内实例要有可观察的几何差异，同时保持该类别的结构判据；本机在每类产出时抽样验收，服务器只承担通过验收后的大规模实例生产。已有类别与新扩展类别采用同一标准。

现有 Spraybot 的普通椅、OpusChair 和汽车保险杠经同一类别判据与交付标准复核后可计入 80+ 总数。一个随机生成函数若覆盖多种结构，应拆分结构型计数，函数本身不单独占类别名额。制造喷涂需求不明确的候选暂不计入，交由人工核查喷涂任务。本 fork 负责几何与生成侧结构信息；专家轨迹、训练转换和模型仍归 Spraybot，双方通过跨家族样例核验接口。

候选的计数须结合实际可生成构型核查；电竞椅等例子不能仅凭名称计入。我先整理结构、材料与目标表面证据，争议项由用户或指定领域人员复核。各类本机验收不以机器人仿真或膜厚达标为必需条件；可做目标面可见性、喷枪空间等几何检查，完整机器人与喷涂质量验证留待轨迹及工位条件具备时进行，并标明尚未验证的指标。

## 来源与职责

| 内容 | 来源 | 在本 fork 中的处理 |
| --- | --- | --- |
| 工件类别、实例、可喷表面等术语 | Spraybot 仓库根目录 `CONTEXT.md` | 已复制到本 fork 根目录；后续类别判定以此为准 |
| 现有 Infinigen 生成及数据转换流程 | [Spraybot `datagen/README.md`](https://github.com/liang-zijian/Spraybot/blob/unitspray/datagen/README.md) | 保持在 Spraybot；本 fork 只开发生成侧，接口设计时对照该文档和代码 |
| 数据与模型的整体关系 | [Spraybot 数据方案](https://github.com/liang-zijian/Spraybot/blob/unitspray/docs/%E6%96%B9%E6%A1%88%E4%BB%8B%E7%BB%8D_%E6%95%B0%E6%8D%AE%E4%B8%8E%E6%A8%A1%E5%9E%8B.md) | 保持在 Spraybot；训练模型输入不应依赖 Infinigen 专有标签 |
| 后续规划 | 同级 Spraybot 工作区的 `paper-pptx/spraybot-proposal.md`，§4.1.1 | 只采用 80+ 与三级分类目标；该文件当前未纳入 Spraybot Git 跟踪，不把其中时间节点当作期限 |

## 已核实的生成方式

- Spraybot 的椅子生成脚本 `datagen/chair_spray/gen_chairs.py` 调用 Infinigen 1.0 `ChairFactory`，在生成时额外记录 `part_id`、`part_type`、杆件中轴线及靠背信息，再保存为 NPZ。OpusChair 与保险杠也有各自的生成和轨迹规则；现有三类约 3 万实例不等于 3 万类别。
- 本 fork 的基础版本是 Infinigen `a0d1a0d`（2.0.0a3）。本机执行 `.venv/bin/infinigen --list Object` 得到 94 个已注册函数名。清单含部件、植物、岩石、地形、布艺物件和随机包装函数，不能按名称计为 94 个合格工件类别。源码中还有未列入该清单的 `chair_bench_rand`。
- `table_side_rand` 等函数主要复用已有桌型并改变尺寸；类别审计需要检查拓扑、遮挡和可达面布局。Infinigen 2.0 的物体生成器通常返回网格，不能默认提供 Spraybot 使用的部件标签和中轴线。
- 本机以种子 0 运行 `chair_dining_rand`、`storage_cell_shelf_rand`、`door_composite_rand`，均保存并在 Blender 中检查了几何。三个样本的评估网格没有 Spraybot 所需的语义面标签。这仅证明跨家族几何可生成；尚未验证新类别的轨迹数据接入。

## 后续探索顺序

1. 逐项审计 1.0 工厂、2.0 注册函数及源码中未注册函数，建立结构家族 → 候选类别 → 生成路径的清单。标明“已有可用、需改造、需新建、喷涂工艺待确认”，并排除尺寸变体和随机汇总函数。
2. 选座椅、桌/架、门板等跨家族样本，试验生成时保留可喷表面、部件语义及按结构需要的轨迹先验；对照 Spraybot 当前数据链确定生成侧与轨迹侧的接口。
3. 根据实测缺口讨论实现方案。优先程序化扩展 Infinigen；具体结构难以覆盖时使用 Blender/CAD。扩展程序化生成器本身不需要训练模型；LLM/MCP 可辅助建模，但不是几何引擎或验收依据。
4. 方案确定后在本 fork 逐类实现生成器；每完成一类就做少量种子的几何、尺度、结构信息、类内多样性与基本喷涂空间检查，通过后才累计类别数。服务器只承担后续大规模生成。

当前尚无经审计的 80 类清单，也没有证明现成 Infinigen 已覆盖 80 类。

## Current furniture baseline

The active baseline is the 34-category furniture and door/window matrix in
[`adopted-workpiece-categories.csv`](adopted-workpiece-categories.csv). The old
40-entry registry remains available as historical/internal code, but only
accepted categories that pass the current validation gates are exposed for
Spraybot production.

The first workflow pilot covers `slat_back_chair`, `straight_leg_desk`,
`open_cell_shelf`, `legged_solid_headboard_bed`, `door_with_handle`, and
`window_rectangular_frame`. Each pilot category must pass 20-seed automated
checks, contact-sheet review, manual category review, and a downstream Spraybot
read test before the same pattern is applied to the rest of the baseline.

The fork owns mesh generation and generation-side structure data: `spray_part`,
`spray_target`, and optional category-specific priors. Spraybot owns trajectory
rules, PaintDS output, and training-format conversion. The two repositories are
connected through exported compatibility data rather than Python imports.

### Standard validation workflow

For an accepted category, run the 20-seed screen and create contact sheets:

```bash
PYTHONPATH=src .venv/bin/python scripts/spraybot_validate.py \
  outputs_scratch/<category>-validate --category <category_id> --seeds 20
PYTHONPATH=src .venv/bin/python scripts/spraybot_contact_sheets.py \
  outputs_scratch/<category>-validate
```

Then copy [`manual-review-template.md`](manual-review-template.md) into the
validation directory and record the category decision. A category is formally
usable only after generation, automatic checks, contact-sheet review, manual
review, and compatibility export all pass. Use
`scripts/spraybot_compare_batches.py` to compare same-seed batches when a
reproducibility check is needed.
