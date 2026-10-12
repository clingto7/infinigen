# 阶段 1 人工审查 SOP：94 个原生接口候选分类

**日期**：2026-10-12
**输入批次**：radar `outputs_scratch/object-audit-2026-10-12`，本地轻量副本 `~/Documents/tmp/infinigen-object-audit-2026-10-12/`
**产出**：`interface-review-worksheet.csv` 填写完成，并汇总出阶段 2（打标改造）候选清单

## 目的与边界

本阶段只回答四个问题，每个接口一行结论：

1. **是不是工件**——存在真实喷涂任务的实物对象；地形、植物、岩石、随机原语、纯特效网格不是。
2. **是不是随机汇总**——一个函数类内跨多种结构构型（拓扑/遮挡/可达面布局不同）。是则记录应拆分的子结构。
3. **是否与其他接口重复**——生成的结构家族相同（常见于复用同一 `_xxx_geometry` 辅助函数、只改尺寸的 `table_side_rand` 类函数）。
4. **类内结构是否一致**——20 张拼图是否保持同一构型（尺寸/装饰变化允许）。

附带粗判：该结构是否可能有合理喷涂任务（外露表面为主、整件过半面积需喷涂，见 `CONTEXT.md` 喷涂任务定义）。**不做**可达性、膜厚、工艺参数判断——那些是阶段 3 的事。

禁止事项：

- 不给接口写入任何 `spray_part`/`spray_target` 标签（阶段 2 的事）。
- 不把自动筛查通过当作类别资格；技术列只是参考。
- 争议项标 `uncertain` 并写明原因，不强行定论，交共识会。

判定术语以仓库根 `CONTEXT.md` 为准：结构家族、工件类别、工件实例、喷涂任务、可喷表面。

## 数据与工具

### 现成审查材料（本地，无需重跑）

- `~/Documents/tmp/infinigen-object-audit-2026-10-12/interfaces.csv`——技术筛查结果总表。
- `contact_sheets/000_*.jpg … 093_*.jpg`——每接口 20 种子 × 2 视角拼图，本阶段主要审这套。
- `overview_00_09.jpg … overview_80_89.jpg`——按序号分组的总览图，用于横向对比找重复。

看图：`rd --gui <file>`` 或直接 `open <file>`。

全量数据（每种子 `.blend`/PNG/`result.json`，约 2 GB）在 radar 的 `outputs_scratch/object-audit-2026-10-12/`，仅当拼图不足以判断时再取。

### 需要时重跑（本机）

仓库 `~/ws/infinigen-spray`，本机 `.venv` 已就绪：

```bash
# 单接口加 20 个新种子（怀疑类内跨构型时用，--start-seed 换种子段）
./.venv/bin/python scripts/spraybot_validate.py outputs_scratch/recheck \
    --only storage_composite_rand --seeds 20 --start-seed 100

