import bpy
import array
import sys

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

# helper to make binary buffer
def make_buffer(format, data):
    buf = array.array(format, data)
    if sys.byteorder != 'little':
        buf.byteswap()
    return buf

# compute bytes per vertex
def bytesPerVertex(vtx_format):
    totalSize = 0
    if vtx_format & VTF_POS: totalSize += 12
    if vtx_format & VTF_NORMAL: totalSize += 12
    if vtx_format & VTF_UV0: totalSize += 8
    if vtx_format & VTF_TANGENT_BITANGENT: totalSize += 24
    if vtx_format & VTF_UV1: totalSize += 8
    if vtx_format & VTF_COLOR: totalSize += 12
    if vtx_format & VTF_BONE_DATA: totalSize += 20

    return totalSize
##

###
# buildBuffers: return tuple of vb and ib
def buildBuffers(obj, report=None, format=VTF_DEFAULT):
    
    # mesh
    m = obj.data
    
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

    # submeshes = materials
    submeshes_count = len(m.materials)
    print("BCF_SUBMESHES_COUNT: %d" % submeshes_count)

    
    # empty list, fill later
    unique_verts = []
    
    # real triangle data (optimized)
    # real_tris = []
    # allocate submeshes data
    submeshes_data = []
    for i in range(submeshes_count):
        submeshes_data.append({
            "material": m.materials[i].name,
            "data": []
        })
    
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

            # Transform by -90 along x axis
            # to conform to opengl standard
            # [x y z] => [x -z y]
            
            # build vertex data as flat array
            '''
            [pos.x, -pos.z, pos.y],
            [normal.x, -normal.z, normal.y],
            [uv.x, uv.y]
            '''
            vdata = []

            # grab vertex data (only when needed)
            # ALL VERTEX DATA NEED TO BE ROTATED 90deg
            # ALONG X AXIS. JUST SWAP Y <-> Z
            # position
            if format & VTF_POS:
                pos = verts[vtx.vertex_index].co
                vdata.append([pos.x, pos.z, -pos.y])

            # normal
            if format & VTF_NORMAL:
                normal = vtx.normal
                vdata.append([normal.x, normal.z, -normal.y])

            # uv0
            if format & VTF_UV0:
                uv = uv0_data[loop_id].uv
                vdata.append([uv.x, uv.y])

            # tangent + bitangent
            if format & VTF_TANGENT_BITANGENT:
                tangent = vtx.tangent
                bitangent = vtx.bitangent
                vdata.append([
                    tangent.x, tangent.z, -tangent.y,
                    bitangent.x, bitangent.z, -bitangent.y
                ])

            # uv1
            if format & VTF_UV1 and uv1_data != None:
                uv = uv1_data[loop_id].uv
                vdata.append([uv.x, uv.y])
            
            # add if no vertex found, add as new
            # otherwise, this vertex is not unique
            if vdata not in unique_verts:
                unique_verts.append(vdata)
                
            # grab its index
            # get unique id of such vertex
            unique_v_idx = unique_verts.index(vdata)
            # add to triangle data
            triangle.append(unique_v_idx)
        
        # append real tris data
        # real_tris.append(triangle)
        # append to appropriate submeshes?
        submeshes_data[t.material_index]['data'].append(triangle)

    print("BCF_BUFFERS_BUILT\n")
    return (unique_verts, submeshes_data)

# preparation step
def can_write(context, vtx_format, me):
    print("CHECKING IF CONTEXT MAKES SENSE...\n")
    
    # check some requirements...
    # make sure an object is selected
    if (len(context.selected_objects) == 0):
        print("NO OBJECT SELECTED. BAIL....")
        me.report({'ERROR'}, 'NO OBJECT SELECTED!')
        return False
    
    # make sure it's a mesh object
    obj = context.selected_objects[0]
    m = obj.data

    if type(m) != bpy.types.Mesh:
        print("OBJECT DATA IS NOT MESH!")
        me.report({'ERROR'}, "SELECTED OBJECT '%s' IS NOT A MESH" % obj.name)
        return False

    # make sure it has at least 1 uv map
    if (len(m.uv_layers) < 1):
        print("NO UV MAP FOUND!")
        me.report({'ERROR'}, "AT LEAST 1 UV MAP MUST BE CREATED!")
        return False

    # if uv1 is specified, make sure it has 2 uv maps
    if (vtx_format & VTF_UV1) and len(m.uv_layers) < 2:
        print("CANNOT FIND SECOND UV MAP!! MAYBE EXPORT WITH UV0 only!")
        me.report({'ERROR'}, "UV1 WAS REQUESTED BUT THERE WAS ONLY 1 UV MAP!")
        return False

    return True

