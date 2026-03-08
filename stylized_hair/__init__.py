"""Stylized hair — mesh only, tree structure (no curves, no GeoNodes)."""

import bpy

from .section_creation import HTOOL_OT_CreateHairSection
from .section import register as section_register, unregister as section_unregister
from .section_branch import HTOOL_OT_AddSplitBranch
from .ui import HTOOL_PT_StylizedHairMesh, HTOOL_OT_SelectProfile


def register():
    section_register()
    bpy.utils.register_class(HTOOL_OT_CreateHairSection)
    bpy.utils.register_class(HTOOL_OT_AddSplitBranch)
    bpy.utils.register_class(HTOOL_OT_SelectProfile)
    bpy.utils.register_class(HTOOL_PT_StylizedHairMesh)


def unregister():
    bpy.utils.unregister_class(HTOOL_PT_StylizedHairMesh)
    bpy.utils.unregister_class(HTOOL_OT_SelectProfile)
    bpy.utils.unregister_class(HTOOL_OT_AddSplitBranch)
    bpy.utils.unregister_class(HTOOL_OT_CreateHairSection)
    section_unregister()
