# 复杂工件可用清单（人工审查结果）

日期：2026-10-24。审查对象是 [Infinigen_复杂工件_30类生成清单.md](Infinigen_复杂工件_30类生成清单.md) 里的 G01–G30。

本文只记录人工审查的判定结果，不重复 30 类的完整设计说明。设计说明以原清单为准，实现与判据以
`src/infinigen2/workpieces/d/shells/` 为准。

## 结论

- 30 类中 **22 类可用**，8 类经人工审查剔除。
- 审查依据是五个验证批次的 20 种子拼图（`contact_sheets/`）和既有 `manual-review.md`，不是自动标签检查。
- 可用指：可以生成、20 个种子保持同一结构类别、类内有可见几何差异、外露面全部是喷涂目标、
  部件标签与共享表一致。**不等于**轨迹、机器人可达性或涂层质量已经验收。

| 批次 | 类别数 | 可用 | 剔除 |
| --- | --- | --- | --- |
| shells（G01–G06） | 6 | 4 | 2 |
| openings（G07–G12） | 6 | 5 | 1 |
| pipes（G13–G18） | 6 | 6 | 0 |
| ribs（G19–G24） | 6 | 3 | 3 |
| compound（G25–G30） | 6 | 4 | 2 |
| 合计 | 30 | **22** | 8 |

## 一、剔除的 8 类

下表只记录判定，不写具体剔除理由。理由由审查者按 [manual-review-template.md](manual-review-template.md)
补进对应批次的 `manual-review.md`，避免用推测补空。表中的 `outputs_scratch` 路径和拼图都是本机
产物，被 `.gitignore` 排除，不进仓库。

| 编号 | 类别 | 类别 ID | 批次目录 | 拼图 |
| --- | --- | --- | --- | --- |
| G03 | 球窝方壳 | `spherical_pocket` | `outputs_scratch/shells-validate-2026-10-20` | `contact_sheets/002_spherical_pocket.jpg` |
| G05 | U 型长槽护罩 | `u_groove_shroud` | `outputs_scratch/shells-validate-2026-10-20` | `contact_sheets/004_u_groove_shroud.jpg` |
| G10 | 大开窗隔板 | `windowed_panel` | `outputs_scratch/openings-validate-2026-10-20` | `contact_sheets/003_windowed_panel.jpg` |
| G19 | 十字加强筋底座 | `ribbed_base` | `outputs_scratch/ribs-validate-2026-10-20` | `contact_sheets/000_ribbed_base.jpg` |
| G21 | 错位多凸台盒体 | `offset_boss_box` | `outputs_scratch/ribs-validate-2026-10-20` | `contact_sheets/002_offset_boss_box.jpg` |
| G22 | 斜撑门式支座 | `portal_brace` | `outputs_scratch/ribs-validate-2026-10-20` | `contact_sheets/003_portal_brace.jpg` |
| G28 | 三叶复合鼓体 | `trefoil_body` | `outputs_scratch/compound-validate-2026-10-20` | `contact_sheets/003_trefoil_body.jpg` |
| G29 | 扭曲弧板开窗体 | `twisted_arc_panel` | `outputs_scratch/compound-validate-2026-10-20` | `contact_sheets/004_twisted_arc_panel.jpg` |

这 8 类的模块已从 `d/shells/` 删除，`d/shells/__init__.py` 里的导入也已去掉，
`workpieces.generate(<类别 ID>, ...)` 现在会报未知类别。剔除的含义是**不再计入可用复杂工件集合**，
也从注册表移除。若要恢复某一类，需从 git 历史取回模块并重新登记。

## 二、可用的 22 类

部件列是 `spray_part` 实际出现过的组合；所有类的 `spray_target` 覆盖率为 1，没有玻璃、布艺或
陶瓷这类非目标面。

### 凹腔与开口壳体

| 编号 | 类别 | 类别 ID | 结构判据 | 部件 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| G01 | 偏心月牙圆筒 | `eccentric_crescent` | 偏心内孔的圆筒，薄壁一侧有轴向开口，可带端面盘 | `shell` / `shell`+`flange` | P0 |
| G02 | 离心风机蜗壳原型 | `volute_housing` | 螺旋扫掠壳体，侧向矩形出口，圆孔入口带法兰 | `shell`+`flange` | P1 |
| G04 | 阶梯凹腔箱体 | `stepped_cavity` | 顶面多层台阶凹腔，腔口可偏，底面留壁 | `shell` | P0 |
| G06 | 侧窗空心圆筒 | `windowed_cylinder` | 空心圆筒带侧向矩形窗，可在端面加环 | `shell` / `shell`+`flange` | P0 |

