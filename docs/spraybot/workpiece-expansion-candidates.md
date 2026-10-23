# 工件类别扩充候选

目标是 80 个整件类别。[adopted-workpiece-categories.md](adopted-workpiece-categories.md) 从已审查接口中得到 34 类，本文再补 58 类，合计 92 类，另列 9 个备选。多出的 12 类用来抵消验收不过或并类的损失。计数口径与该文件相同：家具或门窗、可喷涂、只计整件、尺寸和材质差异不另计。

候选只是规划，不代表已经可以生成。每一类都要按 [README.md](README.md) 的标准做少量种子的抽样验收，通过后才计入 80。生成逻辑和各档需要补的接口见 [generation-interface.md](generation-interface.md)。

## 分档

| 档 | 含义 | 主要工作 |
| --- | --- | --- |
| A | 源码里已有函数，但未注册到 `infinigen --list`，也未经过审查 | 审查种子、锁定分支、加喷涂标签 |
| B | 用现有部件组合成新家具 | 写组合函数，处理部件对位和尺寸约束 |
| C | 现有部件做不出来，需要新建几何 | 写新的几何函数，再按 B 档组合 |
| 外部 | Spraybot 仓库已有的类别 | 按同一判据复核 |

工作量按单类估：低指半天以内，中指一到两天，高指三天以上。

## 汇总

| 家族 | 已采用 | A | B | C | 外部 | 合计 |
| --- | --- | --- | --- | --- | --- | --- |
| 坐具 | 7 | 2 | 4 | 10 | 1 | 24 |
| 桌台 | 10 | 0 | 5 | 7 | 0 | 22 |
| 柜架 | 6 | 2 | 7 | 9 | 0 | 24 |
| 床具 | 3 | 0 | 0 | 3 | 0 | 6 |
| 门窗 | 8 | 2 | 0 | 2 | 0 | 12 |
| 其他家具 | 0 | 0 | 0 | 4 | 0 | 4 |
| 合计 | 34 | 6 | 16 | 35 | 1 | 92 |

已采用的 34 类里有 4 类待定（T05、C05、C06、W04），本文 C07 也可能与 C06 重叠。即使这 5 类都并掉，仍有 87 类。

表中“类别 ID”是拟用于 `spraybot.py` 固定入口的名字。

