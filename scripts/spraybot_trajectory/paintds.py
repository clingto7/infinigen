"""Native Spraybot PaintDS convention: XYZ in mm, ZYX Euler, tool Z aims at surface."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


def aim_to_zyx_deg(aim: np.ndarray) -> np.ndarray:
    z = np.array(aim, dtype=float, copy=True)
    z /= np.linalg.norm(z, axis=1, keepdims=True)
    up = np.broadcast_to([0.0, 0.0, 1.0], z.shape)
    x = np.cross(up, z)
    vertical = np.linalg.norm(x, axis=1) < 1e-3
    x[vertical] = np.array([1.0, 0.0, 0.0]) - z[vertical] * z[vertical, :1]
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    y = np.cross(z, x)
    matrices = np.stack((x, y, z), axis=-1)
    return Rotation.from_matrix(matrices).as_euler("ZYX", degrees=True)


def euler_zyx_to_aim(angles: np.ndarray) -> np.ndarray:
    return Rotation.from_euler("ZYX", np.asarray(angles), degrees=True).apply([0, 0, 1])


def write_paintds(strokes: list, path: Path) -> None:
    rows = ["X;Y;Z;A;B;C;strokeId"]
    for sid, stroke in enumerate(strokes):
        abc = aim_to_zyx_deg(stroke.aim.copy())
        for point, angle in zip(stroke.positions_mm, abc):
            rows.append(f"{point[0]:.6f};{point[1]:.6f};{point[2]:.6f};"
                        f"{angle[0]:.4f};{angle[1]:.4f};{angle[2]:.4f};{sid}.0")
    path.write_text("\n".join(rows) + "\n")
