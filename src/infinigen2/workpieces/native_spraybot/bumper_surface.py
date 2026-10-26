# Copyright (C) 2026, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory of this source tree.

# Authors: Opus
"""The single source of truth for the CarBumper SURFACE -- pure numpy, no bpy.

`CarBumperFactory` builds its mesh from this map, and `bumper_spray` builds the trajectory
from the SAME map (reconstructed from `rec["surface"]`), so the sprayed surface is *exactly*
the meshed surface (white-box, no shape inference).

A bumper is a height-field over a normalised param rectangle (s in [-1,1] across width, v in
[0,1] bottom->top):

    point(s,v) = PlanCurve(s) + frontNormal(s) * profileForward(v) + (0, 0, z(s,v))
    z(s,v)     = z_bot(s) + v * (z_top(s) - z_bot(s))            # per-column envelope

The FRONT (outer, Class-A) face is `point`; the outward normal is the finite-difference normal
oriented toward -Y. The BACK (inner) face is, for now, the parallel offset by the shell
thickness -- but it is produced by `sample(side="back")` as its OWN (point, normal) pair, so
when an asymmetric inner structure is added later only this method changes, not the spray.
"""
from __future__ import annotations

import numpy as np


# ------------------------------------------------------------------ 2D polygon primitives (s,v)
def rrect(cx, cy, hw, hh, r, n=7):
    r = float(min(r, hw * 0.99, hh * 0.99))
    a = np.linspace(0, np.pi / 2, n)
    cs, sn = np.cos(a), np.sin(a)
    corners = [
        (cx + hw - r + r * cs, cy + hh - r + r * sn),
        (cx - hw + r - r * sn, cy + hh - r + r * cs),
        (cx - hw + r - r * cs, cy - hh + r - r * sn),
        (cx + hw - r + r * sn, cy - hh + r - r * cs),
    ]
    return np.concatenate([np.column_stack(c) for c in corners], axis=0)


def ellipse(cx, cy, rx, ry, n=40):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([cx + rx * np.cos(a), cy + ry * np.sin(a)])


def trapezoid(cx, cy, hw_bot, hw_top, hh, r=0.0):
    pts = np.array([
        [cx - hw_bot, cy - hh], [cx + hw_bot, cy - hh],
        [cx + hw_top, cy + hh], [cx - hw_top, cy + hh],
    ])
    if r <= 0:
        return pts
    out = []
    for i in range(4):
        p, q = pts[i], pts[(i + 1) % 4]
        for t in np.linspace(0, 1, 6, endpoint=False):
            out.append(p * (1 - t) + q * t)
    return np.asarray(out)


def scale_hex(cx, cv, rs, rv, flat_top=False):
    off = 0.0 if flat_top else np.pi / 6
    a = np.linspace(0, 2 * np.pi, 6, endpoint=False) + off
    return np.column_stack([cx + rs * np.cos(a), cv + rv * np.sin(a)])


def pip(pts, poly):
    """Vectorised even-odd point-in-polygon. pts (N,2), poly (M,2) implicitly closed."""
    pts = np.asarray(pts, float)
    poly = np.asarray(poly, float)
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    xj, yj = poly[-1]
    for i in range(len(poly)):
        xi, yi = poly[i]
        cond = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
        inside ^= cond
        xj, yj = xi, yi
    return inside


def grid_mesh(mask2d, S, V):
    """mask2d (Ns,Nv) bool -> (verts_sv (K,2), faces (T,3)); inside cells become two tris."""
    Ns, Nv = mask2d.shape
    idx = -np.ones((Ns, Nv), np.int64)
    sv = []
    for i in range(Ns):
        for j in range(Nv):
            if mask2d[i, j]:
                idx[i, j] = len(sv)
                sv.append((S[i], V[j]))
    faces = []
    for i in range(Ns - 1):
        for j in range(Nv - 1):
            a, b, c, d = idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]
            if a >= 0 and b >= 0 and c >= 0 and d >= 0:
                faces.append((a, b, c))
                faces.append((a, c, d))
    return np.asarray(sv, float), np.asarray(faces, np.int64)


def _smoothstep_ramp(x, lo, hi):
    a = np.clip((np.abs(x) - lo) / max(hi - lo, 1e-6), 0, 1)
    return a * a * (3 - 2 * a)


