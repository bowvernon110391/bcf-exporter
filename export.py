import bpy

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
VTF_POS     = (1<<0)
VTF_NORMAL  = (1<<1)
VTF_UV0     = (1<<2)
VTF_TANGENT_BITANGENT      = (1<<3)
VTF_UV1     = (1<<4)
VTF_COLOR   = (1<<5)
VTF_BONE_DATA   = (1<<6)
VTF_TWEEN   = (1<<7)

VTF_DEFAULT = VTF_POS | VTF_NORMAL | VTF_UV0

###
# buildBuffers: return tuple of vb and ib
def buildBuffers(obj, report=None, format=VTF_DEFAULT):
    
    # mesh
    m = obj.data
    
    # make sure it's a mesh
    if type(m) != bpy.types.Mesh:
        print("OBJECT DATA IS NOT MESH!")
        if report != None:
            report({'ERROR'}, "Object data is not a <Mesh>!")
        return (None, None)
    
    # make sure it has 1 uv map
    if (len(m.uv_layers) < 1):
        print("NO UV MAP FOUND!")
        if report != None:
            report({'ERROR'}, "AT LEAST 1 UV MAP MUST BE CREATED!")
        return (None, None)
    
    # start
    print("BCF_START_BUILDING_BUFFERS...\n")
    # compute data
    print("BCF_COMPUTE_TRIANGLES...\n")
    m.calc_loop_triangles()

    print("BCF_COMPUTE_SPLIT_NORMALS...\n")
    m.calc_normals_split()

    print("BCF_COMPUTE_TANGENTS...\n")
    m.calc_tangents()
    
    # now we access the data
    # the mesh loops (for v_idx, normal, tangent, bitangent)
    mls = m.loops
    print("BCF_DISCOVERED: Loops(%d)\n" % len(mls))
    # vertex list
    verts = m.vertices
    print("BCF_DISCOVERED: Vertices(%d)\n" % len(verts))
    # triangle list
    tris = m.loop_triangles
    print("BCF_DISCOVERED: Triangles(%d)\n" % len(tris))
    # uv0 data
    uv0_data = m.uv_layers[0].data
    print("BCF_DISCOVERED: UV0Coords(%d)\n" % len(uv0_data))

    # uv1 data (if available)
    uv1_data = None
    if len(m.uv_layers) > 1:
        uv1_data = m.uv_layers[1].data
        print("BCF_DISCOVERED: UV1Coords(%d)\n" % len(uv1_data))
    else:
        print("BCF_DISCOVERED: No UV1Coords available\n")
    
    # empty list, fill later
    unique_verts = []
    
    # real triangle data (optimized)
    real_tris = []
    
    # for each triangle
    print("BCF_START_PROCESSING_TRIANGLES...\n")
    for t in tris:
        triangle = [] # only list of verts
        
        # let's loop over indices in this triangle
        # REVISED (reverse order, cause blender's front is CW)
        for i in range(2, -1, -1):
            # get loop id
            loop_id = t.loops[i]
            # get loop data
            vtx = mls[loop_id]
            
            # grab vertex data
            pos = verts[vtx.vertex_index].co
            normal = vtx.normal
            uv = uv0_data[loop_id].uv

            # Transform by -90 along x axis
            # to conform to opengl standard
            # [x y z] => [x -z y]
            
            # build vertex data as flat array
            vdata = [
                [pos.x, -pos.z, pos.y],
                [normal.x, -normal.z, normal.y],
                [uv.x, uv.y]
            ]
            
            # add if no vertex found
            if vdata not in unique_verts:
                unique_verts.append(vdata)
                
            # grab its index
            # get unique id of such vertex
            unique_v_idx = unique_verts.index(vdata)
            # add to triangle data
            triangle.append(unique_v_idx)
        
        # append real tris data
        real_tris.append(triangle)

    print("BCF_BUFFERS_BUILT\n")
    return (unique_verts, real_tris)