### 开孔、切槽与穿透结构

| 编号 | 类别 | 类别 ID | 结构判据 | 部件 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| G07 | 拱洞桥块 | `arched_bridge` | 厚块底部为宽拱洞，两侧留桥墩，可加顶脊 | `shell` / `shell`+`rib` | P0 |
| G08 | 斜贯穿孔厚块 | `inclined_bore` | 厚板有倾斜贯穿圆孔，可在顶面加一条浅槽 | `shell` | P0 |
| G09 | 正交双孔块 | `crossing_bores` | 厚块内两根大圆孔斜交或正交，并在块内交汇 | `shell` | P1 |
| G11 | 缺口环形法兰 | `notched_flange` | 带中心孔的扁环切去一段扇区，缺口对面有局部凸缘 | `shell`+`flange` | P0 |
| G12 | 宽螺旋槽圆柱 | `helical_groove` | 粗圆柱表面有不到两圈的宽螺旋槽，两端留余量 | `shell` | P2 |

### 管道、分支与变截面

| 编号 | 类别 | 类别 ID | 结构判据 | 部件 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| G13 | 大弯头带法兰 | `flanged_elbow` | 圆弧弯管两端带法兰，内通道贯通 | `shell`+`flange` | P0 |
| G14 | T 型三通管体 | `tee_pipe` | 正交三通管，主管与支管在内部连通，可加三端法兰 | `shell` / `shell`+`flange` | P0 |
| G15 | Y 型分流管体 | `wye_pipe` | Y 形三通，两支管可不等径，节点可圆滑，内腔贯通 | `shell` | P0 |
| G16 | 十字四通管壳 | `cross_pipe` | 两根粗管相交成四通，可错层，可加端环 | `shell` / `shell`+`flange` | P1 |
| G17 | 偏心变径圆管 | `eccentric_reducer` | 大小圆口偏心过渡的变径管，两端带法兰 | `shell`+`flange` | P1 |
| G18 | 圆转方过渡风道 | `circle_rect_duct` | 圆口到圆角方口的过渡风道，两端带法兰，可偏心 | `shell`+`flange` | P1 |

### 凸台、加强筋与支撑结构

| 编号 | 类别 | 类别 ID | 结构判据 | 部件 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| G20 | 辐射肋圆筒壳 | `radial_rib_shell` | 短粗圆筒顶面大口，外壁有径向厚肋，可加顶环 | `shell`+`rib`，可加 `flange` | P0 |
| G23 | 偏心阶梯柱座 | `stepped_column` | 多层偏心圆柱堆叠，侧面有扇形缺口或竖槽 | `shell` | P0 |
| G24 | 曲面罩壳带纵向肋 | `ribbed_shroud` | 半圆柱罩壳外壁有纵向宽肋，侧面可开窗 | `shell`+`rib` | P1 |

### 复合异形与组合原型

| 编号 | 类别 | 类别 ID | 结构判据 | 部件 | 优先级 |
| --- | --- | --- | --- | --- | --- |
| G25 | 双腔连通鼓形壳 | `connected_drums` | 两个鼓形腔由短粗管连通，两端各有大凹口 | `shell` | P1 |
| G26 | 球筒复合阀壳 | `valve_housing` | 球体加两到三段端口，顶部凸台，底部有座 | `shell`+`boss` | P0 |
| G27 | 开窗穹顶防护罩 | `windowed_dome` | 开底球冠壳，侧面有宽窗，底边有加强环 | `shell`+`flange` | P1 |
| G30 | 综合异形泵体原型 | `pump_body` | 圆角盒并鼓腔和侧管，再开大口和槽，带底肋 | `shell`+`rib` | P1 |

## 三、可用类的实测范围

20 个种子、每类 20 件，共 440 件。数据来自各批次 `review.csv` 与种子目录的 `result.json`。