# ------------------------------------------------------------------ the surface
class BumperSurface:
    """Reconstructable from a plain param dict (-> stored on `rec["surface"]`)."""

    def __init__(self, p: dict):
        self.p = dict(p)
        self.W_lat = float(p["W_lat"])
        self.H = float(p["H"])
        self.thick = float(p["thick"])
        self.plan_flat = float(p["plan_flat"])
        self.wrap_phi = float(p["wrap_phi"])
        self.w_top = float(p["w_top"])
        self.w_bot = float(p["w_bot"])
        self.corner_round = float(p["corner_round"])
        self.top_kind = str(p["top_kind"])
        self.bot_kind = str(p["bot_kind"])
        for k in ("horn_h", "horn_s", "horn_w", "arch_h", "dip_h", "val_h", "smile_h"):
            setattr(self, k, float(p[k]))
        # openings: list of (M,2) polygons in (s,v)
        self.openings = [np.asarray(o, float) for o in p.get("openings", [])]

        # plan-curve lookup: integrate turning angle psi(u) -> (X,Y), centred at u=0
        ud = np.linspace(-1.0, 1.0, 401)
        g = _smoothstep_ramp(ud, self.plan_flat, 1.0)
        psi = np.sign(ud) * self.wrap_phi * g
        du = ud[1] - ud[0]
        scale = self.W_lat / 2.0
        dx = np.cos(psi) * scale * du
        dy = np.sin(psi) * scale * du
        X = np.concatenate([[0.0], np.cumsum(0.5 * (dx[1:] + dx[:-1]))])
        Y = np.concatenate([[0.0], np.cumsum(0.5 * (dy[1:] + dy[:-1]))])
        mid = len(ud) // 2
        self._ud, self._Xlut, self._Ylut = ud, X - X[mid], Y - Y[mid]

        # forward-bulge profile over v
        P = float(p["protrude"])
        self._va = np.array([0.0, 0.22, float(p["bulge_v"]), 0.80, 1.0])
        self._fa = np.array([-float(p["chin"]) * P, 0.72 * P, 1.0 * P,
                             0.74 * P, -float(p["toproll"]) * P])

    # ---- param dict (for rec) ---------------------------------------------------
    def params(self):
        return dict(self.p)

    # ---- 1D component maps ------------------------------------------------------
    def plan(self, s):
        s = np.asarray(s, float)
        X = np.interp(s, self._ud, self._Xlut)
        Y = np.interp(s, self._ud, self._Ylut)
        psi = np.sign(s) * self.wrap_phi * _smoothstep_ramp(s, self.plan_flat, 1.0)
        return X, Y, np.sin(psi), -np.cos(psi)        # X, Y, front-normal (nx, ny), unit

    def profile_fwd(self, v):
        return np.interp(v, self._va, self._fa)

    def halfwidth(self, v):
        v = np.asarray(v, float)
        w = self.w_bot + (self.w_top - self.w_bot) * v
        bb = np.clip(v / max(self.corner_round, 1e-3), 0, 1)
        ease_b = np.sqrt(np.clip(1 - (1 - bb) ** 2, 0, 1))
        tt = np.clip((1 - v) / 0.10, 0, 1)
        ease_t = np.sqrt(np.clip(1 - (1 - tt) ** 2, 0, 1))
        return w * (0.6 + 0.4 * ease_b) * (0.9 + 0.1 * ease_t)

    def z_top(self, s):
        s = np.asarray(s, float)
        H, k = self.H, self.top_kind
        if k == "arch":
            return H * (1 + self.arch_h * (1 - s ** 2))
        if k == "dip":
            return H * (1 - self.dip_h * (1 - s ** 2))
        if k == "twin_horn":
            g = np.exp(-((np.abs(s) - self.horn_s) / self.horn_w) ** 2)
            center = np.clip(1 - (s / max(self.horn_s, 1e-3)) ** 2, 0, 1)
            return H * (1 + self.horn_h * g - 0.45 * self.dip_h * center)
        if k == "shoulder":
            return H * (1 + self.horn_h * 0.6 * np.clip((np.abs(s) - 0.35) / 0.65, 0, 1) ** 1.4)
        return H * (1 - 0.015 * s ** 2)

    def z_bot(self, s):
        s = np.asarray(s, float)
        if self.bot_kind == "valance":
            return -self.H * self.val_h * (1 - s ** 2)
        if self.bot_kind == "smile":
            return self.H * self.smile_h * s ** 2
        return np.zeros_like(s)

    # ---- 3D surface ------------------------------------------------------------
    def point(self, sv, recess=0.0):
        """FRONT-face point (meters). `recess` pushes it deeper along the front normal
        (used only when meshing the recessed grille)."""
        sv = np.asarray(sv, float)
        s, v = sv[:, 0], sv[:, 1]
        X, Y, nx, ny = self.plan(s)
        fwd = self.profile_fwd(v) - recess
        zt, zb = self.z_top(s), self.z_bot(s)
        z = zb + v * (zt - zb)
        return np.column_stack([X + nx * fwd, Y + ny * fwd, z])

    def outward_normal(self, sv, eps=2e-3):
        """Finite-difference unit normal of the FRONT face, oriented outward (toward -Y)."""
        sv = np.asarray(sv, float)
        P = self.point(sv)
        Ps = self.point(np.column_stack([np.clip(sv[:, 0] + eps, -1, 1), sv[:, 1]]))
        Pv = self.point(np.column_stack([sv[:, 0], np.clip(sv[:, 1] + eps, 0, 1)]))
        N = np.cross(Ps - P, Pv - P)
        N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
        N[N[:, 1] > 0] *= -1                          # point toward -Y (front / outward)
        return N

    def sample(self, sv, side="front", eps=2e-3):
        """(surface_point, outward_normal) in METERS for the requested face.

        front: the outer Class-A surface. back: currently the parallel inner offset, returned
        as its own (point, normal) so an asymmetric inner map can drop in here later."""
        P = self.point(sv)
        N = self.outward_normal(sv, eps=eps)
        if side == "back":
            return P - N * self.thick, -N            # inner face, normal into the body (+Y-ish)
        return P, N

    def inside(self, sv):
        """True where the shell exists: inside the tapered outline AND outside every opening."""
        sv = np.asarray(sv, float)
        m = np.abs(sv[:, 0]) <= self.halfwidth(sv[:, 1])
        for h in self.openings:
            m &= ~pip(sv, h)
        return m