# 重出拼图
./.venv/bin/python scripts/spraybot_contact_sheets.py outputs_scratch/recheck
```

### 源码对照（判汇总/重复必须看）

生成器都在 `src/infinigen2/objects/`。两个识别手法：

- **汇总函数**：函数体内 `pf.control.choice(...)` 在多个**结构构造函数**之间抽样（不是在尺寸/材质参数间抽样）。例如 `chair_dining_rand` 抽 slat/solid 靠背 + 直腿/滚轮底座，是真汇总；`table_side_rand` 若只复用同批桌型改尺寸，是尺寸变体不是汇总。
- **重复接口**：多个注册函数调用同一个 `_xxx_geometry` 辅助函数，或一个函数只是另一个加了默认参数。记 `duplicate_of` 指向保留的那个（通常选名字最通用、参数最全的）。

## 审查流程（每接口约 5 分钟）

1. 打开 `contact_sheets/NNN_名称.jpg`，通看 20 个种子。
2. **非工件**？地形/植物/岩石/原语/特效直接 `not_workpiece`，notes 写一眼依据。
3. **跨构型**？不同种子出现明显不同结构（不是尺寸装饰差异）→ 打开源码确认抽样点，`aggregator_split`，`sub_structures` 列出子结构名（用源码里的构造函数名）。
4. **重复**？与 `overview_*.jpg` 里已审接口横比；疑似则查源码是否共享辅助函数。是则 `duplicate`，`duplicate_of` 填保留接口。
5. **类内一致性**：其余情况检查 20 种子是否同构型。一致性存疑（例如一半种子多个部件）回到第 3 步。
6. **粗判喷涂任务**：整件外露表面是否过半需喷涂、是不是天然需要表面处理的物件（家具/金属件/容器通常是；电子器件外壳、布艺件存疑）。
7. 前面全过 → `candidate`，`family` 填结构家族（如座椅、储物、桌案、门板、容器）。

每行 `notes` 必填一句依据；`coarse_coating_task` 填 `yes/no/unsure`。

## 结论标签（verdict 枚举）

| verdict | 含义 | 必填列 |
| --- | --- | --- |
| `not_workpiece` | 非喷涂工件（地形/植物/岩石/原语/特效） | notes |
| `aggregator_split` | 随机汇总，需拆分成多个结构型 | sub_structures, notes |
| `duplicate` | 与其他接口同结构家族 | duplicate_of, notes |
| `candidate` | 候选类别，进入阶段 2 打标改造 | family, coarse_coating_task |
| `uncertain` | 证据不足或两人分歧 | notes（原因） |

一个接口只能一个 verdict；既是汇总又疑似重复的，优先 `aggregator_split`（拆完再对子结构判重）。

## 技术指标怎么用（interfaces.csv 列）

| 列 | 含义 | 用法 |
| --- | --- | --- |
| `geometry_screen_passed` | 20 种子全生成 + 无退化面 | False 不自动出局，但 retrofit 时要修几何，notes 里记一笔 |
| `near_zero_triangle_fraction_max` | 最大近零三角面比例 | > 0.01 即退化告警，同上 |
| `triangles_min/max` | 三角面数范围 | 数十万级（如地形 50 万）提示非工件尺度；工件类异常高也记一笔 |
| `variation_detected` | 归一化哈希类内有差异 | 全部为 True，弱信号；结构一致性靠人看拼图 |
| `target_area_fraction_*` | 目标面占比 | 原生接口无标签，全空，忽略 |

记住：自动筛查全过 ≠ 类别资格；自动筛查不过 ≠ 出局（几何可修）。

## 两人分工

审查者 A、B 两人，`worksheet` 的 `owner` 列已按序号预填。

| 轮次 | 谁 | 做什么 | 预算 |
| --- | --- | --- | --- |
| 第一轮 独立审查 | A：序号 000–046；B：序号 047–093 | 各自按流程填完自己 47 行的 verdict 与必填列 | 每人约 4–5 小时 |
| 第二轮 交叉复审 | 互换：A 复查 B 的行，B 复查 A 的 | 重点复查 `candidate`、`aggregator_split`、`uncertain` 三类（`not_workpiece`/`duplicate` 抽查即可）；不同意就在 notes 追加异议，不改对方 verdict | 每人约 1.5–2 小时 |
| 第三轮 共识会 | 两人一起 | 只议有异议和 `uncertain` 的行，逐行定稿；把 `uncertain` 归入四类之一或明确挂起原因 | 1–2 小时 |

终稿产出两样东西：

1. 填完的 `interface-review-worksheet.csv`（放 `docs/spraybot/`）。
2. 分类汇总清单：`not_workpiece` 数、`duplicate` 合并组、`aggregator_split` 拆分表（汇总接口 → 子结构列表）、`candidate` 清单（进入阶段 2，按结构家族分组）。此清单就是阶段 2 的改造排期输入。

## 验收自查

- 94 行全部有 verdict，无空行。
- `aggregator_split` 每行有子结构列表；`duplicate` 每行有指向；`candidate` 每行有家族归属。
- 每行 notes 非空。
- 两人分歧全部在共识会解决或明确挂起。