## 坐具

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| S08 | 靠背长椅 | `backed_bench` | A | 多人宽的座面加整排靠背，底座跨度大 | `workpieces/a/seating/backed_bench.py` 调用 `chair.chair_bench_rand`。`back_style` 不锁定，两种靠背都是构型；`spray_tags=True` 时座面和靠背强制硬质材料，前缘下凹置零以免底座横档穿出座面。20 个种子已通过自动检查，待人工复核 | 低 |
| S09 | 储物长凳 | `storage_bench` | A | 无靠背，座面下是开敞格或抽屉柜体 | `workpieces/a/seating/storage_bench.py` 调用 `storage.storage_bench_rand`。门正面已锁掉，开敞和抽屉保留为构型。20 个种子已通过自动检查，待人工复核 | 低 |
| S10 | 方凳 | `square_stool` | B | 方形座板加四腿，无靠背，与圆凳的座面轮廓不同 | `workpieces/b/seating/square_stool.py`。方形 `table_top` 加 `base_straight_rand`。框式两端腿不是四条独立的腿，这里不用。横档有无是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| S11 | 吧凳 | `bar_stool` | B | 座高 0.65–0.8 m，腿间有脚踏横档 | `workpieces/b/seating/bar_stool.py`。圆座或方座是构型。`base_straight_rand` 固定 `stretcher_increment=1`，横档高度约 0.18–0.28 m（相对位置 0 靠近腿顶，1 落在地面）。20 个种子已通过自动检查，待人工复核 | 中 |
| S12 | 吧椅 | `bar_chair` | B | 带靠背的高脚椅，加脚踏横档 | `workpieces/b/seating/bar_chair.py`。复用 `_dining_seat_with_back`，条板或实心靠背是构型，前缘不下凹。高腿和脚踏与 S11 相同。20 个种子已通过自动检查，待人工复核 | 中 |
| S13 | 无靠背长凳 | `backless_bench` | B | 长座板加两端框腿，无靠背 | `workpieces/b/seating/backless_bench.py`。长 `table_top` 加 `base_square_rand(close_edges=True)`，框腿沿长度方向分在两端。20 个种子已通过自动检查，待人工复核 | 低 |
| S14 | 扶手椅 | `armchair` | C | 餐椅两侧有扶手和扶手立柱 | `workpieces/c/seating/armchair.py`。餐椅座靠加直腿，两侧扶手前后有立柱落到座面。条板或实心靠背是构型。20 个种子已通过自动检查，待人工复核 | 中 |
| S15 | 温莎椅 | `windsor_chair` | C | 弧形顶冠加多根细圆棒靠背，腿斜插入座板 | `workpieces/c/seating/windsor_chair.py`。圆座、弧形顶冠和细圆棒。四腿在地面分开、在座下收拢，腿间有横档。圆棒数是构型。20 个种子已通过自动检查，待人工复核 | 高 |
| S16 | 梯背椅 | `ladder_back_chair` | C | 靠背是两根立柱间的多根横档，不是竖条板 | `workpieces/c/seating/ladder_back_chair.py`。立柱标为靠背，横档标为条板。横档数是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| S17 | 摇椅 | `rocking_chair` | C | 腿落在两根弧形摇脚上 | `workpieces/c/seating/rocking_chair.py`。餐椅座靠。四根短柱落在两根弧形摇脚上，不直接着地。20 个种子已通过自动检查，待人工复核 | 中 |
| S18 | 折叠椅 | `folding_chair` | C | X 形交叉腿，座面与腿铰接 | `workpieces/c/seating/folding_chair.py`。每侧两根木条交叉，一根延到靠背。座面是搭在交叉点上方的横条。20 个种子已通过自动检查，待人工复核 | 高 |
| S19 | 悬臂管椅 | `cantilever_chair` | C | 一根连续弯管形成底座和座下支撑，无后腿 | `workpieces/c/seating/cantilever_chair.py`。左右各一根圆管从前脚经后方弯上，再伸到座下并在到位前停下。座靠复用餐椅。20 个种子已通过自动检查，待人工复核 | 中 |
| S20 | 儿童高脚椅 | `high_chair` | C | 高腿外撑，前方有托盘，座面有围挡 | `workpieces/c/seating/high_chair.py`。腿从座下向外撑开。座面前方有托盘，两侧和前方有围挡，前腿间有脚踏。20 个种子已通过自动检查，待人工复核（2026-10-20 修复围挡悬空后重跑） | 高 |
| S21 | 公园长椅 | `park_bench` | C | 座面和靠背由多根横向条木组成，两端是侧框 | `workpieces/c/seating/park_bench.py`。两端侧框含前腿、后倾后腿和扶手。座面和靠背都是沿长度的条木。20 个种子已通过自动检查，待人工复核 | 中 |
| S22 | 躺椅 | `lounge_chair` | C | 长条座面，靠背可倾斜，常为条木 | `workpieces/c/seating/lounge_chair.py`。两侧支架沿座面折上成靠背，倾斜程度是构型。条木横跨在支架上。20 个种子已通过自动检查，待人工复核 | 中 |
| S23 | 踏步凳 | `step_stool` | C | 两到三级踏板，侧板支撑 | `workpieces/c/seating/step_stool.py`。低踏板在前，高踏板靠后，左右侧板从地面托到该级踏板。级数是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| S24 | OpusChair | `opus_chair` | 外部 | 以 Spraybot 中的定义为准 | Spraybot 现有生成与轨迹规则，按同一判据复核 | 低 |

Spraybot 的普通椅基于 Infinigen 1.0 `ChairFactory`，可能与 S01–S03 重复，放在备选里。

