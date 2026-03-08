"""Stylized Hair UI: Hair Tree (root → branches), Select Profile, Strands panel."""

import bpy
from .section_plane import _active_plane_profile, _get_root_profiles, _get_child_profiles


class HTOOL_OT_SelectProfile(bpy.types.Operator):
    bl_idname = "hair_system.select_profile"
    bl_label = ""
    obj_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.obj_name)
        if obj:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj
        return {'FINISHED'}


def _draw_profile_tree(layout, profile_obj, active_obj, depth=0):
    row = layout.row(align=True)
    for _ in range(depth):
        row.label(icon='BLANK1', text="")
    is_active = profile_obj == active_obj
    op = row.operator(
        "hair_system.select_profile",
        text=profile_obj.name.replace('_profile', '').replace('_branch', ''),
        icon='RADIOBUT_ON' if is_active else 'MESH_DATA',
        emboss=is_active,
    )
    op.obj_name = profile_obj.name
    for child in _get_child_profiles(profile_obj):
        _draw_profile_tree(layout, child, active_obj, depth + 1)


class HTOOL_PT_StylizedHairMesh(bpy.types.Panel):
    bl_label = "Hair Section"
    bl_idname = "HTOOL_PT_StylizedHairMesh"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Stylized Hair'
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        sub = col.column()
        sub.enabled = (context.mode == 'EDIT_MESH')
        sub.operator("hair_system.create_hair_section", icon='ADD', text='Create Hair Section')
        if context.mode != 'EDIT_MESH':
            col.label(text="Run in Edit Mode on scalp mesh", icon='INFO')

        layout.separator()
        layout.label(text="Hair Tree", icon='OUTLINER')
        box = layout.box()
        root_profiles = _get_root_profiles()
        if root_profiles:
            for root in root_profiles:
                _draw_profile_tree(box, root, context.active_object)
        else:
            box.label(text="No hair sections yet", icon='INFO')

        target_profile = _active_plane_profile(context)
        if target_profile is None:
            return

        is_root = target_profile.parent and target_profile.parent.type == 'EMPTY' and '_hair' in getattr(target_profile.parent, 'name', '')

        layout.separator()
        box = layout.box()
        box.label(text="Root" if is_root else "Branch", icon='MOD_MESHDEFORM')
        row = box.row(align=True)
        row.prop(target_profile, 'htool_plane_segments', text="Segments")
        row = box.row(align=True)
        row.prop(target_profile, 'htool_plane_length', text="Length")

        scene = context.scene
        box_s = layout.box()
        box_s.label(text="Split Branch (특정 높이에서 rip)", icon='MOD_EXPLODE')
        box_s.label(text="쭉 이어지다가 그 높이에서만 갈라짐", icon='NONE')
        row = box_s.row(align=True)
        row.prop(scene, 'htool_split_branch_split_t', text="Split At")
        row = box_s.row(align=True)
        row.prop(scene, 'htool_split_branch_count', text="Count")
        row = box_s.row(align=True)
        row.prop(scene, 'htool_split_branch_spread_angle', text="Spread Angle°")
        if not is_root:
            op = box_s.operator("hair_system.add_split_branch", icon='ADD', text="Add Branches")
            op.split_t = scene.htool_split_branch_split_t
            op.count = scene.htool_split_branch_count
            op.spread_angle = scene.htool_split_branch_spread_angle
