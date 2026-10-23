"""C08 水槽底柜。

结构判据：柜顶开口，内部无搁板，正面是门。
单扇或双开门、把手样式是构型。玻璃芯板被锁掉。
"""

import procfunc as pf

from infinigen2.objects import storage
from infinigen2.util import spray
from infinigen2.workpieces import assemble


def build(rng: pf.RNG) -> pf.MeshObject:
    mesh = assemble.adopt_storage(storage.storage_sink_base_rand(rng, spray_tags=True).mesh)
    spray.write_spray_target(mesh)
    return mesh

