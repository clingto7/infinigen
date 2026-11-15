# Copyright (C) 2026, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Authors: Opus
"""CarBumperFactory -- procedural *front car-bumper cover* (a wide, thin, wrapped shell).

Abstracted from a sheet of red front bumper covers (fascias). Every example is the same
object family: a wide, gently convex thin SHELL that wraps back at the two ends, rolled at
top/bottom, pierced by a few large OPENINGS (central air intake, fog-lamp holes, ...), with a
recessed mesh GRILLE behind the central intake.

The exact surface is defined once in `bumper_surface.BumperSurface` (pure numpy); this factory
samples its parameters, builds the mesh FROM that surface, and records the full parameter dict
on `self._rec["surface"]` so `bumper_spray` reconstructs the *same* surface for trajectory gen
(white-box, no shape inference). Construction is 2D-first (silhouette minus openings in the
(s,v) param rectangle, grid-masked + triangulated) then mapped to 3D + SOLIDIFY for thickness;
the GRILLE is the same trick over the intake, mapped one `recess` deeper.

Diversity = a weighted `front_style` family (sedan / sport / suv / classic / split) crossed
with TOP/BOTTOM envelope archetypes (flat / arch / dip / twin_horn / shoulder; valance / smile),
convexity class, wrap angle, grille pattern, fog shape, and on/off ornaments.

Geometry only -- no spray trajectory. Each face is tagged with a `part_type` int
(shell=0 / grille=1 / lip=2). Self-contained (isolated `carbumper/` work package, touches no
shared infinigen registration). Import by full path::

    from car_bumper import CarBumperFactory     # after carbumper/ is on sys.path
"""
from __future__ import annotations

import bpy
import numpy as np
from numpy.random import uniform

from infinigen.assets.utils.decorate import set_shade_smooth
from infinigen.assets.utils.object import join_objects, new_bbox
from infinigen.core.placement.factory import AssetFactory
from infinigen.core.util import blender as butil
from infinigen.core.util.math import FixedSeed
from infinigen.core.util.random import random_general as rg

from .bumper_surface import (
    BumperSurface, rrect, ellipse, trapezoid, scale_hex, pip, grid_mesh,
)
from infinigen2.workpieces.parametric_capture import active_capture

PART_TYPE = {"shell": 0, "grille": 1, "lip": 2}


