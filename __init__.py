"""
Hair Tool Stylized — Mesh Only (no curves, no geometry nodes).

Create hair sections as plain mesh from 2 verts or edge row.
Edit in Edit Mode; no control curves or GeoNodes.
"""

bl_info = {
    "name": "Hair Tool Stylized (Mesh)",
    "description": "Stylized hair sections as mesh only — no curves, no GeoNodes",
    "author": "Bartosz Styperek",
    "blender": (4, 2, 0),
    "location": "View 3D > N-Panel > Stylized Hair",
    "version": (1, 0, 0),
    "warning": "",
    "category": "Object"
}

if "bpy" in locals():
    import importlib
    from . import stylized_hair
    importlib.reload(stylized_hair)
else:
    from . import stylized_hair

import bpy


def register():
    stylized_hair.register()
    print("Registered Hair Tool Stylized (Mesh)")


def unregister():
    stylized_hair.unregister()
    print("Unregistered Hair Tool Stylized (Mesh)")


if __name__ == "__main__":
    register()