## 桌台

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| T11 | 带书架书桌 | `desk_with_hutch` | B | 桌面后方立起一组开敞格架 | `workpieces/b/tables/desk_with_hutch.py`。`desk_tabletop_rand` 加后方 `storage_cell_shelf_rand`，格架深度小于桌深。格数和背板有无是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| T12 | L 形书桌 | `corner_desk` | B | 两块桌面成直角拼接，转角处共用腿 | `workpieces/b/tables/corner_desk.py`。两块 `table_top` 在接缝处相贴、体积不重叠，内角有一条共用腿。20 个种子已通过自动检查，待人工复核 | 中 |
| T13 | 梳妆台 | `dressing_table` | B | 书桌加两侧抽屉，桌面后方竖立镜框 | `workpieces/b/tables/dressing_table.py`。`desk_with_side_storage_rand(front_style="drawer")` 加立式木框。镜面标为 `glass`，不喷涂。镜宽留在两侧柜的空档内。20 个种子已通过自动检查，待人工复核 | 中 |
| T14 | 双层茶几 | `two_tier_coffee_table` | B | 腿间多一块下层搁板 | `workpieces/b/tables/two_tier_coffee_table.py`。直腿或两端框腿是构型，不用独柱。搁板按脚的落点放大，腿或框穿过搁板。20 个种子已通过自动检查，待人工复核 | 低 |
| T15 | 厨房岛台 | `kitchen_island` | B | 柜体组合加外伸台面，一侧可坐 | `workpieces/b/tables/kitchen_island.py`。两只 `storage_composite_rand` 并排，正面同为门或同为抽屉。台面在一侧悬出约 0.3–0.4 m，悬出段下面没有腿。20 个种子已通过自动检查，待人工复核 | 中 |
| T16 | 支架桌 | `trestle_table` | C | 两端是 A 形或 I 形支架，中间一根长横撑 | `workpieces/c/tables/trestle_table.py`。桌面沿长度居中，两端各一架。A 形是底板、两根斜撑、顶枕和中横档；I 形是上下宽梁加中柱。A 与 I 是构型。一根方料横撑沿长度穿过两架。20 个种子已通过自动检查，待人工复核 | 中 |
| T17 | 折叠桌 | `folding_table` | C | 桌面下是可折叠的 X 腿或 U 形管腿 | `workpieces/c/tables/folding_table.py`。X 形和 U 形管是构型。X 在左右两侧沿长度交叉；U 形管在两端，弯在地面。20 个种子已通过自动检查，待人工复核 | 中 |
| T18 | 绘图桌 | `drafting_table` | C | 桌面倾斜，带挡边 | `workpieces/c/tables/drafting_table.py`。前缘低、后缘高，挡边立在低的前缘上。前腿短、后腿长。20 个种子已通过自动检查，待人工复核 | 中 |
| T19 | 工作台 | `workbench` | C | 厚台面、腿间有横撑和下层搁板 | `workpieces/c/tables/workbench.py`。厚台面下有一圈裙板，搁板嵌在四条方腿之间。20 个种子已通过自动检查，待人工复核 | 中 |
| T20 | 发夹腿桌 | `hairpin_leg_table` | C | 每条腿是一根弯成 V 形的金属细杆 | `workpieces/c/tables/hairpin_leg_table.py`。四角各一根细杆，弯头露在桌面下，两脚在地面分开。20 个种子已通过自动检查，待人工复核（2026-10-20 修复腿顶点未达桌面后重跑） | 低 |
| T21 | 弯腿边桌 | `cabriole_leg_table` | C | S 形弯腿，腿上部有裙板 | `workpieces/c/tables/cabriole_leg_table.py`。腿向外弯出膝再收回踝。裙板挂在桌面下、四腿之间。20 个种子已通过自动检查，待人工复核 | 高 |
| T22 | 课桌 | `school_desk` | C | 桌面下有开口书斗，常为金属框加木面 | `workpieces/c/tables/school_desk.py`。书斗挂在桌面下、四腿之间，朝前方开口。前腿间有脚踏。20 个种子已通过自动检查，待人工复核 | 中 |