# do the writing (easy)
def write_some_data(context, filepath, vtx_format, me):
    print("BCF_EXPORT_STARTED...\n")

    # check some requirements...
    if (len(context.selected_objects) == 0):
        print("NO OBJECT SELECTED. BAIL....")
        me.report({'ERROR'}, 'NO OBJECT SELECTED!')
        return {'CANCELLED'}
    
    # grab object
    obj = context.selected_objects[0]

    # process the object
    print("BCF_VERTEX_FORMAT: %d\n" % vtx_format)
    vb, ib = buildBuffers(obj, report=me.report)

    # now write the data
    print("BCF_WRITING_TO_FILE: (%s)...\n" % filepath)
    f = open(filepath, 'w', encoding='utf-8')
    f.write("vtx_format %d\n" % vtx_format)
    f.write("object: %s\n" % obj.name)

    # write vertex count and data
    print("BCF_WRITING_VERTEX_DATA...\n")
    f.write("vertex_count: %d\n" % len(vb))
    for v_idx, v in enumerate(vb):
        f.write("%d: %.4f %.4f %.4f \t%.4f %.4f %.4f\t%.4f %.4f\n" % (
            v_idx,
            v[0][0], v[0][1], v[0][2],
            v[1][0], v[1][1], v[1][2],
            v[2][0], v[2][1]
        ))
    print("DONE.\n")

    # write index data
    print("BCF_WRITING_TRIANGLE_DATA...\n")
    f.write("triangle_count: %d\n" % len(ib))
    for t_idx, t in enumerate(ib):
        f.write("%d: %d %d %d\n" % (
            t_idx, t[0], t[1], t[2]
        ))

    f.close()
    print("DONE.\n")

    me.report({'INFO'}, "Done writing shits: %d unique vertices and %d triangles " % (len(vb), len(ib)))

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty
from bpy.types import Operator


class BCFExporter(Operator, ExportHelper):
    """Export to Bowie's Custom Format (BCF) ascii"""
    bl_idname = "bcf_exporter.export"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "EXPORT BCF!"

    # ExportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob: StringProperty(
        default="*.txt",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # some default vertex format
    vertex_has_pos: BoolProperty(name="Position", description="XYZ vertex data", default=(VTF_DEFAULT & VTF_POS)!=0)
    vertex_has_normal: BoolProperty(name="Normal", description="XYZ normal data", default=(VTF_DEFAULT & VTF_NORMAL)!=0)
    vertex_has_uv0: BoolProperty(name="UV0", description="primary (first) UV", default=(VTF_DEFAULT & VTF_UV0)!=0)
    vertex_has_tangents: BoolProperty(name="Tangent+Bitangent", description="tangent+bitangent 2x(XYZ)", default=(VTF_DEFAULT & VTF_TANGENT_BITANGENT)!=0)
    vertex_has_uv1: BoolProperty(name="UV1", description="secondary UV", default=(VTF_DEFAULT & VTF_UV1)!=0)
    vertex_has_color: BoolProperty(name="Color", description="(RGB) vertex color", default=(VTF_DEFAULT & VTF_COLOR)!=0)
    vertex_has_bone: BoolProperty(name="Bone Weights+IDs", description="Bone Weights + ID for skeletal animation", default=(VTF_DEFAULT & VTF_BONE_DATA)!=0)
    vertex_has_tween: BoolProperty(name="Tween", description="XYZ vertex animation data", default=(VTF_DEFAULT & VTF_TWEEN)!=0)

    # # List of operator properties, the attributes will be assigned
    # # to the class instance from the operator settings before calling.
    # use_setting: BoolProperty(
    #     name="Example Boolean",
    #     description="Example Tooltip",
    #     default=True,
    # )
    # type: EnumProperty(
    #     name="Animation Data",
    #     description="Store animation (bone weights+id) data?",
    #     items=(
    #         ('OPT_NO_ANIM', "Without Animation data", "No Vertex weights info"),
    #         ('OPT_WITH_ANIM', "With Animation data", "With vertex weights"),
    #     ),
    #     default='OPT_NO_ANIM',
    # )

    def execute(self, context):
        # build a vertex format before executing
        format = 0
        if self.vertex_has_pos: format |= VTF_POS
        if self.vertex_has_normal: format |= VTF_NORMAL
        if self.vertex_has_uv0: format |= VTF_UV0
        if self.vertex_has_tangents: format |= VTF_TANGENT_BITANGENT
        if self.vertex_has_uv1: format |= VTF_UV1
        if self.vertex_has_color: format |= VTF_COLOR
        if self.vertex_has_bone: format |= VTF_BONE_DATA
        if self.vertex_has_tween: format |= VTF_TWEEN


        return write_some_data(context, self.filepath, format, self)


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
    bpy.ops.bcf_exporter.export('INVOKE_DEFAULT')
