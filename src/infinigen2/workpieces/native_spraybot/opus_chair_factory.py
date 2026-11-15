# Copyright (C) 2026, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Authors: Opus
"""OpusChairFactory -- procedural *animal-back decorative round stool*.

Abstracted from a sheet of hand-made DIY chairs (white, stylized): every example is the
same object family ::

    round/elliptical flat SEAT  +  3-4 splayed tapered round LEGS  +  a symmetric pair of
    decorative back ORNAMENTS rising from the rear of the seat.

The ornament is the signature variable and collapses to three archetypes ::

    antler  : a branching, recursively-forking tapered rack   (deer)
    ear     : two tall uprights -- a closed teardrop loop, or a straight pointed ear (rabbit)
    horn    : a tapered curl that leans out then spirals inward over the top (ram)

The ornament family is *plugin-style*: `_ORNAMENTS` maps a type name to a builder that
returns the right-half tube list; adding a 4th archetype is one new builder + one entry +
one weight. Everything is built from Bezier spines swept into round, length-tapered tubes
(`geo_tube`), mirrored across the sagittal (x=0) plane so the pair is exactly symmetric.

Geometry only -- no spray trajectory here. Each face is tagged with a `part_type` int
(seat=0 / leg=1 / ornament=2) so a later white-box prior pass can address parts directly.

Self-contained on purpose (no shared package registration), so it can be developed in
isolation. Import it by full module path::

    from infinigen.assets.objects.seating.chairs.opus_chair import OpusChairFactory
"""
from __future__ import annotations

import bmesh
import bpy
import numpy as np
from numpy.random import uniform

from infinigen.assets.utils.decorate import set_shade_smooth, write_attribute
from infinigen.assets.utils.draw import bezier_curve
from infinigen.assets.utils.object import join_objects, new_bbox
from infinigen.core import surface
from infinigen.core.nodes.node_info import Nodes
from infinigen.core.placement.factory import AssetFactory
from infinigen.core.util import blender as butil
from infinigen.core.util.math import FixedSeed
from infinigen.core.util.random import random_general as rg
from infinigen2.workpieces.parametric_capture import active_capture

PART_TYPE = {"seat": 0, "leg": 1, "ornament": 2}

# tube cross-section resolution (sides of the swept circle)
_TUBE_RES = 12


def geo_tube(nw, r0, r1, resolution=_TUBE_RES):
    """Sweep a circular profile along a mesh polyline with a radius that lerps r0 -> r1
    from spline start to end (base -> tip taper). Mirrors `geo_radius` but length-varying."""
    skeleton = nw.new_node(
        Nodes.GroupInput, expose_input=[("NodeSocketGeometry", "Geometry", None)]
    )
    curve = nw.new_node(Nodes.MeshToCurve, [skeleton])
    factor = nw.new_node(Nodes.SplineParameter).outputs["Factor"]
    radius = nw.new_node(
        Nodes.MapRange, input_kwargs={"Value": factor, 3: r0, 4: r1}
    ).outputs["Result"]
    curve = nw.new_node(
        Nodes.SetCurveRadius, input_kwargs={"Curve": curve, "Radius": radius}
    )
    geometry = nw.curve2mesh(
        curve, nw.new_node(Nodes.CurveCircle, input_kwargs={"Resolution": resolution})
    )
    geometry = nw.new_node(Nodes.MergeByDistance, [geometry, None, 1e-3])
    nw.new_node(Nodes.GroupOutput, input_kwargs={"Geometry": geometry})


def _interp_on(anchors: np.ndarray, frac: float) -> np.ndarray:
    """Point at arc-length `frac` (0..1) along the polyline through `anchors` (N,3)."""
    seg = np.linalg.norm(np.diff(anchors, axis=0), axis=1)
    arc = np.concatenate([[0.0], np.cumsum(seg)])
    if arc[-1] < 1e-9:
        return anchors[0].copy()
    return np.array([np.interp(frac * arc[-1], arc, anchors[:, d]) for d in range(3)])