# do the writing (easy)
def do_write(context, filepath, vtx_format, me, mode="ascii"):
    print("BCF_EXPORT_STARTED...\n")

    # check some requirements...
    if not can_write(context, vtx_format, me):
        return {'CANCELLED'}
    
    # grab object
    obj = context.selected_objects[0]

    # process the object
    print("BCF_VERTEX_FORMAT: %d\n" % vtx_format)
    vb, ibs = buildBuffers(obj, report=me.report,format=vtx_format)

    if mode == 'ascii':
        # write to ascii for now (changeable later)
        total_tris = write_to_ascii(filepath, vb, ibs, vtx_format, obj.name)
    elif mode == 'binary':
        total_tris = write_to_binary(filepath, vb, ibs, vtx_format, obj.name)
    else:
        # error happens
        me.report({'INFO'}, "UNKNOWN WRITE TYPE '%s'" % mode)
        return {'CANCELLED'}

    me.report({'INFO'}, "Done writing shits: %d unique vertices and %d submeshes, totaling %d tris " % (len(vb), len(ibs), total_tris))

    return {'FINISHED'}

# write_to_binary, write binary file
# FORMAT IS AS FOLLOWS:
# 1b : vtx_format
# 1b : bytes_per_vertex
# 2b : vertex_count (max 65535 vertex)
# 4b : vertex_buffer_size_in_bytes
# 2b : sub_mesh_count
# 32b: objname
# 2b : total_tris
# --SUB_MESH_DATA_---
# { 32b: material_name, 2b: begin_at, 2b: total_tri }
# { vertex_buffer }
# { index_buffer }
def write_to_binary(filepath, vb, ibs, vtx_format, objname):
    # preprocess indices data first
    total_tris = 0
    for ib in ibs:
        ib['begin_at'] = total_tris
        ib['total_elem'] = len(ib['data'])
        total_tris += ib['total_elem']

    print("BCF_BINARY_WRITE: (%s)...\n" % filepath)
    vertex_size = bytesPerVertex(vtx_format)

    print("format: %d, bytes per vertex: %d\n" % (vtx_format, vertex_size) )
    f = open(filepath, 'wb')

    # write vtx format and bytes per vertex
    # 1b : vtx_format
    # 1b : bytes_per_vertex
    print("BCF_WRITE_HEADER...\n")
    buf = make_buffer('B',[ vtx_format, vertex_size ])
    f.write(buf)
    
    # 2b : vertex_count (max 65535 vertex)
    # 4b : vertex_buffer_size_in_bytes
    vertex_count = len(vb)
    '''
    'b'         signed integer     1
    'B'         unsigned integer   1
    'u'         Unicode character  2 (see note)
    'h'         signed integer     2
    'H'         unsigned integer   2
    'i'         signed integer     2
    'I'         unsigned integer   2
    'l'         signed integer     4
    'L'         unsigned integer   4
    'q'         signed integer     8 (see note)
    'Q'         unsigned integer   8 (see note)
    'f'         floating point     4
    'd'         floating point     8
    '''
    f.write(make_buffer('H', [vertex_count]))
    vertex_buffer_size_in_bytes = vertex_count * vertex_size
    print("vertex_count: %d, vertex_buffer_size_in_bytes: %d\n" % ( vertex_count, vertex_buffer_size_in_bytes ))
    f.write(make_buffer('L', [vertex_buffer_size_in_bytes]))

    # 2b : sub_mesh_count
    submesh_count = len(ibs)
    print("submesh_count: %d\n" % submesh_count)
    f.write(make_buffer('H', [submesh_count]))

    # 32b: objname
    print("objname: %s\n" % objname)
    buf = bytearray(objname, 'utf-8')
    padded_buf = buf.ljust(32, b'\0')
    f.write(padded_buf)

    # 2b: total_tris
    print("total_tris: %d\n" % total_tris)
    buf = make_buffer('H', [total_tris])
    f.write(buf)

    # SUBMESH_DATA
    for ib in ibs:
        print("writing mesh(%s, begin: %d, total: %d)\n" % (ib['material'], ib['begin_at'], ib['total_elem']))

        # 32b: material_name
        buf = bytearray(ib['material'], 'utf-8')
        padded_buf = buf.ljust(32, b'\0')
        f.write(padded_buf)

        # 2b: begin_at
        buf = make_buffer('H', [ib['begin_at']])
        f.write(buf)
        
        # 2b: total_elem
        buf = make_buffer('H', [ib['total_elem']])
        f.write(buf)

    # VERTEX_BUFFER
    print("writing vertex buffer...\n")
    for v_idx, v in enumerate(vb):
        i = 0   # track data pointer
        # write position if there is
        if vtx_format & VTF_POS:
            buf = make_buffer('f', v[i])
            f.write(buf)
            i+=1

        # write normal
        if vtx_format & VTF_NORMAL:
            buf = make_buffer('f', v[i])
            f.write(buf)
            i+=1

        # write uv0
        if vtx_format & VTF_UV0:
            buf = make_buffer('f', v[i])
            f.write(buf)
            i+=1

        # write tangent + bitangent
        if vtx_format & VTF_TANGENT_BITANGENT:
            buf = make_buffer('f', v[i])
            f.write(buf)
            i+=1

        # write uv1
        if vtx_format & VTF_UV1:
            buf = make_buffer('f', v[i])
            f.write(buf)
            i+=1

    
    # WRITE ALL INDICES
    # for each submesh
    for ib in ibs:
        for t in ib['data']:
            f.write(make_buffer('H', t))

    f.close()

    return total_tris

