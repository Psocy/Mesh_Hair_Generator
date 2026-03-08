"""
Create Hair Section (mesh only): 2 verts or edge row → strands mesh (가닥 시스템).
Multiple strands (가닥) as mesh, no curves, no GeoNodes.
"""

import bpy
import bmesh
from mathutils import Vector, Matrix

from ..utils.general_utils import link_obj_to_same_collections, set_parent
from .profile import surface_normal_at_point
from .section_plane import create_strands_mesh_at_orient
from .section_branch import rebuild_branches_for_root

# 가닥 = 헤어 트리에서 루트 하나. 직사각형(2 vert/edge row)을 헤어 너비로 나눈 수만큼 루트 프로필 생성.


class HTOOL_OT_CreateHairSection(bpy.types.Operator):
    """Create hair section as mesh strands from 2 vertices (root line) or one row of edges."""
    bl_idname = "hair_system.create_hair_section"
    bl_label = "Create Hair Section"
    bl_description = (
        "Strands = 완전한 갈라짐 (from the start). "
        "Select 2 verts or edge row → mesh strands. Edit in Edit Mode."
    )
    bl_options = {'REGISTER', 'UNDO'}

    strand_count: bpy.props.IntProperty(
        name="Strands",
        description="완전한 갈라짐: 루트에서부터 나뉜 가닥 수 (number of strands from the start)",
        min=1, max=64, default=8,
    )
    segments: bpy.props.IntProperty(
        name="Segments",
        description="Segments along length (root→tip) per strand",
        min=1, max=64, default=8,
    )

    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None
            and context.active_object.type == 'MESH'
            and context.mode == 'EDIT_MESH'
        )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=320)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "strand_count")
        layout.prop(self, "segments")

    def execute(self, context):
        scalp_obj = context.active_object
        base_name = scalp_obj.name.replace("_scalp", "").replace("Scalp", "")
        profile_name = f"{base_name}_profile"

        root_chain, parallel_chain = self._two_verts_to_rectangle(scalp_obj)
        if root_chain is None:
            root_chain, parallel_chain = self._selected_edge_row_to_quad(scalp_obj)
        if root_chain is None:
            self.report(
                {'ERROR'},
                "Select 2 vertices (root line) OR one row of edges (open chain, 2 endpoints)."
            )
            return {'CANCELLED'}

        world_mat = scalp_obj.matrix_world.copy()
        bpy.ops.object.mode_set(mode='OBJECT')

        hair_group_name = f"{base_name}_hair"
        hair_group = bpy.data.objects.new(hair_group_name, None)
        link_obj_to_same_collections(scalp_obj, hair_group)
        hair_group.matrix_world = Matrix.Identity(4)

        n_strands = max(1, self.strand_count)
        n_seg = max(1, self.segments)
        profile_objs = self._create_root_strands(
            root_chain, parallel_chain, world_mat, base_name, hair_group, n_strands, n_seg
        )
        if not profile_objs:
            self.report({'ERROR'}, "Could not build hair section (degenerate geometry?).")
            return {'CANCELLED'}

        for p in profile_objs:
            full_h = self._profile_height(p)
            p.htool_plane_length = full_h
            p.htool_plane_length_full = full_h
            p.htool_plane_segments = n_seg

        # rip(갈라짐)은 Create 시 적용하지 않음. 가닥만 만든 뒤, 필요하면 Add Branches로 적용.
        context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        profile_objs[0].select_set(True)
        context.view_layer.objects.active = profile_objs[0]
        self.report({'INFO'}, f"Hair Section '{base_name}': {n_strands} root strands (가닥).")
        return {'FINISHED'}

    def _profile_height(self, profile_obj):
        ys = [v.co.y for v in profile_obj.data.vertices]
        return max(ys) - min(ys) if ys else 1.0

    def _surface_normal_at_point(self, mesh_data, point_local):
        return surface_normal_at_point(mesh_data, Vector(point_local))

    def _two_verts_to_rectangle(self, mesh_obj):
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        bm.verts.ensure_lookup_table()
        selected_verts = [v for v in bm.verts if v.select]
        if len(selected_verts) != 2:
            return None, None
        v0 = selected_verts[0].co.copy()
        v1 = selected_verts[1].co.copy()
        root_chain = [v0, v1]
        center = (v0 + v1) * 0.5
        normal = self._surface_normal_at_point(mesh_obj.data, center)
        if normal is None or normal.length_squared < 1e-10:
            normal = Vector((0, 0, 1))
        else:
            normal = normal.normalized()
        root_dir = (v1 - v0)
        length = root_dir.length
        if length < 1e-6:
            return None, None
        root_dir = root_dir / length
        perp = root_dir.cross(normal)
        if perp.length_squared < 1e-10:
            perp = Vector((0, 1, 0)) if abs(root_dir.z) < 0.9 else Vector((1, 0, 0))
        perp = perp.normalized()
        width = length
        offset = width * perp
        parallel_chain = [v0 + offset, v1 + offset]
        return root_chain, parallel_chain

    def _create_root_strands(self, root_chain, parallel_chain, world_mat, base_name, parent_obj,
                             strand_count, n_seg):
        """한 오브젝트·한 메쉬에 가닥 전부 붙여서 만듦. 갈라진 플랭크/틈 없음."""
        w0 = world_mat @ root_chain[0]
        w1 = world_mat @ root_chain[-1]
        wp0 = world_mat @ parallel_chain[0]
        wp1 = world_mat @ parallel_chain[-1]

        root_center = (w0 + w1) * 0.5
        tip_center = (wp0 + wp1) * 0.5
        width = (w1 - w0).length
        height = (tip_center - root_center).length
        if width < 1e-6 or height < 1e-6:
            return []

        y_axis = (tip_center - root_center).normalized()
        hair_w = (w1 - w0).normalized()
        z_axis = hair_w.cross(y_axis)
        z_axis = z_axis.normalized() if z_axis.length_squared > 1e-10 else Vector((0, 0, 1))
        hair_w = y_axis.cross(z_axis).normalized()

        hw_total = width * 0.5
        orient = Matrix((
            (z_axis.x, y_axis.x, hair_w.x, root_center.x),
            (z_axis.y, y_axis.y, hair_w.y, root_center.y),
            (z_axis.z, y_axis.z, hair_w.z, root_center.z),
            (0, 0, 0, 1),
        ))
        name = f"{base_name}_profile"
        obj = create_strands_mesh_at_orient(
            name, orient, height, hw_total, strand_count, n_seg, parent_obj, parent_obj,
            depth_ratio=0.02,
        )
        return [obj]

    def _order_edges_to_chain(self, bm, edge_list):
        if not edge_list:
            return []
        adj = {}
        for e in edge_list:
            a, b = e.verts[0].index, e.verts[1].index
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        start = None
        for vid, neigs in adj.items():
            if len(neigs) == 1:
                start = vid
                break
        if start is None:
            start = next(iter(adj))
        chain = []
        seen = set()
        cur = start
        while cur is not None:
            seen.add(cur)
            chain.append(bm.verts[cur].co.copy())
            next_v = None
            for n in adj.get(cur, []):
                if n not in seen:
                    next_v = n
                    break
            cur = next_v
        return chain

    def _selected_edge_row_to_quad(self, mesh_obj):
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        selected_edges = [e for e in bm.edges if e.select]
        if not selected_edges:
            return None, None

        strip_faces = [f for f in bm.faces if any(e.select for e in f.edges)]
        if not strip_faces:
            return None, None

        def edge_key(e):
            return (min(e.verts[0].index, e.verts[1].index), max(e.verts[0].index, e.verts[1].index))

        selected_set = {edge_key(e) for e in selected_edges}
        edge_face_count = {}
        for f in strip_faces:
            for e in f.edges:
                k = edge_key(e)
                edge_face_count[k] = edge_face_count.get(k, 0) + 1
        boundary_keys = {k for k, c in edge_face_count.items() if c == 1}
        parallel_keys = boundary_keys - selected_set
        if not parallel_keys:
            return None, None
        parallel_edges = [e for e in bm.edges if edge_key(e) in parallel_keys]

        root_chain = self._order_edges_to_chain(bm, selected_edges)
        parallel_chain = self._order_edges_to_chain(bm, parallel_edges)
        if not root_chain or not parallel_chain:
            return None, None

        adj_sel = {}
        for e in selected_edges:
            a, b = e.verts[0].index, e.verts[1].index
            adj_sel.setdefault(a, []).append(b)
            adj_sel.setdefault(b, []).append(a)
        endpoints = [v for v, neigs in adj_sel.items() if len(neigs) == 1]
        if len(endpoints) != 2:
            return None, None

        d0 = (parallel_chain[0] - root_chain[0]).length_squared
        d1 = (parallel_chain[-1] - root_chain[0]).length_squared
        if d1 < d0:
            parallel_chain = list(reversed(parallel_chain))

        for f in bm.faces:
            f.select = f in strip_faces
        bmesh.update_edit_mesh(mesh_obj.data)
        return root_chain, parallel_chain
