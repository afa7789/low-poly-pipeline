#!/usr/bin/env python3
"""Dense test mesh of a signed-distance grid, numpy only (PIPELINE 28.L10-3: input of retopo.py in python3.14 tests).

    verts, tris = surface_nets(grid, origin, voxel)

Naive surface nets (one vertex per mixed cell, the mean of its edge crossings; one quad per sign-changing grid edge, split on
the shorter diagonal). Same family as openvdb's convertToPolygons(adaptivity 0) that the build uses: about two triangles per
surface voxel, rounded edges, closed when the field is positive on the grid's border. Outward normals (negative inside).
"""
import numpy as np

CORNERS = np.array([(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)])
EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8) if (CORNERS[a] != CORNERS[b]).sum() == 1]
# the 4 cells around a grid edge along axis x / y / z: offsets of the cell (lower corner) from the edge's lower end
RING = {0: [(0, -1, -1), (0, 0, -1), (0, 0, 0), (0, -1, 0)],
        1: [(-1, 0, -1), (-1, 0, 0), (0, 0, 0), (0, 0, -1)],
        2: [(-1, -1, 0), (0, -1, 0), (0, 0, 0), (-1, 0, 0)]}


def cell_vertices(grid):
    """(cell id of each mixed cell (nx-1, ny-1, nz-1) or -1, vertex positions in grid units (m, 3))."""
    shape = np.array(grid.shape) - 1
    corner = np.stack([grid[i:i + shape[0], j:j + shape[1], k:k + shape[2]] for i, j, k in CORNERS])
    mixed = (corner < 0).any(0) & (corner >= 0).any(0)
    total, count = np.zeros((*shape, 3)), np.zeros(shape)
    for a, b in EDGES:
        va, vb = corner[a], corner[b]
        cross = (va < 0) != (vb < 0)
        t = np.where(cross, va / np.where(cross, va - vb, 1.0), 0.0)
        total += cross[..., None] * (CORNERS[a] + t[..., None] * (CORNERS[b] - CORNERS[a]))
        count += cross
    ids = np.full(shape, -1)
    ids[mixed] = np.arange(mixed.sum())
    base = np.stack(np.meshgrid(*[np.arange(s) for s in shape], indexing="ij"), -1)
    return ids, (total / np.maximum(count, 1)[..., None] + base)[mixed]


def quads(grid, ids):
    """(q, 4) cell ids around every sign-changing interior grid edge, wound so the normal points out of the negative side."""
    out = []
    for axis, ring in RING.items():
        lo = [slice(1, s - 1) for s in grid.shape]
        hi = list(lo)
        hi[axis] = slice(2, grid.shape[axis])
        lo[axis] = slice(1, grid.shape[axis] - 1)
        a, b = grid[tuple(lo)], grid[tuple(hi)]
        pts = np.argwhere((a < 0) != (b < 0)) + 1
        cells = np.stack([ids[tuple((pts + off).T)] for off in ring], 1)
        flip = (grid[tuple(pts.T)] >= 0)[:, None]
        out.append(np.where(flip, cells[:, ::-1], cells))
    return np.concatenate(out)


def surface_nets(grid, origin, voxel):
    """(verts (m, 3), tris (f, 3)) of the zero set of an (nx, ny, nz) grid; origin and voxel as sdf_body.Field."""
    ids, pos = cell_vertices(np.asarray(grid, np.float64))
    q = quads(np.asarray(grid, np.float64), ids)
    q = q[(q >= 0).all(1)]
    short = np.linalg.norm(pos[q[:, 0]] - pos[q[:, 2]], axis=1) <= np.linalg.norm(pos[q[:, 1]] - pos[q[:, 3]], axis=1)
    tris = np.concatenate([np.where(short[:, None], q[:, [0, 1, 2]], q[:, [1, 2, 3]]),
                           np.where(short[:, None], q[:, [0, 2, 3]], q[:, [1, 3, 0]])])
    verts = np.asarray(origin) + voxel * pos
    vol = np.einsum("fd,fd->f", verts[tris[:, 0]], np.cross(verts[tris[:, 1]], verts[tris[:, 2]])).sum()
    return verts, (tris[:, ::-1] if vol < 0 else tris)
