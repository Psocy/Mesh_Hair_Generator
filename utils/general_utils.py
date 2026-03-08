# Minimal utils for mesh-only addon (no curves/geonodes)

import bpy


def get_addon_name():
    return __package__.split(".")[0]


def addon_name_lowercase():
    return get_addon_name().lower()


def get_addon_preferences():
    name = get_addon_name()
    if name not in bpy.context.preferences.addons:
        return None
    return bpy.context.preferences.addons[name].preferences


def set_parent(obj, new_parent):
    if obj.parent:
        old_parent_m_w = obj.parent.matrix_world.copy()
        backup_obj_mpi = obj.matrix_parent_inverse.copy()
        obj.parent = new_parent
        obj.matrix_parent_inverse = new_parent.matrix_world.inverted() @ old_parent_m_w @ backup_obj_mpi
    else:
        obj.parent = new_parent
        obj.matrix_parent_inverse = new_parent.matrix_world.inverted()


def link_obj_to_same_collections(source_obj, clone, force_linking=True):
    for col in source_obj.users_collection:
        if clone.name not in col.objects:
            col.objects.link(clone)
    if not source_obj.users_collection and clone.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(clone)
