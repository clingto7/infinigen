"""G26 球筒复合阀壳。

主球体并入 2 到 3 段圆柱端口，端口内孔打进球腔但不穿对面。
顶部加粗凸台，底部加可偏移的座盒。端口夹角在水平面内变化。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    box,
    cut,
    cylinder,
    finish,
    fuse,
    hard_material,
    register,
    rest_on_ground,
    sphere,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    r_ball = pf.random.uniform(rng_size, 0.085, 0.130)
    wall = min(pf.random.uniform(rng_size, 0.010, 0.018), r_ball * 0.18)
    n_port = int(pf.random.randint(rng_size, 2, 4))
    port_r = pf.random.uniform(rng_size, 0.026, 0.046)
    port_len = pf.random.uniform(rng_size, 0.055, 0.110)
    base_t = pf.random.uniform(rng_size, 0.022, 0.040)
    base_x = r_ball * pf.random.uniform(rng_size, 1.35, 1.85)
    base_y = r_ball * pf.random.uniform(rng_size, 1.15, 1.55)
    base_off = pf.random.uniform(rng_size, -0.04, 0.04)
    boss_r = pf.random.uniform(rng_size, 0.022, 0.040)
    boss_h = pf.random.uniform(rng_size, 0.035, 0.070)
    yaw0 = pf.random.uniform(rng_style, 0.0, 2.0 * math.pi)
    ellipsoid = pf.control.choice(rng_style, [(False, 1.2), (True, 1.0)])
    aspect = pf.random.uniform(rng_style, 1.08, 1.28) if ellipsoid else 1.0

    z_ball = base_t + r_ball * 0.92
    radii = (r_ball * aspect, r_ball, r_ball)
    shell = sphere(radii, (0.0, 0.0, z_ball), segments=36, rings=18)
    fuse(
        shell,
        box((base_x, base_y, base_t), (base_off, 0.0, base_t * 0.5)),
        what="valve base",
    )
    ports = []
    embed = r_ball * 0.40
    for index in range(n_port):
        step = math.radians(pf.random.uniform(rng_size, 72.0, 125.0))
        yaw = yaw0 + index * step
        lift = math.radians(pf.random.uniform(rng_style, -8.0, 22.0)) if index else 0.0
        direction = (
            math.cos(yaw) * math.cos(lift),
            math.sin(yaw) * math.cos(lift),
            math.sin(lift),
        )
        total = port_len + embed
        # Inner end sits inside the ball; outer end is port_len past the sphere.
        center_dist = r_ball - embed + total * 0.5
        center = (
            direction[0] * center_dist,
            direction[1] * center_dist,
            z_ball + direction[2] * center_dist,
        )
        fuse(
            shell,
            cylinder(port_r, total, center, rotation=aim_z(direction), vertices=28),
            what="valve port",
        )
        ports.append(direction)

    inner_r = r_ball - wall
    cut(
        shell,
        sphere((inner_r * aspect, inner_r, inner_r), (0.0, 0.0, z_ball), segments=28, rings=14),
        what="valve cavity",
    )
    bore_r = port_r - wall
    if bore_r > 0.008:
        for direction in ports:
            inner_stop = r_ball - wall - 0.010
            outer_tip = r_ball + port_len + 0.025
            bore_len = outer_tip - inner_stop
            bore_mid = (
                direction[0] * (inner_stop + bore_len * 0.5),
                direction[1] * (inner_stop + bore_len * 0.5),
                z_ball + direction[2] * (inner_stop + bore_len * 0.5),
            )
            cut(
                shell,
                cylinder(bore_r, bore_len, bore_mid, rotation=aim_z(direction), vertices=24),
                what="port bore",
            )

    material = hard_material(rng_mat)
    embed = 0.004
    boss = cylinder(
        boss_r,
        boss_h,
        (0.0, 0.0, z_ball + r_ball + boss_h * 0.5 - embed),
        vertices=24,
    )
    return rest_on_ground(finish([tag(shell, material, "shell"), tag(boss, material, "boss")]))


register(Category(
    category_id="valve_housing",
    code="G26",
    family="壳体",
    criterion="球体加两到三段端口，顶部凸台，底部有座",
    build=build,
    allowed_parts=frozenset({"shell", "boss"}),
))
