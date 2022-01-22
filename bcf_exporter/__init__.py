import bpy
from .export import BCFExporter

"""
Author: Bowie
This exporter defines a pretty basic export for
OGL compatible vertex buffer

Vertex Format (using bit position to toggle availability):
(1 << 0) : POSITION
(1 << 1) : NORMAL
(1 << 2) : UV0
(1 << 3) : TANGENT + BITANGENT
(1 << 4) : UV1 (NOT IMPLEMENTED YET)
(1 << 5) : COLOR (NOT IMPLEMENTED YET)
(1 << 6) : BONE_WEIGHTS + IDS (NOT IMPLEMENTED YET)
(1 << 7) : TWEEN (NOT IMPLEMENTED YET)
"""

bl_info = {
    "name": "Bowie Custom Format Exporter",
    "author": "Bowie",
    "blender": (2, 82, 0),
    "version": (0, 0, 1),
    "location": "File > Import-Export",
    "description": "Export BCF File",
    "category": "Import-Export"
}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(BCFExporter.bl_idname, text="BCF Export")


def register():
    bpy.utils.register_class(BCFExporter)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(BCFExporter)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    # bpy.ops.bcf_exporter.export('INVOKE_DEFAULT')
