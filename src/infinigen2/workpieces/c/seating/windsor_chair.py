"""S15 温莎椅。

结构判据：弧形顶冠加多根细圆棒靠背，腿斜插入座板。
圆棒从座板后缘插到弧形顶冠。四条腿在地面分开、在座板下收拢。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    chain,
    join_tagged,
    point_at_z,
    register,
    rod,
    round_seat,
    vertex_bounds,
)


def _bow(count: int, half: float) -> list[float]:
    return [half * (-1.0 + 2.0 * i / (count - 1)) for i in range(count)]


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    seat_h = pf.random.uniform(rng_size, 0.44, 0.48)
    seat_r = pf.random.uniform(rng_size, 0.42, 0.48)
    back_h = pf.random.uniform(rng_size, 0.34, 0.44)
    n_spindles = pf.control.choice(rng_size, [(7, 1.0), (9, 1.0), (11, 1.0)])
    material = hard_material(rng_mat)
    seat = round_seat(material, seat_r, 0.028, seat_h)
    underside = vertex_bounds(seat)[4]
    half = 0.16
    ys = _bow(int(n_spindles), half)
    tops = []
    parts = [seat]
    for y in ys:
        bow = 1.0 - (y / half) ** 2
        bottom = (-0.02 + 0.04 * bow, y, seat_h - 0.012)
        top = (-0.10 - 0.05 * bow, y * 1.15, seat_h + back_h + 0.035 * bow)
        tops.append(top)
        parts.append(rod(bottom, top, 0.0075, material, "slat", resolution=6))
    parts.extend(chain(tops, material, "back", radius=0.012, overlap=0.012))
    seat_pts = {
        "fl": (0.07, 0.07, underside + 0.015),
        "fr": (0.07, -0.07, underside + 0.015),
        "bl": (-0.05, 0.07, underside + 0.015),
        "br": (-0.05, -0.07, underside + 0.015),
    }
    floor_pts = {
        "fl": (0.20, 0.18, 0.014),
        "fr": (0.20, -0.18, 0.014),
        "bl": (-0.18, 0.17, 0.014),
        "br": (-0.18, -0.17, 0.014),
    }
    for key in seat_pts:
        parts.append(rod(floor_pts[key], seat_pts[key], 0.014, material, "leg_base"))
    z_rail = 0.16
    rail = {key: point_at_z(floor_pts[key], seat_pts[key], z_rail) for key in seat_pts}
    parts.append(rod(rail["fl"], rail["bl"], 0.010, material, "leg_base"))
    parts.append(rod(rail["fr"], rail["br"], 0.010, material, "leg_base"))
    parts.append(rod(rail["bl"], rail["br"], 0.010, material, "leg_base"))
    return join_tagged(parts)


register(Category(
    category_id="windsor_chair",
    code="S15",
    family="坐具",
    criterion="弧形顶冠加多根细圆棒靠背，腿斜插入座板",
    build=build,
    allowed_parts=frozenset({"seat", "back", "slat", "leg_base"}),
))