class OpusChairFactory(AssetFactory):
    ornament_types = (
        "weighted_choice",
        # core archetypes abstracted from the DIY reference photos
        (1.3, "antler"),
        (1.3, "ear"),
        (1.3, "horn"),
        # imaginative extensions (same Bezier-tube + mirror toolkit)
        (1.0, "wing"),
        (1.0, "flower"),
        (1.0, "heart"),
        (1.0, "bow"),
        (1.0, "crown"),
        (1.0, "swirl"),
        (1.0, "cat_ear"),
        # flat-panel (plate) backrests -- solid, not made of rods
        (1.4, "cloud"),
        (1.0, "blob"),
        (1.0, "scallop"),
        (1.0, "shield"),
    )

    def __init__(self, factory_seed, coarse=False):
        super().__init__(factory_seed, coarse)
        with FixedSeed(self.factory_seed):
            self._sample_params()

    # ------------------------------------------------------------------ sampling
    def _sample_params(self):
        # seat: round / mildly elliptical thick disc with rounded rim (or rounded-square)
        self.seat_shape = np.random.choice(["round", "square"], p=[0.7, 0.3])
        self.seat_r = uniform(0.13, 0.18)
        self.seat_t = uniform(0.030, 0.046)
        self.seat_ry = uniform(0.92, 1.06)  # y/x ratio (ellipse)

        # legs: 3 or 4 splayed chunky dowels, optionally outward-bowed
        self.n_legs = int(np.random.choice([3, 4], p=[0.6, 0.4]))
        self.leg_h = uniform(0.20, 0.30)
        self.leg_top_r = self.seat_r * uniform(0.5, 0.7)
        self.leg_splay = np.radians(uniform(6, 16))
        self.leg_rad0 = uniform(0.015, 0.021)  # at seat
        self.leg_rad1 = self.leg_rad0 * uniform(0.7, 0.95)  # at floor (gentle dowel taper)
        self.leg_curve = uniform(0.02, 0.06) if uniform() < 0.45 else 0.0  # outward mid-bow

        # ornament (the signature): one archetype, mirrored into a symmetric pair
        self.ornament_type = rg(self.ornament_types)
        self.orn_h = uniform(0.20, 0.32)  # height above seat top
        self.orn_r0 = uniform(0.013, 0.020)  # base radius (~leg thickness)
        self.orn_r1 = self.orn_r0 * uniform(0.35, 0.60)  # tip radius
        self.orn_spread = uniform(0.05, 0.11)  # outward x reach
        self.root_dx = uniform(0.02, 0.05)  # half-gap between the pair's roots
        self.root_y = self.seat_r * uniform(0.45, 0.7)  # how far back on the seat
        self.root_z = -self.seat_t * 0.2

        # antler-specific
        self.antler_branches = int(np.random.randint(2, 4))
        self.antler_depth = int(np.random.choice([1, 2], p=[0.45, 0.55]))
        # ear-specific
        self.ear_is_loop = uniform() < 0.6
        self.ear_loop_w = uniform(0.05, 0.09)
        self.ear_foot_w = uniform(0.03, 0.06)
        self.ear_lean = uniform(0.15, 0.5)  # fraction of spread the tip leans outward
        # horn-specific
        self.horn_tightness = uniform(0.45, 0.85)  # how far the curl comes back inward
        # extension-specific
        self.wing_blades = int(np.random.randint(2, 4))     # feathers per side
        self.flower_ring_r = uniform(0.035, 0.06)           # blossom ring radius
        self.bow_h = uniform(0.50, 0.72)                    # knot height (frac of orn_h)
        self.crown_points = int(np.random.randint(2, 4))    # spikes per side
        self.swirl_turns = uniform(1.0, 1.6)                # fiddlehead curl turns
        self.cat_ear_wide = uniform(0.5, 0.8)               # how wide the triangular ear
        # flat-panel backrests (cloud / blob / scallop / shield)
        self.panel_w = self.seat_r * uniform(0.70, 1.0)     # half-width of the plate
        self.panel_h = uniform(0.16, 0.26)                  # height above seat
        self.panel_t = uniform(0.020, 0.034)                # plate thickness
        self.panel_bumps = int(np.random.randint(3, 6))     # cloud bump count

        self.base_color = np.array(
            [uniform(0.88, 0.96), uniform(0.86, 0.93), uniform(0.80, 0.88), 1.0]
        )

    # ------------------------------------------------------------------ scaffolding
    def create_placeholder(self, **kwargs) -> bpy.types.Object:
        reach = self.seat_r + self.orn_spread + self.leg_h * np.tan(self.leg_splay)
        return new_bbox(
            -reach, reach,
            -reach, max(self.root_y + 0.05, self.seat_r),
            -self.leg_h, self.orn_h * 1.25,
        )

    def create_asset(self, **params) -> bpy.types.Object:
        # white-box spray priors captured at build time (meters); consumed by opus_spray.py
        self._rec = {"seat": None, "root_y": float(self.root_y), "root_z": float(self.root_z),
                     "legs": [], "orn_kind": None, "orn_rods": [], "orn_panel": None}
        parts = [self.make_seat(), *self.make_legs(), *self.make_ornament()]
        obj = join_objects(parts)
        set_shade_smooth(obj)
        self._assign_material(obj)
        return obj

    def finalize_assets(self, assets):
        pass

    # ------------------------------------------------------------------ tube helper
    def _tube(self, anchors: np.ndarray, r0, r1, part):
        """anchors: (N,3) world points -> tapered round tube tagged with `part`."""
        obj = bezier_curve(anchors.T, vector_locations=())  # bezier wants (3,N)
        surface.add_geomod(obj, geo_tube, apply=True, input_args=[float(r0), float(r1)])
        write_attribute(obj, PART_TYPE[part], "part_type", "FACE")
        rec = getattr(self, "_rec", None)  # record centerline prior (legs / rod ornaments)
        if rec is not None:
            key = "legs" if part == "leg" else "orn_rods"
            rec[key].append((np.asarray(anchors, float).copy(), float(r0), float(r1)))
        capture = active_capture()
        if capture is not None and part == 'leg':
            capture.native_opus(obj, 'leg_base', 'tapered_bezier_tube', {
                'anchors_m': np.asarray(anchors, float).tolist(),
                'start_radius_m': float(r0), 'end_radius_m': float(r1),
                'profile_sides': int(_TUBE_RES),
            })
        return obj

    # ------------------------------------------------------------------ seat
    def make_seat(self):
        if self.seat_shape == "square":
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -self.seat_t / 2))
            obj = bpy.context.active_object
            obj.scale = (self.seat_r, self.seat_r * self.seat_ry, self.seat_t / 2)
            butil.apply_transform(obj)
            butil.modify_mesh(obj, "BEVEL", width=min(self.seat_r * 0.3, self.seat_t * 0.45),
                              segments=8)
        else:
            bpy.ops.mesh.primitive_cylinder_add(
                vertices=64, radius=self.seat_r, depth=self.seat_t,
                location=(0, 0, -self.seat_t / 2),
            )
            obj = bpy.context.active_object
            obj.scale = (1.0, self.seat_ry, 1.0)
            butil.apply_transform(obj)
            butil.modify_mesh(obj, "BEVEL", width=self.seat_t * 0.3, segments=4)
        write_attribute(obj, PART_TYPE["seat"], "part_type", "FACE")
        if getattr(self, "_rec", None) is not None:
            self._rec["seat"] = {"shape": str(self.seat_shape), "r": float(self.seat_r),
                                 "ry": float(self.seat_ry), "t": float(self.seat_t)}
        capture = active_capture()
        if capture is not None:
            capture.native_opus(obj, 'seat', 'beveled_seat', {
                **self._rec['seat'],
                'bevel_width_m': float(min(self.seat_r * .3, self.seat_t * .45)
                                       if self.seat_shape == 'square' else self.seat_t * .3),
                'bevel_segments': 8 if self.seat_shape == 'square' else 4,
            })
        return obj

    # ------------------------------------------------------------------ legs
    def make_legs(self):
        # one leg points front (-y); the rest are spaced symmetrically about x=0
        if self.n_legs == 3:
            angles = np.array([-90.0, 30.0, 150.0])
        else:
            angles = np.array([45.0, 135.0, 225.0, 315.0])
        bot_r = self.leg_top_r + self.leg_h * np.tan(self.leg_splay)
        legs = []
        for a in np.radians(angles):
            ca, sa = np.cos(a), np.sin(a)
            top = np.array([self.leg_top_r * ca, self.leg_top_r * sa, -self.seat_t * 0.3])
            bot = np.array([bot_r * ca, bot_r * sa, -self.leg_h])
            if self.leg_curve > 0:  # outward-bowed dowel
                mr = (self.leg_top_r + bot_r) / 2 + self.leg_curve
                mid = np.array([mr * ca, mr * sa, -self.leg_h * 0.5])
                anchors = np.stack([top, mid, bot])
            else:
                anchors = np.stack([top, bot])
            legs.append(self._tube(anchors, self.leg_rad0, self.leg_rad1, "leg"))
        return legs

    # ------------------------------------------------------------------ ornament
    def make_ornament(self):
        """Rod ornaments build only the right half and get mirrored into a symmetric pair;
        flat-panel ornaments (`_FULL_ORNAMENTS`) build the whole symmetric plate themselves."""
        root = np.array([self.root_dx, self.root_y, self.root_z])
        if getattr(self, "_rec", None) is not None:
            self._rec["orn_kind"] = "panel" if self.ornament_type in _FULL_ORNAMENTS else "rod"
        parts = _ORNAMENTS[self.ornament_type](self, root)
        obj = join_objects(parts)
        if self.ornament_type not in _FULL_ORNAMENTS:
            # mirror across the sagittal plane (object origin is world origin)
            butil.modify_mesh(obj, "MIRROR", use_axis=(True, False, False))
        capture = active_capture()
        if capture is not None:
            if self.ornament_type in _FULL_ORNAMENTS:
                parameters = {'ornament_type': self.ornament_type,
                              'panel': self._rec['orn_panel'],
                              'bevel_width_m': float(self.panel_t * .4),
                              'bevel_segments': 3}
                constructor = 'beveled_ornament_panel'
            else:
                parameters = {'ornament_type': self.ornament_type,
                              'rods': [{'anchors_m': np.asarray(points, float).tolist(),
                                        'start_radius_m': float(r0),
                                        'end_radius_m': float(r1)}
                                       for points, r0, r1 in self._rec['orn_rods']],
                              'profile_sides': int(_TUBE_RES), 'mirrored_x': True}
                constructor = 'mirrored_bezier_tubes'
            capture.native_opus(obj, 'ornament', constructor, parameters)
        return [obj]

    # ---- antler: a main beam with a few outward-forking tines ---------
    def _build_antler(self, root):
        tubes = []
        H, S = self.orn_h * 0.9, self.orn_spread * 1.4  # antlers: a bit shorter, wider

        # main beam: curves outward (+x) and up, leaning slightly back (+y)
        beam = np.stack([
            root,
            root + np.array([0.25 * S, 0.03, 0.40 * H]),
            root + np.array([0.65 * S, 0.05, 0.74 * H]),
            root + np.array([1.00 * S, 0.04, H]),
        ])
        tubes.append(self._tube(beam, self.orn_r0, self.orn_r0 * 0.5, "ornament"))

        # tines fork off the beam, each reaching further out and up
        fracs = np.linspace(0.32, 0.86, self.antler_branches)
        for k, f in enumerate(fracs):
            base = _interp_on(beam, f)
            out = (0.6 + 0.5 * k) * S
            tip = base + np.array([
                out * uniform(0.55, 0.85), uniform(-0.02, 0.05),
                (1 - f) * H * uniform(0.6, 1.0) + 0.12 * H,
            ])
            mid = (base + tip) / 2 + np.array([0.06 * S, 0, 0.05 * H])
            r0 = self.orn_r0 * (0.9 - 0.4 * f)
            tubes.append(self._tube(np.stack([base, mid, tip]), r0, r0 * 0.45, "ornament"))
            # occasional secondary fork on the tine (depth 2)
            if self.antler_depth > 1 and uniform() < 0.55:
                b2 = _interp_on(np.stack([base, mid, tip]), uniform(0.5, 0.75))
                tip2 = b2 + np.array([
                    0.45 * S * uniform(0.4, 0.7), uniform(-0.02, 0.04),
                    0.3 * H * uniform(0.6, 1.0),
                ])
                tubes.append(self._tube(np.stack([b2, (b2 + tip2) / 2, tip2]), r0 * 0.6, r0 * 0.3, "ornament"))
        return tubes

    # ---- ear: closed teardrop loop, or a straight pointed ear ---------
    def _build_ear(self, root):
        H = self.orn_h
        y = root[1]
        lean = self.ear_lean * self.orn_spread
        if self.ear_is_loop:
            cx = root[0] + self.ear_foot_w / 2
            lw = self.ear_loop_w
            anchors = np.array([
                [cx - self.ear_foot_w / 2, y, root[2]],          # inner foot
                [cx - lw / 2 + 0.3 * lean, y, 0.55 * H],         # inner side
                [cx - lw / 2 + lean, y, 0.92 * H],               # inner shoulder
                [cx + lean, y, H],                               # top
                [cx + lw / 2 + lean, y, 0.92 * H],               # outer shoulder
                [cx + lw / 2 + 0.3 * lean, y, 0.55 * H],         # outer side
                [cx + self.ear_foot_w / 2, y, root[2]],          # outer foot
            ])
            r = self.orn_r0 * uniform(0.85, 1.0)
            return [self._tube(anchors, r, r, "ornament")]
        # pointed ear: thick base -> sharp tip, leaning outward
        tip = root + np.array([0.7 * self.orn_spread, 0, H])
        mid = root + np.array([0.35 * self.orn_spread, 0, 0.5 * H])
        anchors = np.stack([root, mid, tip])
        return [self._tube(anchors, self.orn_r0, self.orn_r0 * 0.30, "ornament")]

    # ---- horn: lean out, then curl inward over the top ----------------
    def _build_horn(self, root):
        H, S = self.orn_h, self.orn_spread
        cx, y = root[0], root[1]
        t = self.horn_tightness
        anchors = np.array([
            [cx, y, root[2]],
            [cx + 0.18 * S, y, 0.34 * H],
            [cx + 0.92 * S, y, 0.70 * H],          # lean outward
            [cx + 1.08 * S, y, 1.00 * H],          # top outer
            [cx + (1.08 - 0.85 * t) * S, y, 1.08 * H],   # curl over inward
            [cx + (1.08 - 1.45 * t) * S, y, 0.96 * H],   # curl tip, inward/down
        ])
        return [self._tube(anchors, self.orn_r0, self.orn_r1, "ornament")]

    # ---- wing: a fan of curved feather-blades ------------------------
    def _build_wing(self, root):
        tubes = []
        H, S = self.orn_h, self.orn_spread
        n = self.wing_blades + 1
        for k in range(n):
            frac = k / (n - 1)
            reach = S * (1.35 - 0.55 * frac)            # lower blades reach out more
            up = H * (0.45 + 0.55 * frac)               # upper blades stand taller
            tip = root + np.array([reach, 0.02, up])
            mid = root + np.array([0.5 * reach, 0.01, 0.5 * up + 0.08 * H])
            r = self.orn_r0 * (1 - 0.12 * k)
            tubes.append(self._tube(np.stack([root, mid, tip]), r, r * 0.35, "ornament"))
        return tubes

    # ---- flower: a stalk topped by a small ring (blossom) ------------
    def _build_flower(self, root):
        H, S = self.orn_h, self.orn_spread
        y = root[1]
        top = root + np.array([0.3 * S, 0, H])
        stalk = self._tube(
            np.stack([root, root + np.array([0.15 * S, 0, 0.5 * H]), top]),
            self.orn_r0, self.orn_r0 * 0.7, "ornament")
        rr = self.flower_ring_r
        cx, cz = top[0], top[2] + rr
        ang = np.linspace(0, 2 * np.pi, 9)
        ring = np.stack([cx + rr * np.cos(ang), np.full(9, y), cz + rr * np.sin(ang)], axis=1)
        return [stalk, self._tube(ring, self.orn_r0 * 0.55, self.orn_r0 * 0.55, "ornament")]

    # ---- heart: right half of a centred heart (mirror completes it) --
    def _build_heart(self, root):
        H, S = self.orn_h, self.orn_spread
        y, zb = root[1], root[2]
        W, Hh = 1.7 * S, 0.72 * H   # chubby heart: wider than the default narrow spread
        anchors = np.array([
            [0.0,      y, zb + 0.10 * Hh],   # bottom tip on the centreline
            [0.55 * W, y, zb + 0.42 * Hh],   # right side
            [0.52 * W, y, zb + 0.78 * Hh],   # right lobe outer
            [0.26 * W, y, zb + 0.97 * Hh],   # right lobe top
            [0.0,      y, zb + 0.74 * Hh],   # top-centre notch
        ])
        r = self.orn_r0 * uniform(0.9, 1.05)
        return [self._tube(anchors, r, r, "ornament")]

    # ---- bow: a ribbon wing + tail on a short post (mirror -> bow) ---
    def _build_bow(self, root):
        H, S = self.orn_h, self.orn_spread
        y = root[1]
        kz = root[2] + self.bow_h * H       # knot height
        knot = np.array([0.014, y, kz])
        loop = np.array([
            knot,
            [0.55 * S, y, kz + 0.34 * H],
            [1.30 * S, y, kz + 0.16 * H],
            [1.30 * S, y, kz - 0.16 * H],
            [0.55 * S, y, kz - 0.34 * H],
            knot,
        ])
        tail = np.array([knot, [0.50 * S, y, kz - 0.30 * H], [0.62 * S, y, kz - 0.62 * H]])
        post = np.array([[0.014, y, root[2]], knot])
        r = self.orn_r0
        return [self._tube(loop, r * 0.85, r * 0.85, "ornament"),
                self._tube(tail, r * 0.85, r * 0.55, "ornament"),
                self._tube(post, r, r * 0.9, "ornament")]

    # ---- crown: a post + banded top with spikes (mirror -> crown) ----
    def _build_crown(self, root):
        H, S = self.orn_h, self.orn_spread
        y, zt = root[1], root[2] + 0.62 * H
        tubes = [
            self._tube(np.array([[0.03, y, root[2]], [0.05, y, zt]]),
                       self.orn_r0, self.orn_r0 * 0.9, "ornament"),
            self._tube(np.array([[0.0, y, zt], [0.55 * S, y, zt + 0.05 * H], [1.1 * S, y, zt]]),
                       self.orn_r0 * 0.8, self.orn_r0 * 0.8, "ornament"),
        ]
        for k in range(self.crown_points + 1):  # spikes at band nodes, alternating heights
            bx = k / self.crown_points * S * 1.1
            tip = np.array([bx, y, zt + (0.34 + 0.10 * (k % 2)) * H])
            tubes.append(self._tube(np.array([[bx, y, zt], tip]),
                                    self.orn_r0 * 0.65, self.orn_r0 * 0.2, "ornament"))
        return tubes

    # ---- swirl: a stem ending in a fiddlehead curl -------------------
    def _build_swirl(self, root):
        H, S = self.orn_h, self.orn_spread
        y = root[1]
        stem_top = root + np.array([0.2 * S, 0, 0.5 * H])
        n = 16
        t = np.linspace(0, 1, n)
        ang = np.pi + t * self.swirl_turns * 2 * np.pi   # continue upward, then curl in
        cr0 = 0.32 * S
        rad = cr0 * (1 - 0.7 * t)
        cx, cz = stem_top[0] + cr0, stem_top[2] + cr0
        curl = np.stack([cx + rad * np.cos(ang), np.full(n, y), cz + rad * np.sin(ang)], axis=1)
        spine = np.vstack([root, stem_top, curl])
        return [self._tube(spine, self.orn_r0, self.orn_r0 * 0.45, "ornament")]

    # ---- cat_ear: a wide triangular ear ------------------------------
    def _build_cat_ear(self, root):
        H, S = self.orn_h, self.orn_spread
        tip = root + np.array([0.45 * S, 0, H])
        base_out = root + np.array([(0.5 + 0.6 * self.cat_ear_wide) * S, 0, 0.12 * H])
        anchors = np.stack([root, tip, base_out])
        return [self._tube(anchors, self.orn_r0, self.orn_r0 * 0.5, "ornament")]

    # ================= flat-panel backrests (silhouette -> filled -> solidified) =====
    def _panel(self, sil_xz):
        """sil_xz: ordered (x,z) boundary of a symmetric plate in the back plane -> a solid,
        beveled, thickened panel standing at y=root_y. No mirror (already full & symmetric)."""
        bm = bmesh.new()
        vs = [bm.verts.new((float(x), float(self.root_y), float(z))) for x, z in sil_xz]
        bm.faces.new(vs)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new("panel")
        bm.to_mesh(me)
        bm.free()
        obj = bpy.data.objects.new("panel", me)
        bpy.context.collection.objects.link(obj)
        butil.modify_mesh(obj, "SOLIDIFY", thickness=self.panel_t, offset=0)
        butil.modify_mesh(obj, "BEVEL", width=self.panel_t * 0.4, segments=3)
        write_attribute(obj, PART_TYPE["ornament"], "part_type", "FACE")
        if getattr(self, "_rec", None) is not None:
            self._rec["orn_panel"] = {"sil_xz": [(float(x), float(z)) for x, z in sil_xz],
                                      "y": float(self.root_y), "t": float(self.panel_t)}
        return [obj]

    @staticmethod
    def _close(top, base_z):
        """top = (x,z) along the upper edge left->right; close with a flat bottom at base_z."""
        return top + [(top[-1][0], base_z), (top[0][0], base_z)]

    # ---- cloud: flat bottom, top = upper envelope of overlapping bumps -----
    def _build_cloud(self, root):
        W, z0 = self.panel_w, root[2]
        n = self.panel_bumps
        centers = np.linspace(-W, W, n)
        radii = uniform(0.5, 0.95, n) * W
        xs = np.linspace(-W, W, 88)
        env = np.zeros_like(xs)
        for c, r in zip(centers, radii):
            env = np.maximum(env, np.sqrt(np.clip(r ** 2 - (xs - c) ** 2, 0, None)))
        env = env / (env.max() + 1e-9) * self.panel_h
        return self._panel(self._close(list(zip(xs, z0 + env)), z0))

    # ---- blob / scallop: a lumpy radial plate (few big lumps vs many small) -
    def _radial_panel(self, k, amp):
        W = self.panel_w
        Rz = self.panel_h * 0.55
        zc = self.root_z + Rz
        th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        rad = 1 + amp * np.cos(k * th)
        xs = W * rad * np.sin(th)
        zs = zc + Rz * rad * np.cos(th)
        return self._panel(list(zip(xs, zs)))

    def _build_blob(self, root):
        return self._radial_panel(k=np.random.randint(3, 6), amp=uniform(0.14, 0.24))

    def _build_scallop(self, root):
        return self._radial_panel(k=np.random.randint(8, 13), amp=uniform(0.08, 0.14))

    # ---- shield: straight sides + a semicircular arched top ----------------
    def _build_shield(self, root):
        W, z0 = self.panel_w, root[2]
        body = self.panel_h * 0.58
        xs = np.linspace(-W, W, 56)
        arch = (self.panel_h - body) * np.sqrt(np.clip(1 - (xs / W) ** 2, 0, None))
        return self._panel(self._close(list(zip(xs, z0 + body + arch)), z0))

    # ------------------------------------------------------------------ material
    def _assign_material(self, obj):
        mat = bpy.data.materials.new(f"opus_chair_{self.factory_seed}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = tuple(self.base_color)
            bsdf.inputs["Roughness"].default_value = 0.72
        obj.data.materials.append(mat)


# plugin-style ornament registry: name -> right-half builder. Add a 4th archetype with one
# new `_build_*` method, one entry here, and one weight in `ornament_types`.
_ORNAMENTS = {
    "antler": OpusChairFactory._build_antler,
    "ear": OpusChairFactory._build_ear,
    "horn": OpusChairFactory._build_horn,
    "wing": OpusChairFactory._build_wing,
    "flower": OpusChairFactory._build_flower,
    "heart": OpusChairFactory._build_heart,
    "bow": OpusChairFactory._build_bow,
    "crown": OpusChairFactory._build_crown,
    "swirl": OpusChairFactory._build_swirl,
    "cat_ear": OpusChairFactory._build_cat_ear,
    # flat-panel (plate) backrests
    "cloud": OpusChairFactory._build_cloud,
    "blob": OpusChairFactory._build_blob,
    "scallop": OpusChairFactory._build_scallop,
    "shield": OpusChairFactory._build_shield,
}

# panel ornaments build a full symmetric plate themselves -> skip the mirror in make_ornament
_FULL_ORNAMENTS = {"cloud", "blob", "scallop", "shield"}