| 类别 ID | 三角形数 | 包围盒最大边 / m | 可喷表面积 / m² | 近零面积三角形占比 |
| --- | --- | --- | --- | --- |
| `eccentric_crescent` | 370–582 | 0.32–0.46 | 0.56–1.33 | ≤0.27% |
| `volute_housing` | 1228–1380 | 0.45–0.66 | 0.57–1.07 | 0 |
| `stepped_cavity` | 44–60 | 0.31–0.46 | 0.33–0.59 | 0 |
| `windowed_cylinder` | 492–1276 | 0.27–0.51 | 0.41–1.21 | 0 |
| `arched_bridge` | 100–144 | 0.33–0.49 | 0.32–0.69 | 0 |
| `inclined_bore` | 176–196 | 0.40–0.56 | 0.44–0.66 | ≤0.56% |
| `crossing_bores` | 528–624 | 0.41–0.50 | 1.04–1.50 | ≤0.34% |
| `notched_flange` | 352–416 | 0.36–0.54 | 0.14–0.39 | 0 |
| `helical_groove` | 608–2068 | 0.31–0.47 | 0.40–0.64 | 0 |
| `flanged_elbow` | 4336–4676 | 0.26–0.55 | 0.27–0.75 | 0 |
| `tee_pipe` | 710–1756 | 0.36–0.56 | 0.37–0.83 | ≤0.13% |
| `wye_pipe` | 1298–2116 | 0.37–0.56 | 0.33–0.54 | 0 |
| `cross_pipe` | 944–1976 | 0.33–0.50 | 0.40–0.78 | ≤0.10% |
| `eccentric_reducer` | 2688（恒定） | 0.23–0.38 | 0.28–0.50 | 0 |
| `circle_rect_duct` | 2848（恒定） | 0.27–0.39 | 0.42–0.61 | 0 |
| `radial_rib_shell` | 396–732 | 0.28–0.39 | 0.29–0.71 | 0 |
| `stepped_column` | 232–606 | 0.19–0.29 | 0.12–0.32 | 0 |
| `ribbed_shroud` | 232–324 | 0.30–0.48 | 0.36–0.78 | 0 |
| `connected_drums` | 3373–4116 | 0.32–0.46 | 0.24–0.44 | 0 |
| `valve_housing` | 2435–2685 | 0.28–0.43 | 0.31–0.57 | 0 |
| `windowed_dome` | 1408–1664 | 0.40–0.51 | 0.43–0.74 | ≤0.14% |
| `pump_body` | 912–1026 | 0.31–0.43 | 0.41–0.61 | ≤0.10% |

`stepped_cavity` 的 44–60 个三角形是直角台阶腔本身的面数，不是简化错误。`eccentric_reducer`
和 `circle_rect_duct` 的三角形数恒定，差异只在顶点位置。

可喷表面积最小的是 `stepped_column`（0.12–0.32 m²）和 `notched_flange`（0.14–0.39 m²）。
它们仍算可用，但单件可用喷幅小，排产时要比其它类多取件或单独设姿态。

## 四、可用类的边界

逐类边界摘自各批次 `manual-review.md`，本节只是汇总，不新增判定。这些是使用时的已知限制，
不是缺陷。

- **G01 `eccentric_crescent`**：偏心的壁厚差在斜视图里不如开口显眼。种子 12、18 有约 0.27% 的
  近零面积三角形。
- **G02 `volute_housing`**：可喷外露面积是边界情况，螺旋与出口足够，入口很小。种子 0 的 `view_1`
  里入口更像内端上的小凸起，圆孔与法兰环在审查图里不易分开；网格中法兰面存在。轨迹若依赖入口，
  需单独确认孔径。
- **G04 `stepped_cavity`**：几何是直角盒，层数 2 或 3，面数为 18 的 11 个种子、24 的 9 个种子。
- **G06 `windowed_cylinder`**：端环可有可无，6 个种子没有环；单环 92 面，双环 184 面。
- **G07 `arched_bridge`**：10/20 带顶脊，顶脊是构型，不算另一类。
- **G08 `inclined_bore`**：单张斜视图里孔口接近正圆，倾角要对照两面开口的位置。种子 7、10 的
  近零面积三角形约 0.56%。
- **G09 `crossing_bores`**：夹角离直角不远，斜交不会拉得很开。交汇偏内时两个开口分处不同面，
  要做到孔里看。从顶面向下打射线，20 个种子顶面都没有被打穿。种子 15 约 0.35%。