## 柜架

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| C07 | 带腿柜 | `legged_cabinet` | A | 柜体由 0.15–0.3 m 高的腿托起 | `workpieces/a/cabinets/legged_cabinet.py` 调用 `storage.storage_with_legs_rand`，正面锁成抽屉，避免和待定的 C06 开敞格架重叠。20 个种子已通过自动检查，待人工复核 | 低 |
| C08 | 水槽底柜 | `sink_base_cabinet` | A | 柜顶开口，内部无搁板，正面是门 | `workpieces/a/cabinets/sink_base_cabinet.py` 调用 `storage.storage_sink_base_rand`。单扇或双开门是构型，玻璃芯板已锁掉。20 个种子已通过自动检查，待人工复核 | 低 |
| C09 | 床头柜 | `nightstand` | B | 小柜体，上部抽屉、下部开敞格 | `workpieces/b/cabinets/nightstand.py`。下部开敞格，上部抽屉，避免和 C03 抽屉门柜重叠。抽屉层数是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| C10 | 电视柜 | `tv_stand` | B | 低而宽，开敞格与门或抽屉横向并排 | `workpieces/b/cabinets/tv_stand.py`。两侧开敞格，中间是门或抽屉。中间正面类型是构型。20 个种子已通过自动检查，待人工复核 | 中 |
| C11 | 餐边柜 | `sideboard` | B | 中等高度，抽屉列与门柜列左右并排 | `workpieces/b/cabinets/sideboard.py`。与电视柜共用 `assemble.place_row`。左右哪一侧是抽屉是构型。20 个种子已通过自动检查，待人工复核 | 中 |
| C12 | 带门书柜 | `bookcase_with_doors` | B | 上部开敞书架，下部门柜 | `workpieces/b/cabinets/bookcase_with_doors.py`。门柜在下，开敞格架在上，同深同宽。格数和单扇或双开门是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| C13 | 转角柜 | `corner_cabinet` | B | 平面为 L 形，两段柜体在转角相接 | `workpieces/b/cabinets/corner_cabinet.py`。两段门柜直角相接、体积不重叠，内角有一根封板。20 个种子已通过自动检查，待人工复核 | 中 |
| C14 | 推拉门柜 | `sliding_door_cabinet` | B | 两扇门前后错开，在轨道上滑动，部分重叠 | `workpieces/b/cabinets/sliding_door_cabinet.py`。开敞格柜体前放两扇 `door_body_rand`，前后相差一个门厚，宽度都超过一半。20 个种子已通过自动检查，待人工复核 | 低 |
| C15 | 吊柜 | `wall_cabinet` | B | 无底座，浅柜体，底面外露 | `workpieces/b/cabinets/wall_cabinet.py`。无腿。深度 0.28–0.36 m，底面是柜体底板。单扇或双开门是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| C16 | 衣柜 | `wardrobe` | C | 高柜，内部挂衣杆和顶部搁板，大门扇 | `workpieces/c/cabinets/wardrobe.py`。开敞高柜加顶部搁板和挂衣杆。单扇或双开门是构型。20 个种子已通过自动检查，待人工复核（2026-10-20 修复挂衣杆与搁板悬空后重跑） | 中 |
| C17 | 翻斗鞋柜 | `tilt_out_shoe_cabinet` | C | 正面是向外翻出的斗，内部是斜置隔板 | `workpieces/c/cabinets/tilt_out_shoe_cabinet.py`。每个斗绕下沿向前翻，斗里有一块更斜的隔板。斗数是构型。20 个种子已通过自动检查，待人工复核 | 高 |
| C18 | 百叶门柜 | `louvered_cabinet` | C | 门芯由多根斜向百叶条组成 | `workpieces/c/cabinets/louvered_cabinet.py`。开敞柜体前是百叶门，不是平板门。门扇数是构型。20 个种子已通过自动检查，待人工复核 | 中 |
| C19 | 梯形架 | `ladder_shelf` | C | 两根斜立柱靠墙，搁板由下往上变窄 | `workpieces/c/cabinets/ladder_shelf.py`。立柱下端向前、上端靠后。搁板数是构型，上层更窄。20 个种子已通过自动检查，待人工复核 | 中 |
| C20 | 三角角架 | `corner_shelf` | C | 平面为三角形的多层搁板，放墙角 | `workpieces/c/cabinets/corner_shelf.py`。直角贴墙角，斜边朝向室内。层数是构型，角上有一根立柱。20 个种子已通过自动检查，待人工复核 | 低 |
| C21 | 博古架 | `staggered_display_shelf` | C | 格子大小不一、错位排列 | `workpieces/c/cabinets/staggered_display_shelf.py`。上下两段的竖隔错开，横隔高度不均匀。20 个种子已通过自动检查，待人工复核 | 中 |
| C22 | 格子酒架 | `wine_rack` | C | 菱形或 X 形交叉隔板 | `workpieces/c/cabinets/wine_rack.py`。外框里每一格是一对交叉斜板。格数是构型。20 个种子已通过自动检查，待人工复核 | 中 |
| C23 | 金属货架 | `metal_shelving` | C | 四根角钢立柱加多层薄板，无侧板和背板 | `workpieces/c/cabinets/metal_shelving.py`。四角是 L 形立柱，薄板只搭在立柱上。层数是构型。20 个种子已通过自动检查，待人工复核 | 低 |
| C24 | 带盖储物箱 | `storage_chest` | C | 无腿或矮脚箱体，顶部是盖板 | `workpieces/c/cabinets/storage_chest.py`。箱口敞开，盖板略大于箱口。有没有矮脚是构型。20 个种子已通过自动检查，待人工复核 | 低 |

Infinigen 1.0 有 `TVStandFactory`、`TriangleShelfFactory`、`KitchenIslandFactory`、`SimpleBookcaseFactory`、`LargeShelfFactory` 等工厂，可作为 C10、C20、T15、C12 的参考。本机没有 1.0 源码，具体工厂名和结构需对照 1.0 仓库核实。

