"""
Split branch (mesh-only): 루트 메쉬를 세로로 N분할하여 split_t 높이에서 rip.
항상 저장된 원본 파라미터(length_full, hw)로 처음부터 재빌드 — 상태 누적 없음.
"""

import bpy
from .section_plane import (
    _build_strands_verts_faces,
    _get_child_profiles,
    _is_root_profile,
)


_updating_split_branch = False


def _remove_children_recursive(profile_obj):
    for child in list(_get_child_profiles(profile_obj)):
        _remove_children_recursive(child)
        bpy.data.objects.remove(child, do_unlink=True)


def _unique_name(base):
    i = 1
    while bpy.data.objects.get(f"{base}{i}_profile"):
        i += 1
    return f"{base}{i}"


def _build_ripped_mesh(length_full, hw, split_t, n_branches, n_seg):
    """원본 파라미터로 항상 새로 빌드: 루트(전체 너비) + N갈래(너비 1/N씩)."""
    root_len = split_t * length_full
    branch_len = max(length_full - root_len, 0.05)
    hw_branch = hw / n_branches

    combined_verts = []
    combined_faces = []

    # 루트 구간: 전체 너비
    verts_r, faces_r = _build_strands_verts_faces(root_len, hw, 1, n_seg)
    combined_verts.extend(verts_r)
    combined_faces.extend(faces_r)
    n_offset = len(verts_r)

    # 브랜치 구간: N개 strip (각각 hw/N 너비, 원래 폭 안에서 나란히)
    # depth_ratio를 n배 키워서 X축 두께는 루트와 동일하게 유지
    branch_depth_ratio = n_branches * 0.08
    for i in range(n_branches):
        z_center = -hw + (i + 0.5) * (2.0 * hw / n_branches)
        verts_b, faces_b = _build_strands_verts_faces(branch_len, hw_branch, 1, n_seg, branch_depth_ratio)
        for v in verts_b:
            combined_verts.append((v[0], v[1] + root_len, v[2] + z_center))
        for f in faces_b:
            combined_faces.append(tuple(idx + n_offset for idx in f))
        n_offset += len(verts_b)

    return combined_verts, combined_faces


def rebuild_branches_for_root(parent, split_t, count, spread_angle, context, select_new_branches=False):
    global _updating_split_branch
    if _updating_split_branch:
        return
    _updating_split_branch = True
    try:
        _remove_children_recursive(parent)

        # 원본 파라미터 복원 — 없으면 현재 메쉬에서 읽고 저장 (최초 1회)
        length_full = getattr(parent, 'htool_plane_length_full', None)
        if not length_full or length_full < 1e-6:
            ys = [v.co.y for v in parent.data.vertices]
            length_full = (max(ys) - min(ys)) if ys else 1.0
            parent.htool_plane_length_full = length_full

        hw = getattr(parent, 'htool_plane_hw', None)
        if not hw or hw < 1e-6:
            zs = [v.co.z for v in parent.data.vertices]
            hw = (max(zs) - min(zs)) * 0.5 if zs else 0.1
            parent.htool_plane_hw = hw

        n_branches = max(2, min(8, count))
        n_seg = max(2, getattr(parent, 'htool_plane_segments', 8))

        verts, faces = _build_ripped_mesh(length_full, hw, split_t, n_branches, n_seg)

        mesh_name = parent.data.name
        new_mesh = bpy.data.meshes.new(mesh_name)
        new_mesh.from_pydata(verts, [], faces)
        new_mesh.update()
        old_mesh = parent.data
        parent.data = new_mesh
        bpy.data.meshes.remove(old_mesh)

        sub = parent.modifiers.get('Subdivision')
        if sub is None:
            sub = parent.modifiers.new(name='Subdivision', type='SUBSURF')
            sub.subdivision_type = 'SIMPLE'
            sub.levels = 2

        if context:
            context.view_layer.update()
        if select_new_branches and context:
            bpy.ops.object.select_all(action='DESELECT')
            parent.select_set(True)
            context.view_layer.objects.active = parent
    finally:
        _updating_split_branch = False


def _update_split_branch_live(self, context):
    if not context or not context.active_object:
        return
    obj = context.active_object
    if obj.type != 'MESH' or not obj.name.endswith('_profile'):
        return
    if not _is_root_profile(obj):
        return
    split_t = getattr(self, 'htool_split_branch_split_t', 0.5)
    count = getattr(self, 'htool_split_branch_count', 2)
    spread = getattr(self, 'htool_split_branch_spread_angle', 25.0)
    rebuild_branches_for_root(obj, split_t, count, spread, context, select_new_branches=False)


class HTOOL_OT_AddSplitBranch(bpy.types.Operator):
    bl_idname = "hair_system.add_split_branch"
    bl_label = "Add Split Branch"
    bl_options = {'REGISTER', 'UNDO'}

    split_t: bpy.props.FloatProperty(name='Split At', min=0.01, max=0.99, default=0.5)
    count: bpy.props.IntProperty(name='Count', min=2, max=8, default=2)
    spread_angle: bpy.props.FloatProperty(name='Spread Angle°', min=1.0, max=90.0, default=12.0)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH' or not obj.name.endswith('_profile'):
            return False
        return context.mode == 'OBJECT'

    def execute(self, context):
        parent = context.active_object
        rebuild_branches_for_root(
            parent, self.split_t, self.count, self.spread_angle,
            context, select_new_branches=True,
        )
        scene = context.scene
        if hasattr(scene, 'htool_split_branch_split_t'):
            scene.htool_split_branch_split_t = self.split_t
        if hasattr(scene, 'htool_split_branch_count'):
            scene.htool_split_branch_count = self.count
        if hasattr(scene, 'htool_split_branch_spread_angle'):
            scene.htool_split_branch_spread_angle = self.spread_angle
        self.report({'INFO'}, "Mesh rip 완료.")
        return {'FINISHED'}
