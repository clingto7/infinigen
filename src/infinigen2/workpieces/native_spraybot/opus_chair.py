"""Source-native Spraybot Opus chair category."""

import procfunc as pf

from infinigen2.workpieces.native_spraybot.common import BuiltWorkpiece, category, json_safe, map_part_type, native_seed, register


PARTS = {0: "seat", 1: "leg_base", 2: "ornament"}


def build(rng):
    from infinigen2.workpieces.native_spraybot.opus_chair_factory import OpusChairFactory

    factory = OpusChairFactory(native_seed(rng))
    obj = factory.create_asset()
    mesh = map_part_type(pf.MeshObject(obj), PARTS)
    return BuiltWorkpiece(mesh, json_safe(factory._rec))


register(category("opus_chair", "N02", "OpusChairFactory 原生随机结构", build, PARTS.values()))