## 床具

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| B04 | 婴儿床 | `crib` | C | 四周都是竖栏，床面离地较高 | `workpieces/c/beds/crib.py`。四根角柱之间四面都是竖栏，床板高于普通床。20 个种子已通过自动检查，待人工复核（2026-10-20 修复床板悬空后重跑） | 中 |
| B05 | 上下铺 | `bunk_bed` | C | 两层床面由四根立柱连接，带爬梯和护栏 | `workpieces/c/beds/bunk_bed.py`。四根立柱连两层床板。爬梯在床尾，上层长边有护栏。20 个种子已通过自动检查，待人工复核（2026-10-20 修复爬梯与护栏悬空后重跑） | 高 |
| B06 | 四柱床 | `four_poster_bed` | C | 四角立柱高出床头，顶部可有框 | `workpieces/c/beds/four_poster_bed.py`。硬质床头、床尾、侧梁和床板。四根立柱升过床头，顶部连成框。20 个种子已通过自动检查，待人工复核 | 中 |

## 其他家具

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| O01 | 屏风 | `folding_screen` | C | 三到四扇框板铰接，呈折线放置 | `workpieces/c/other/folding_screen.py` 复用 `door_body_rand` 做框板，按折线铰接。20 个种子已通过自动检查，待人工复核 | 低 |
| O02 | 衣帽架 | `coat_rack` | C | 单根立柱，底部三到四只脚，顶部挂钩 | `workpieces/c/other/coat_rack.py` 新建立柱、撑脚和挂钩。20 个种子已通过自动检查，待人工复核 | 低 |
| O03 | 花架 | `plant_stand` | C | 多层阶梯式小台面 | `workpieces/c/other/plant_stand.py` 新建三级阶梯台面。20 个种子已通过自动检查，待人工复核 | 低 |
| O04 | 餐车 | `serving_cart` | C | 金属或木框，两到三层托盘，带脚轮 | `workpieces/c/other/serving_cart.py` 新建托盘、立柱、把手和脚轮。20 个种子已通过自动检查，待人工复核 | 中 |

## 门窗

| 编号 | 类别 | 类别 ID | 档 | 结构判据 | 来源或实现路径 | 工作量 |
| --- | --- | --- | --- | --- | --- | --- |
| D05 | 拱顶门 | `arched_door` | A | 门扇顶边是圆弧，门内为窗格棂条 | `workpieces/a/openings/arched_door.py` 调用 `door.door_glass_from_profile_rand` 配 `window.top_rounded_profile_rand`，`include_glass_pane=False`。20 个种子已通过自动检查，待人工复核 | 低 |
| D06 | 百叶门 | `louvered_door` | A | 门芯由多根斜向百叶条组成 | `workpieces/a/openings/louvered_door.py` 调用 `door_composite_rand(body_style="glass_grid", shutter=True)`，玻璃不生成。20 个种子已通过自动检查，待人工复核 | 低 |
| D07 | 门套 | `door_casing` | C | 贴墙的 U 形三边框，截面为线脚 | `workpieces/c/openings/door_casing.py` 新建墙板加内凸线脚的三边框。20 个种子已通过自动检查，待人工复核 | 低 |
| W05 | 窗套 | `window_casing` | C | 四边框加下方外伸的窗台板 | `workpieces/c/openings/window_casing.py` 新建四边框和外伸窗台。20 个种子已通过自动检查，待人工复核 | 低 |

D06 与 C18 百叶门柜都用百叶条，可以共用 `_window_shutter`，C18 的工作量因此可降为低。

## 备选（不计入上面的 92 类）

| 候选 | 说明 |
| --- | --- |
| Spraybot 普通椅 | 可能与 S01–S03 重复，需复核 |
| 文件柜 | 窄而高的全抽屉柜，金属。与 C04 的区别主要在比例 |
| 浴室柜 | C08 加台面和盆，盆不喷涂。可与 015 合并考虑 |
| 玄关桌 | 窄长桌面加细腿，可带一排薄抽屉。可能与 T05 重叠 |
| 厨房高柜 | 上下两段门柜叠放。可能与 C05 重叠 |
| 三腿凳 | 三条斜腿加圆座。需要 `furniture_bases` 支持三腿 |
| 带扶手办公椅 | S05 加扶手，扶手件与 S14 共用 |
| 玻璃门展示柜 | C02 中玻璃芯板占多数的构型。喷涂面主要是窄框 |
| 画框 | 081。如果把墙面装饰视为家具，可以计入 |

## 建议的实现顺序

1. 先做已采用清单中“需拆出”和“待定”的类别，以及 A 档，共 33 类。这两部分只需锁定分支、加喷涂标签，可以最快验证注册表和验收流程。
2. 再做 B 档。B 档能检验组合函数和统一部件编号的约定。
3. 最后做 C 档。先做共用件多的：X 腿框架（S18、T17）、扫掠管材（S19、T20、C23、O04）、条木与竖栏（S16、S21、S22、B04）。共用件做好后，其余 C 档的成本会下降。