def write_to_ascii(filepath, vb, ibs, vtx_format, objname):

    # now write the data
    print("BCF_WRITING_TO_FILE: (%s)...\n" % filepath)
    f = open(filepath, 'w', encoding='utf-8')
    f.write("vtx_format: %d\n" % vtx_format)
    f.write("object: %s\n" % objname)

    # write vertex count and data
    print("BCF_WRITING_VERTEX_DATA...\n")
    f.write("vertex_count: %d\n" % len(vb))
    for v_idx, v in enumerate(vb):
        # print id
        f.write("%d:" % v_idx)
        # conditional write here....
        i = 0   # track the data pointer
        if vtx_format & VTF_POS: 
            f.write("\tv(%.4f %.4f %.4f)" % (v[i][0], v[i][1], v[i][2]))
            i+=1

        if vtx_format & VTF_NORMAL: 
            f.write("\tn(%.4f %.4f %.4f)" % (v[i][0], v[i][1], v[i][2]))
            i+=1

        if vtx_format & VTF_UV0: 
            f.write("\tu0(%.4f %.4f)" % (v[i][0], v[i][1]))
            i+=1

        if vtx_format & VTF_TANGENT_BITANGENT: 
            f.write("\ttb(%.4f %.4f %.4f %.4f %.4f %.4f)" % (v[i][0], v[i][1], v[i][2], v[i][3], v[i][4], v[i][5]))
            i+=1

        if vtx_format & VTF_UV1: 
            f.write("\tu1(%.4f %.4f)" % (v[i][0], v[i][1]))
            i+=1

        f.write("\n")
    print("DONE.\n")

    # write index data
    print("BCF_WRITING_TRIANGLE_DATA...\n")
    f.write("submeshes_count: %d\n" % len(ibs))
    # for each submeshes
    total_tris = 0
    for ib in ibs:
        f.write("material: %s\n" % ib['material'])
        f.write("triangle_count: %d\n" % len(ib['data']))
        total_tris += len(ib['data'])
        for t_idx, t in enumerate(ib['data']):
            f.write("%d: %d %d %d\n" % (t_idx, t[0], t[1], t[2]))
    
    f.flush()
    f.close()
    print("DONE.\n")

    # return length of vb, num of submeshes, and total tris
    return total_tris

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
    filename_ext = ".bcf"

    filter_glob: StringProperty(
        default="*.bcf",
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

    write_mode: EnumProperty(
        items=(
            ('ascii', "ASCII", "Human readable format"),
            ('binary', "Binary", "Compact memory size")
        ),
        name="File Type",
        description="What kind of file output to write",
        default='ascii'
    )

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


        return do_write(context, self.filepath, format, self, self.write_mode)


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
