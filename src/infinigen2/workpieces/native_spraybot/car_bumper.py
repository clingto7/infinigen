"""Source-native Spraybot car bumper category."""

import procfunc as pf

from infinigen2.workpieces.native_spraybot.common import BuiltWorkpiece, category, json_safe, map_part_type, native_seed, register


PARTS = {0: "shell", 1: "grille", 2: "lip"}


def build(rng):
    from infinigen2.workpieces.native_spraybot.car_bumper_factory import CarBumperFactory

    factory = CarBumperFactory(native_seed(rng))
    obj = factory.create_asset()
    mesh = map_part_type(pf.MeshObject(obj), PARTS)
    return BuiltWorkpiece(mesh, json_safe({**factory._rec, "factory_seed": factory.factory_seed}))


register(category("car_bumper", "N01", "CarBumperFactory 原生随机结构", build, PARTS.values()))
