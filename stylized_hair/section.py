"""
Hair section (mesh-only): register operators and properties.
Tree structure (root → branches), no curves, no GeoNodes.
"""

import bpy

from .section_creation import HTOOL_OT_CreateHairSection
from .section_plane import (
    _update_plane_segments,
    _update_plane_length,
    _active_plane_profile,
    _is_plane_profile,
)
from .section_branch import HTOOL_OT_AddSplitBranch, _update_split_branch_live


def register():
    bpy.types.Object.htool_plane_segments = bpy.props.IntProperty(
        name="Segments",
        description="Segments along length (root→tip) per strand",
        min=1, max=64, default=8,
        update=_update_plane_segments,
    )
    bpy.types.Object.htool_plane_length = bpy.props.FloatProperty(
        name="Length",
        description="Hair section length (Y direction)",
        min=0.01, soft_max=10.0, default=1.0,
        unit='LENGTH',
        update=_update_plane_length,
    )
    bpy.types.Object.htool_plane_length_full = bpy.props.FloatProperty(
        name="Length (full)",
        description="Full length before branch split; used to keep split position",
        min=0.01, soft_max=10.0, default=1.0,
        unit='LENGTH',
    )
    bpy.types.Object.htool_plane_hw = bpy.props.FloatProperty(
        name="Half Width (original)",
        description="Original half-width stored at branch creation; prevents drift on repeated edits",
        min=0.0, soft_max=10.0, default=0.0,
        unit='LENGTH',
    )
    bpy.types.Scene.htool_split_branch_split_t = bpy.props.FloatProperty(
        name="Split At",
        description="Branch = 특정 높이에서의 갈라짐. Height ratio (0~1) where branches split off",
        min=0.01, max=0.99, default=0.5,
        update=_update_split_branch_live,
    )
    bpy.types.Scene.htool_split_branch_count = bpy.props.IntProperty(
        name="Count",
        description="Number of branches at this height",
        min=2, max=8, default=2,
        update=_update_split_branch_live,
    )
    bpy.types.Scene.htool_split_branch_spread_angle = bpy.props.FloatProperty(
        name="Spread Angle°",
        description="Rip = 작은 각도로 갈라짐. 너무 크면 90도 꺾인 것처럼 보임 (1~30 권장)",
        min=1.0, max=90.0, default=12.0,
        soft_max=30.0,
        update=_update_split_branch_live,
    )


def unregister():
    if hasattr(bpy.types.Object, 'htool_plane_segments'):
        del bpy.types.Object.htool_plane_segments
    if hasattr(bpy.types.Object, 'htool_plane_length'):
        del bpy.types.Object.htool_plane_length
    if hasattr(bpy.types.Object, 'htool_plane_length_full'):
        del bpy.types.Object.htool_plane_length_full
    if hasattr(bpy.types.Object, 'htool_plane_hw'):
        del bpy.types.Object.htool_plane_hw
    if hasattr(bpy.types.Scene, 'htool_split_branch_split_t'):
        del bpy.types.Scene.htool_split_branch_split_t
    if hasattr(bpy.types.Scene, 'htool_split_branch_count'):
        del bpy.types.Scene.htool_split_branch_count
    if hasattr(bpy.types.Scene, 'htool_split_branch_spread_angle'):
        del bpy.types.Scene.htool_split_branch_spread_angle
