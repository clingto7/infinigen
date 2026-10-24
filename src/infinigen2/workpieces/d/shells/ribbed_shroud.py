"""G24 曲面罩壳带纵向肋。

沿 Y 的半圆柱壳，开口朝下扣在地面上。内壁掏空，外壁沿母线贴 3 到 6
条纵向宽肋。侧面开窗是构型。
"""

import math

import bmesh
import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    box,
    cut,
    cylinder,
    finish,
    hard_material,
    register,
    rest_on_ground,
    tag,
)

_ALONG_Y = (math.pi * 0.5, 0.0, 0.0)


def _drop_slivers(obj: pf.MeshObject) -> None:
    data = obj.item().data
    bm = bmesh.new()
    try:
        bm.from_mesh(data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bad = [face for face in bm.faces if face.calc_area() < 1e-8]
        if bad:
            bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
            loose = [edge for edge in bm.edges if not edge.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="EDGES")
        bm.to_mesh(data)
        data.update()
    finally:
        bm.free()


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    outer_r = pf.random.uniform(rng_size, 0.12, 0.20)
    wall = min(pf.random.uniform(rng_size, 0.012, 0.022), outer_r * 0.22)
    inner_r = outer_r - wall
    length = pf.random.uniform(rng_size, 0.28, 0.48)
    n_rib = int(pf.random.randint(rng_size, 3, 7))
    rib_t = pf.random.uniform(rng_size, 0.016, 0.030)
    rib_h = pf.random.uniform(rng_size, 0.018, 0.036)
    window = pf.control.choice(rng_style, [(False, 1.0), (True, 1.3)])

    shell = cylinder(outer_r, length, (0.0, 0.0, 0.0), rotation=_ALONG_Y, vertices=48)
    cut(
        shell,
        cylinder(inner_r, length + 0.08, (0.0, 0.0, 0.0), rotation=_ALONG_Y, vertices=48),
        what="shroud bore",
    )
    # Keep the cut off the vertex equator at z = 0 so the boolean does not
    # leave sliver triangles.
    cut_h = outer_r + 0.06
    cut(
        shell,
        box(
            (outer_r * 2.4, length + 0.08, cut_h),
            (0.0, 0.0, 0.004 - cut_h * 0.5),
        ),
        what="half shroud",
    )
    if window:
        win_w = outer_r * pf.random.uniform(rng_style, 0.55, 0.90)
        win_l = length * pf.random.uniform(rng_style, 0.28, 0.50)
        side = 1.0 if pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)]) else -1.0
        cut(
            shell,
            box(
                (outer_r * 0.70, win_l, win_w),
                (side * outer_r * 0.55, 0.0, outer_r * 0.35),
            ),
            what="shroud window",
        )
    _drop_slivers(shell)

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    lo = math.radians(25.0)
    hi = math.radians(155.0)
    for index in range(n_rib):
        t = 0.5 if n_rib == 1 else index / (n_rib - 1)
        yaw = lo + t * (hi - lo)
        radial = (math.cos(yaw), 0.0, math.sin(yaw))
        center_r = outer_r + rib_h * 0.5 - 0.003
        parts.append(tag(
            box(
                (rib_t, length * 0.92, rib_h + 0.006),
                (radial[0] * center_r, 0.0, radial[2] * center_r),
                rotation=aim_z(radial),
            ),
            material,
            "rib",
        ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="ribbed_shroud",
    code="G24",
    family="壳体",
    criterion="半圆柱罩壳外壁有纵向宽肋，侧面可开窗",
    build=build,
    allowed_parts=frozenset({"shell", "rib"}),
))