- **G11 `notched_flange`**：缺口两侧接近平行，不是严格径向扇形边；凸缘是贴在外圆上的局部加厚。
- **G12 `helical_groove`**：槽截面是扫掠宽凹槽，不是矩形牙；圈数少的种子只绕过圆柱一部分。
- **G13 `flanged_elbow`**：弯管是扫掠圆截面，不是精确圆环扇段。一只法兰落地，另一口侧向。
- **G14 `tee_pipe`**：法兰是构型，10/20 三口带法兰。支管内孔停在主管腔里，没有从底面穿出。
  种子 9 约 0.13%。
- **G15 `wye_pipe`**：带倾角支管会在主管侧面留一块相贯凸起，例如种子 4、17。硬连接约 1300 面，
  圆滑节点约 2000 面。
- **G16 `cross_pipe`**：错层时某个角度看像斜插三通，另一面仍能看到第四个口，例如种子 2。
  夹角离直角不远。
- **G17 `eccentric_reducer`**：小口几乎贴在大口一侧，偏心比同心圆锥更明显。侧弯是叠加在偏心上，
  不是单独弯管。
- **G18 `circle_rect_duct`**：截面按高度线性混合，不是曲率连续的 Loft。方口偏心时风道看起来像斜的。
- **G20 `radial_rib_shell`**：端环是构型，7/20 有顶环。肋不一定从底面贴到顶口，起止高度会变。
- **G23 `stepped_column`**：偏心有时较弱，俯视接近同心。竖槽不一定切穿每一层。
- **G24 `ribbed_shroud`**：开窗是构型；窗开在侧面时附近肋仍贴在外壁上。
- **G25 `connected_drums`**：单个视角往往只能看清一只鼓的凹口，另一只在背面。腰管在两鼓重叠
  较多时会缩成一圈领，例如种子 9。
- **G26 `valve_housing`**：顶凸台实心不挖孔；端口内孔停在球腔里，没有从对面穿出。
- **G27 `windowed_dome`**：三扇窗时每扇更窄，例如种子 16。个别种子近零面积三角形约 0.14%。
- **G30 `pump_body`**：底肋贴在盒下缘，等距图里不如鼓口和槽醒目。槽有时切到侧管，管口变成斜切口，
  例如种子 2、4、16。

## 五、未验证项

以下三项不在本次审查范围内，也未被任何自动检查覆盖，不得因为它们出现在本文就算通过：

1. **喷涂轨迹**：可喷面积占比为 1 只说明标签，不说明喷枪能覆盖。
2. **机器人可达性**：G11 内外环壁、G09 孔交汇处、G13 弯管内壁这类区域需要可达性分析。
3. **涂层质量**：没有做喷雾沉积或膜厚仿真。

另外，[repository-status.md](repository-status.md) 记下的 2026-10-23 独立几何复核结论仍然成立：
按“组合度、凹腔遮挡、尺度、目标面语义、特征尺寸、网格质量”六项实测，这批工件多数只是
“一个规整母形加一次差集”。本次人工审查剔除 8 类后，剩下的 22 类在组合度、盲腔遮挡和特征
尺度上没有变化。该复核记录引用的 `complex-workpiece-gap-analysis.md` 当前不在工作区里，
本文不转述其中的 G31–G52 建议。

## 六、复核方式

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe scripts\spraybot_validate.py outputs_scratch\<批次>-validate --category <类别 ID> --seeds 20
.venv\Scripts\python.exe scripts\spraybot_contact_sheets.py outputs_scratch\<批次>-validate
```

单件抽查：

```powershell
.venv\Scripts\python.exe scripts\spraybot_probe.py <类别 ID> 0 outputs_scratch\probe-<类别 ID>
```

## 相关文档

| 文档 | 用途 |
| --- | --- |
| [Infinigen_复杂工件_30类生成清单.md](Infinigen_复杂工件_30类生成清单.md) | G01–G30 的原始设计与参数约定 |
| [workpiece-expansion-candidates.md](workpiece-expansion-candidates.md) | 新工件的结构判据、实现路径和复核状态 |
| [manual-review-template.md](manual-review-template.md) | 人工审查记录模板 |
| [repository-status.md](repository-status.md) | 两套工件的总状态 |
