"""Mesh-only: surface normal helper for section creation."""

from mathutils import Vector
from mathutils.bvhtree import BVHTree


def surface_normal_at_point(mesh_data, point_local):
    """Return face normal at closest point on mesh (object local space)."""
    if not mesh_data or not mesh_data.polygons:
        return None
    try:
        verts = [mesh_data.vertices[i].co.copy() for i in range(len(mesh_data.vertices))]
        polys = [list(p.vertices) for p in mesh_data.polygons]
        bvh = BVHTree.FromPolygons(verts, polys)
        hit, normal, idx, dist = bvh.find_nearest(point_local)
        if normal is not None:
            return normal.normalized()
    except Exception:
        pass
    if mesh_data.polygons:
        return mesh_data.polygons[0].normal.copy().normalized()
    return None
