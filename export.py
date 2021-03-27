import bpy

###
# buildBuffers: return tuple of vb and ib
def buildBuffers(obj, report=None):
    
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
    
    # compute data
    m.calc_loop_triangles()
    m.calc_normals_split()
    m.calc_tangents()
    
    # now we access the data
    # the mesh loops (for v_idx, normal, tangent, bitangent)
    mls = m.loops
    # vertex list
    verts = m.vertices
    # triangle list
    tris = m.loop_triangles
    # uv0 data
    uv0_data = m.uv_layers[0].data
    
    # empty list, fill later
    unique_verts = []
    
    # real triangle data (optimized)
    real_tris = []
    
    # for each triangle
    for t in tris:
        triangle = [] # only list of verts
        
        # let's loop over indices in this triangle
        for i in range(0, 3):
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

    return (unique_verts, real_tris)



def write_some_data(context, filepath, use_some_setting, me):
    print("running write_some_data...")

    # check some requirements...
    if (len(context.selected_objects) == 0):
        print("NO OBJECT SELECTED. BAIL....")
        me.report({'ERROR'}, 'NO OBJECT SELECTED!')
        return {'CANCELLED'}
    
    # grab object
    obj = context.selected_objects[0]

    # process the object
    vb, ib = buildBuffers(obj, report=me.report)

    f = open(filepath, 'w', encoding='utf-8')
    f.write("#Hello World %s\n" % use_some_setting)
    f.write("object: %s\n" % obj.name)

    # write vertex count and data
    f.write("vertex_count: %d\n" % len(vb))
    for v_idx, v in enumerate(vb):
        f.write("%d: %.4f %.4f %.4f \t%.4f %.4f %.4f\t%.4f %.4f\n" % (
            v_idx,
            v[0][0], v[0][1], v[0][2],
            v[1][0], v[1][1], v[1][2],
            v[2][0], v[2][1]
        ))

    # write index data
    f.write("triangle_count: %d\n" % len(ib))
    for t_idx, t in enumerate(ib):
        f.write("%d: %d %d %d\n" % (
            t_idx, t[0], t[1], t[2]
        ))

    f.close()

    me.report({'INFO'}, "Done writing shits: %d unique vertices and %d triangles " % (len(vb), len(ib)))

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "EXPORT BCF!"

    # ExportHelper mixin class uses this
    filename_ext = ".txt"

    filter_glob: StringProperty(
        default="*.txt",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        return write_some_data(context, self.filepath, self.use_setting, self)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSomeData.bl_idname, text="Text Export Operator")


def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')