class CarBumperFactory(AssetFactory):
    front_styles = (
        "weighted_choice",
        (1.4, "sedan_smooth"),   # rounded, single big lower intake + small fogs
        (1.2, "sport_angular"),  # wide hex intake, slot fogs, lower lip
        (1.1, "suv_wide"),       # tall + wide rectangular intake, skid lip
        (1.1, "classic_round"),  # smooth single opening, no fog
        (1.0, "split_two_tier"), # upper slot grille + lower intake
    )
    grille_patterns = ("weighted_choice", (1.3, "honeycomb"), (1.0, "h_slats"),
                       (1.0, "v_bars"), (0.9, "mesh"))
    fog_shapes = ("weighted_choice", (1.0, "round"), (1.0, "oval"), (1.0, "slot"), (0.8, "none"))

    def __init__(self, factory_seed, coarse=False):
        super().__init__(factory_seed, coarse)
        with FixedSeed(self.factory_seed):
            self._sample_params()

    # ------------------------------------------------------------ sampling
    def _sample_params(self):
        self.style = rg(self.front_styles)
        s = self.style

        # overall thin-shell proportions (meters). width = lateral param length W_lat.
        self.W_lat = uniform(1.30, 1.55)
        self.H = uniform(0.34, 0.56)
        if s == "suv_wide":
            self.W_lat = uniform(1.52, 1.78)
            self.H = uniform(0.48, 0.62)
        elif s == "classic_round":
            self.H = uniform(0.33, 0.42)
        self.thick = uniform(0.005, 0.009)

        # plan wrap (flat-middle fraction + end wrap angle): nearly flat -> strongly wrapped
        self.plan_flat = uniform(0.18, 0.55)
        self.wrap_phi = np.radians(uniform(20, 66))
        if s == "classic_round":
            self.plan_flat = uniform(0.12, 0.30)
            self.wrap_phi = np.radians(uniform(22, 40))

        # cross-section CONVEXITY class -> flat-faced vs strongly bulged fronts
        self.convexity = rg(("weighted_choice", (1.0, "flat"), (1.3, "normal"), (1.0, "bulged")))
        self.protrude = {"flat": uniform(0.08, 0.13), "normal": uniform(0.13, 0.19),
                         "bulged": uniform(0.19, 0.27)}[self.convexity]
        self.chin = uniform(0.18, 0.62)              # how far the bottom tucks back
        self.toproll = uniform(0.20, 0.70)           # how far the top rolls back
        self.bulge_v = uniform(0.42, 0.60)           # height of max bulge

        # ---- overall ENVELOPE diversity (big-shape knobs, not just openings) ----
        self.w_top = uniform(0.82, 1.0)              # half-width at the top (side taper)
        self.w_bot = uniform(0.84, 1.0)              # half-width at the bottom
        self.corner_round = uniform(0.14, 0.30)      # bottom-corner rounding span (v units)

        # TOP-edge archetype = the big silhouette variety from the photos
        self.top_kind = rg(("weighted_choice", (1.1, "flat"), (1.0, "arch"),
                            (1.0, "dip"), (1.3, "twin_horn"), (1.0, "shoulder")))
        if s == "sport_angular":
            self.top_kind = rg(("weighted_choice", (1.5, "twin_horn"), (1.0, "shoulder"), (0.6, "dip")))
        elif s == "classic_round":
            self.top_kind = rg(("weighted_choice", (1.4, "arch"), (1.2, "flat"), (0.6, "dip")))
        if self.top_kind in ("twin_horn", "shoulder"):
            self.w_top = uniform(0.95, 1.0)          # keep material out where the horns rise
        self.horn_h = uniform(0.18, 0.42)            # horn rise (fraction of H)
        self.horn_s = uniform(0.58, 0.78)            # |s| location of the horns
        self.horn_w = uniform(0.10, 0.20)            # horn gaussian width
        self.arch_h = uniform(0.07, 0.22)            # centre dome rise (fraction of H)
        self.dip_h = uniform(0.08, 0.26)             # centre dip depth (fraction of H)

        # BOTTOM-edge archetype
        self.bot_kind = rg(("weighted_choice", (1.3, "flat"), (1.0, "valance"), (1.0, "smile")))
        self.val_h = uniform(0.06, 0.18)             # central lower-lip dip
        self.smile_h = uniform(0.06, 0.16)           # corners curl up

        # central intake opening
        self.intake_shape = {
            "sedan_smooth": "trapezoid", "sport_angular": "hex", "suv_wide": "rrect",
            "classic_round": "rrect", "split_two_tier": "trapezoid",
        }[s]
        self.intake_cv = uniform(0.30, 0.42)         # centre height (v)
        self.intake_hw = uniform(0.40, 0.62)         # half-width (s)
        self.intake_hh = uniform(0.14, 0.22)         # half-height (v)
        if s in ("suv_wide", "sport_angular"):
            self.intake_hw = uniform(0.55, 0.74)
            self.intake_hh = uniform(0.17, 0.26)

        # upper slot grille (split style) -- a thin wide intake high up
        self.has_upper = s == "split_two_tier" or uniform() < 0.18
        self.upper_cv = uniform(0.66, 0.76)
        self.upper_hw = uniform(0.34, 0.52)
        self.upper_hh = uniform(0.030, 0.055)

        # fog-lamp openings near the lower corners
        self.fog = "none" if s == "classic_round" else rg(self.fog_shapes)
        self.fog_sx = uniform(0.66, 0.82)            # |s| of the fog centre
        self.fog_cv = uniform(0.20, 0.30)
        self.fog_r = uniform(0.07, 0.11)

        # headlight notches at the two top corners
        self.has_notch = uniform() < 0.5
        self.notch_w = uniform(0.16, 0.26)
        self.notch_h = uniform(0.10, 0.18)

        # lower lip / skid splitter (a short forward apron along the bottom edge)
        self.has_lip = s in ("sport_angular", "suv_wide") or uniform() < 0.3
        self.lip_h = uniform(0.05, 0.09)
        self.lip_fwd = uniform(0.02, 0.05)

        # grille insert
        self.grille_on = uniform() < 0.92
        self.grille_pattern = rg(self.grille_patterns)
        self.grille_recess = uniform(0.025, 0.05)
        self.grille_wall = uniform(0.010, 0.018)     # honeycomb/bar wall thickness (param-ish)

        self.base_color = np.array([uniform(0.55, 0.85), uniform(0.04, 0.10),
                                    uniform(0.04, 0.10), 1.0])

        # ---- assemble the SINGLE surface (shared with bumper_spray via rec["surface"]) ----
        self._openings = self._big_openings()
        self.surf_params = {
            "W_lat": self.W_lat, "H": self.H, "thick": self.thick,
            "plan_flat": self.plan_flat, "wrap_phi": self.wrap_phi,
            "protrude": self.protrude, "chin": self.chin, "toproll": self.toproll,
            "bulge_v": self.bulge_v,
            "w_top": self.w_top, "w_bot": self.w_bot, "corner_round": self.corner_round,
            "top_kind": self.top_kind, "horn_h": self.horn_h, "horn_s": self.horn_s,
            "horn_w": self.horn_w, "arch_h": self.arch_h, "dip_h": self.dip_h,
            "bot_kind": self.bot_kind, "val_h": self.val_h, "smile_h": self.smile_h,
            "openings": [o.round(5).tolist() for o in self._openings],
        }
        self.surf = BumperSurface(self.surf_params)

    # ------------------------------------------------------------ openings (s,v)
    def _big_openings(self):
        """Large holes cut THROUGH the shell (intake / upper slot / fogs / notches)."""
        holes = []
        cx, cv, hw, hh = 0.0, self.intake_cv, self.intake_hw, self.intake_hh
        if self.intake_shape == "trapezoid":
            holes.append(trapezoid(cx, cv, hw, hw * 0.80, hh, r=1.0))
        elif self.intake_shape == "hex":
            holes.append(scale_hex(cx, cv, hw, hh))
        else:
            holes.append(rrect(cx, cv, hw, hh, min(hw, hh) * 0.4, n=7))
        if self.has_upper:
            holes.append(rrect(0.0, self.upper_cv, self.upper_hw, self.upper_hh,
                               self.upper_hh * 0.8, n=5))
        if self.fog != "none":
            for sgn in (-1.0, 1.0):
                fx = sgn * self.fog_sx
                if self.fog == "round":
                    holes.append(ellipse(fx, self.fog_cv, self.fog_r, self.fog_r))
                elif self.fog == "oval":
                    holes.append(ellipse(fx, self.fog_cv, self.fog_r * 1.4, self.fog_r * 0.7))
                else:  # slot
                    holes.append(rrect(fx, self.fog_cv, self.fog_r * 1.5, self.fog_r * 0.45,
                                       self.fog_r * 0.4, n=5))
        if self.has_notch:
            for sgn in (-1.0, 1.0):
                holes.append(rrect(sgn * (1.0 - self.notch_w * 0.3), 1.0,
                                   self.notch_w, self.notch_h, self.notch_w * 0.4, n=5))
        return holes

    # ------------------------------------------------------------ mesh builders
    def _obj_from_sv(self, sv, faces, name, recess=0.0, part="shell"):
        P = self.surf.point(sv, recess=recess)
        me = bpy.data.meshes.new(name)
        me.from_pydata(P.tolist(), [], faces.tolist())
        me.update()
        obj = bpy.data.objects.new(name, me)
        bpy.context.collection.objects.link(obj)
        capture = active_capture()
        if capture is not None:
            capture.native_surface_source(
                obj, kind='bumper_surface_grid',
                parameters={'surface': self.surf.params(), 'part': part,
                            'recess_m': float(recess), 'solidify_thickness_m': float(self.thick)},
                uv=sv, faces=faces,
            )
        butil.modify_mesh(obj, "SOLIDIFY", thickness=self.thick, offset=-1.0)
        self._tag(obj, part)            # tag after modifiers so every final face is labelled
        return obj

    @staticmethod
    def _tag(obj, part):
        me = obj.data
        attr = me.attributes.get("part_type")
        if attr is None or attr.domain != "FACE":
            attr = me.attributes.new("part_type", "INT", "FACE")
        attr.data.foreach_set("value", [PART_TYPE[part]] * len(me.polygons))
        me.update()

    def make_shell(self):
        # dense (s,v) grid masked by the surface's own inside() (outline minus openings)
        Ns, Nv = 132, 66
        S = np.linspace(-1.0, 1.0, Ns)
        Vv = np.linspace(0.0, 1.0, Nv)
        gs, gv = np.meshgrid(S, Vv, indexing="ij")
        pts = np.column_stack([gs.ravel(), gv.ravel()])
        mask = self.surf.inside(pts).reshape(Ns, Nv)
        sv, faces = grid_mesh(mask, S, Vv)
        if len(faces) < 4:
            raise RuntimeError("shell mask produced no faces")
        self._rec_shell()
        return self._obj_from_sv(sv, faces, "bumper_shell", part="shell")

    def make_grille(self):
        if not self.grille_on:
            return []
        cx, cv, hw, hh = 0.0, self.intake_cv, self.intake_hw, self.intake_hh
        panel = rrect(cx, cv, hw * 1.04, hh * 1.04, min(hw, hh) * 0.35, n=7)
        holes = self._grille_holes(cx, cv, hw, hh)
        Ns = max(56, int(hw * 230))
        Nv = max(40, int(hh * 230))
        S = np.linspace(cx - hw * 1.05, cx + hw * 1.05, Ns)
        Vv = np.linspace(cv - hh * 1.05, cv + hh * 1.05, Nv)
        gs, gv = np.meshgrid(S, Vv, indexing="ij")
        pts = np.column_stack([gs.ravel(), gv.ravel()])
        mask = pip(pts, panel)
        for h in holes:
            mask &= ~pip(pts, h)
        sv, faces = grid_mesh(mask.reshape(Ns, Nv), S, Vv)
        if len(faces) < 4:
            return []
        self._rec["grille"] = {"pattern": str(self.grille_pattern),
                               "recess": float(self.grille_recess), "n_holes": len(holes)}
        return [self._obj_from_sv(sv, faces, "bumper_grille",
                                  recess=self.grille_recess, part="grille")]

    def _grille_holes(self, cx, cv, hw, hh):
        pat = self.grille_pattern
        w = self.grille_wall
        holes = []
        if pat in ("h_slats", "mesh"):
            n = max(3, int(2 * hh / 0.05))
            for zc in np.linspace(cv - hh + hh / n, cv + hh - hh / n, n):
                holes.append(rrect(cx, zc, hw * 0.92, hh / n - w, (hh / n - w) * 0.5, n=4))
        if pat in ("v_bars", "mesh"):
            n = max(4, int(2 * hw / 0.06))
            for xc in np.linspace(cx - hw + hw / n, cx + hw - hw / n, n):
                holes.append(rrect(xc, cv, hw / n - w, hh * 0.92, (hw / n - w) * 0.5, n=4))
        if pat == "honeycomb":
            aspect = (self.W_lat / 2.0) / self.H     # s-unit physical / v-unit physical
            r = float(np.clip(max(hh, hw / aspect) / 5.0, 0.045, 0.10))
            dx = r * 1.5
            dy = r * np.sqrt(3) / aspect
            row, zc = 0, cv - hh + r * np.sqrt(3) / aspect
            while zc < cv + hh:
                xc = cx - hw + ((r * 0.75) if (row % 2) else 0.0)
                while xc < cx + hw:
                    holes.append(scale_hex(xc, zc, r - w, (r - w) / aspect))
                    xc += dx
                zc += dy
                row += 1
        return holes

    # ------------------------------------------------------------ lower lip
    def make_lip(self):
        if not self.has_lip:
            return []
        Ns, Nv = 120, 8
        S = np.linspace(-0.96, 0.96, Ns)
        Vv = np.linspace(0.0, self.lip_h, Nv)
        gs, gv = np.meshgrid(S, Vv, indexing="ij")
        sv = np.column_stack([gs.ravel(), gv.ravel()])
        P = self.surf.point(sv)
        s, v = sv[:, 0], sv[:, 1]
        _, _, nx, ny = self.surf.plan(s)
        grow = self.lip_fwd * (1 - v / max(self.lip_h, 1e-6))    # extra forward push toward v=0
        P[:, 0] += nx * grow
        P[:, 1] += ny * grow
        idx = np.arange(Ns * Nv).reshape(Ns, Nv)
        faces = []
        for i in range(Ns - 1):
            for j in range(Nv - 1):
                a, b, c, d = idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]
                faces.append((a, b, c)); faces.append((a, c, d))
        me = bpy.data.meshes.new("bumper_lip")
        me.from_pydata(P.tolist(), [], faces)
        me.update()
        obj = bpy.data.objects.new("bumper_lip", me)
        bpy.context.collection.objects.link(obj)
        capture = active_capture()
        if capture is not None:
            capture.native_surface_source(
                obj, kind='bumper_lip_grid',
                parameters={'surface': self.surf.params(), 'part': 'lip',
                            'lip_forward_m': float(self.lip_fwd),
                            'lip_height': float(self.lip_h),
                            'solidify_thickness_m': float(self.thick)},
                uv=sv, faces=np.asarray(faces, dtype=int),
            )
        butil.modify_mesh(obj, "SOLIDIFY", thickness=self.thick, offset=-1.0)
        self._tag(obj, "lip")
        return [obj]

    # ------------------------------------------------------------ priors / scaffolding
    def _rec_shell(self):
        self._rec = getattr(self, "_rec", {})
        self._rec.update({
            "style": str(self.style), "convexity": str(self.convexity),
            "top_kind": str(self.top_kind), "bot_kind": str(self.bot_kind),
            "thick": float(self.thick),
            "intake": {"shape": self.intake_shape, "cv": float(self.intake_cv),
                       "hw": float(self.intake_hw), "hh": float(self.intake_hh)},
            "part_type_legend": list(PART_TYPE.items()),
            "surface": self.surf.params(),         # <- the single source of truth for spray
        })

    def create_placeholder(self, **kwargs):
        reach = self.W_lat / 2.0 + self.protrude + 0.05
        return new_bbox(-reach, reach, -self.protrude - 0.1, 0.6, -0.15, self.H * 1.5)

    def create_asset(self, **params):
        self._rec = {}
        parts = [self.make_shell()] + self.make_grille() + self.make_lip()
        obj = join_objects(parts)
        set_shade_smooth(obj)
        self._assign_material(obj)
        return obj

    def finalize_assets(self, assets):
        pass

    def _assign_material(self, obj):
        mat = bpy.data.materials.new(f"car_bumper_{self.factory_seed}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = tuple(self.base_color)
            bsdf.inputs["Roughness"].default_value = 0.28
        obj.data.materials.append(mat)
