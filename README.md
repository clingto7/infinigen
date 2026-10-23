# infinigen-spray

[Infinigen](https://github.com/princeton-vl/infinigen) 的 fork（基线 `a0d1a0dd`，v2.0.0a3），为 [Spraybot](https://github.com/liang-zijian/Spraybot) 喷涂轨迹研究提供程序化工件生成。目标：**80+ 个结构上明显不同的可喷涂工件类别**（不限于家具）。

职责边界：本 fork 只负责**几何与生成侧结构信息**；喷涂轨迹、数据转换和模型留在 Spraybot 仓库，双方通过跨家族样本核对接口。

## 当前状态（2026-10）

- 单接口自动验证流水线已就绪，并对全部 94 个原生 `Object` 接口跑完 20 种子筛查：1880/1880 生成成功，76 个过几何筛查、18 个有退化面告警；原生接口均无喷涂标签（待改造状态）。
- 当前登记 21 个合并后的基线接口和 54 个扩展接口，共 75 个生成接口。基线接口通过
  `infinigen2.objects.spraybot.generate_workpiece`，扩展接口通过
  `infinigen2.workpieces.generate` 调用；扩展接口的自动复核与人工审查状态见
  [docs/spraybot/repository-status.md](docs/spraybot/repository-status.md)。
- 扩展接口的前身 57 类已完成 20 种子自动检查和兼容导出探针；2026-10-20 修复
  5 类悬空结构并改进审查图渲染后全量重跑，完整拼图在
  `outputs_scratch/review-expansion-20seed-20261020/contact_sheets/`，
  连通岛审查用 `scripts/spraybot_island_audit.py`。随后按实现合并和注册复核，当前扩展
  接口为 54 类；新合并接口另做了 20 种子检查。
- **当前阶段：阶段 1 人工接口审查**（候选分类），SOP 见 [docs/spraybot/manual-review-sop.md](docs/spraybot/manual-review-sop.md)。后续阶段见 [docs/spraybot/README.md](docs/spraybot/README.md) 的探索顺序。

## 文档

- [CONTEXT.md](CONTEXT.md)——工件类别、结构家族、喷涂任务等术语标准（类别判定以此为准）。
- [docs/spraybot/README.md](docs/spraybot/README.md)——项目范围、来源职责、已核实的生成方式、后续探索顺序。
- [docs/spraybot/manual-review-sop.md](docs/spraybot/manual-review-sop.md)——阶段 1 人工审查 SOP，配套工作表 [docs/spraybot/interface-review-worksheet.csv](docs/spraybot/interface-review-worksheet.csv)。

## 仓库结构

```
src/infinigen2/objects/spraybot.py   # 合并后的基线工件入口，21 个类别
src/infinigen2/workpieces/           # 扩展工件入口与 54 个类别注册
src/infinigen2/objects/*.py          # chair/door/storage/vase 支持 spray_tags=True 显式打标
scripts/spraybot_validate.py         # 批量验证：断点续跑、超时、summary/review/interfaces 报表
scripts/spraybot_validate_one.py     # 单种子 worker：修改器后网格度量、标签检查、双视角 PNG、.blend
scripts/spraybot_contact_sheets.py   # 每类拼图
scripts/spraybot_probe.py            # 紧凑 NPZ 探针（mesh + 标签 + 统计）
scripts/spraybot_batch.py            # 早期批量探针（仅覆盖最初 3 类）
```

生成侧标签约定：`spray_part`（FACE/INT，部件类型）与 `spray_target`（FACE/BOOLEAN，候选喷涂面）。两者是**生成侧候选信息**，不构成可达性或工艺结论。

## 快速开始

Python 3.11：

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/infinigen --list Object   # 列出 94 个原生 Object 接口
```

验证流水线：

```bash
# 原生接口或固定工件，各 20 种子（可断点续跑）
.venv/bin/python scripts/spraybot_validate.py outputs_scratch/my-audit \
    --category backed_bench --seeds 20

# 只跑部分接口 / 换种子段
.venv/bin/python scripts/spraybot_validate.py outputs_scratch/recheck \
    --only storage_composite_rand --seeds 20 --start-seed 100

# 汇总拼图
.venv/bin/python scripts/spraybot_contact_sheets.py outputs_scratch/my-audit
```

输出：每种子 `model.blend`、两张审查 PNG、`result.json`；每批 `summary.json`、`review.csv`、`interfaces.csv`。

## 与上游的关系

基于 [princeton-vl/infinigen](https://github.com/princeton-vl/infinigen) `a0d1a0dd`（v2.0.0a3）。上游的场景生成、地形等能力保持可用；本 fork 的改动集中在 `src/infinigen2/objects/` 的喷涂标签扩展、`scripts/spraybot_*` 工具与 `docs/spraybot/` 文档。上游的完整安装与场景生成文档见[上游仓库](https://github.com/princeton-vl/infinigen)与其[在线文档](https://infinigen.cs.princeton.edu/docs/latest/index.html)。许可证沿用 BSD-3-Clause。
