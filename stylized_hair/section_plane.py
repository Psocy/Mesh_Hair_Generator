"""
Plane profile helpers for mesh-only: segments, length, box mesh, tree (root/child).
No Curve modifier, no ctrl, no GeoNodes.
"""

import bpy
from mathutils import Vector, Matrix

from ..utils.general_utils import link_obj_to_same_collections, set_parent


def _is_plane_profile(obj):
    """Mesh that is a hair profile (name contains _profile)."""
    return (
        obj is not None
        and obj.type == 'MESH'
        and '_profile' in getattr(obj, 'name', '')
    )


def _create_plane_box_mesh(name, height, hw, n_seg=8):
    """Single trunk 3D box mesh (Y=length, Z=±hw, X=±d2)."""
    height = max(1e-6, height)
    hw = max(1e-6, hw)
    d2 = max(1e-5, min(height, hw * 2) * 0.1)
    n_seg = max(1, n_seg)
    verts, faces = [], []
    for r in range(n_seg + 1):
        y = (r / n_seg) * height
        verts += [(-d2, y, -hw), (-d2, y, hw), (d2, y, hw), (d2, y, -hw)]
    for r in range(n_seg):
        i, j = r * 4, (r + 1) * 4
        faces += [
            (i + 0, i + 1, j + 1, j + 0), (i + 1, i + 2, j + 2, j + 1),
            (i + 2, i + 3, j + 3, j + 2), (i + 3, i + 0, j + 0, j + 3),
        ]
    faces += [(0, 1, 2, 3)]
    last = n_seg * 4
    faces += [(last + 0, last + 3, last + 2, last + 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _rebuild_plane_segments(obj, n):
    """Rebuild this profile mesh: one strip (가닥 1개), n segments along Y."""
    old = obj.data
    ys = [v.co.y for v in old.vertices]
    zs = [v.co.z for v in old.vertices]
    height = max(ys) - min(ys) if ys else 1.0
    if height < 1e-6:
        height = 1.0
    hw = (max(zs) - min(zs)) * 0.5 if len(zs) >= 2 else 0.1
    n_seg = max(1, n)
    verts, faces = _build_strands_verts_faces(height, hw, 1, n_seg)

    new_mesh = bpy.data.meshes.new(old.name)
    new_mesh.from_pydata(verts, [], faces)
    new_mesh.update()
    obj.data = new_mesh
    bpy.data.meshes.remove(old)

    sub = obj.modifiers.get('Subdivision')
    if sub:
        obj.modifiers.remove(sub)
    sub = obj.modifiers.new(name='Subdivision', type='SUBSURF')
    sub.subdivision_type = 'SIMPLE'
    sub.levels = 2


def _update_plane_segments(self, context):
    if not _is_plane_profile(self):
        return
    if not self.data or not self.data.vertices:
        return
    _rebuild_plane_segments(self, self.htool_plane_segments)
    if context and getattr(context, 'view_layer', None):
        context.view_layer.update()


def _update_plane_length(self, context):
    """Rescale profile mesh Y extent to new length (mesh-only, no curve)."""
    if not _is_plane_profile(self):
        return
    obj = self
    new_length = max(0.01, getattr(self, 'htool_plane_length', 1.0))
    if not obj.data.vertices:
        return
    ys = [v.co.y for v in obj.data.vertices]
    min_y = min(ys)
    max_y = max(ys)
    old_extent = max(max_y - min_y, 1e-6)
    for v in obj.data.vertices:
        v.co.y = (v.co.y - min_y) / old_extent * new_length
    obj.data.update()


def _active_plane_profile(context):
    """Return selected profile mesh if active object is a profile."""
    obj = context.active_object
    if obj is None:
        return None
    if _is_plane_profile(obj):
        return obj
    return None


def _is_root_profile(obj):
    """Profile that is a root (parent is Empty *_hair). 가닥 = 루트 하나."""
    if not _is_plane_profile(obj):
        return False
    p = obj.parent
    return p is not None and p.type == 'EMPTY' and '_hair' in getattr(p, 'name', '')


def _get_child_profiles(profile_obj):
    """Direct children that are profile meshes (for tree)."""
    if not profile_obj or not hasattr(profile_obj, 'children'):
        return []
    return sorted(
        [c for c in profile_obj.children if _is_plane_profile(c)],
        key=lambda x: x.name
    )


def _get_root_profiles():
    """All root profile objects (parent = Empty *_hair or no parent)."""
    return sorted(
        [o for o in bpy.data.objects if _is_root_profile(o)],
        key=lambda x: x.name
    )


def _orient_from_y(pos, y_axis):
    """4x4 matrix: col0=depth, col1=y_axis, col2=width, translation=pos."""
    up = Vector((0, 0, 1))
    if abs(y_axis.dot(up)) > 0.99:
        up = Vector((1, 0, 0))
    x_axis = y_axis.cross(up).normalized()
    z_axis = x_axis.cross(y_axis).normalized()
    x_axis = y_axis.cross(z_axis).normalized()
    return Matrix((
        (x_axis.x, y_axis.x, z_axis.x, pos.x),
        (x_axis.y, y_axis.y, z_axis.y, pos.y),
        (x_axis.z, y_axis.z, z_axis.z, pos.z),
        (0, 0, 0, 1),
    ))


def _build_strands_verts_faces(height, hw, strand_count, n_seg, depth_ratio=0.08):
    """Return (verts, faces) for strands grid. X=depth, Y=length, Z=width. depth_ratio: 두께 비율(0에 가까우면 카드처럼)."""
    depth = max(1e-5, (2 * hw) * depth_ratio)
    d2 = depth * 0.5
    n_r = n_seg + 1
    n_s = strand_count + 1
    verts = []
    for r in range(n_r):
        y = (r / n_seg) * height if n_seg else 0.0
        for s in range(n_s):
            z = -hw + (s / max(strand_count, 1)) * (2.0 * hw) if strand_count >= 1 else 0.0
            verts.append((-d2, y, z))
            verts.append((d2, y, z))
    faces = []
    for r in range(n_seg):
        for s in range(strand_count):
            i00 = (r * n_s + s) * 2
            i01 = (r * n_s + (s + 1)) * 2
            i10 = ((r + 1) * n_s + s) * 2
            i11 = ((r + 1) * n_s + (s + 1)) * 2
            faces.append((i00, i10, i11, i01))
            faces.append((i00 + 1, i01 + 1, i11 + 1, i10 + 1))
            faces.append((i00, i01, i01 + 1, i00 + 1))
            faces.append((i10, i11, i11 + 1, i10 + 1))
            faces.append((i00, i10, i10 + 1, i00 + 1))
            faces.append((i01, i11, i11 + 1, i01 + 1))
    return verts, faces


def create_strands_mesh_at_orient(profile_name, orient, height, hw, strand_count, n_seg, parent_obj, col_src, depth_ratio=0.08):
    """Create one strands mesh object at given orient (mesh-only, no curve). depth_ratio: 0.02=얇은 카드, 0.08=기본 두께."""
    verts, faces = _build_strands_verts_faces(height, hw, strand_count, n_seg, depth_ratio)
    mesh_data = bpy.data.meshes.new(profile_name)
    mesh_data.from_pydata(verts, [], faces)
    mesh_data.update()
    profile_obj = bpy.data.objects.new(profile_name, mesh_data)
    profile_obj.matrix_world = orient
    link_obj_to_same_collections(col_src, profile_obj)
    set_parent(profile_obj, parent_obj)
    sub_mod = profile_obj.modifiers.new(name='Subdivision', type='SUBSURF')
    sub_mod.subdivision_type = 'SIMPLE'
    sub_mod.levels = 2
    return profile_obj
