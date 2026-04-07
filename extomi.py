
bl_info = {
    "name": "Export to Miproject",
    "author": "Roni Raihan - TRPHB Animation",
    "version": (0, 1),
    "blender": (5, 0, 1),
    "location": "File -> Export -> Miproject",
    "description": "Export Mesh to Miproject",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, see < https://www.gnu.org/licenses/ >.
#
# ##### END GPL LICENSE BLOCK #####

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#inspirasi : forum mineimator      https://www.mineimatorforums.com/index.php?/topic/93715-mine-imator-20-3d-model-converter-mostly/
#            source code (written in C)  https://file.garden/ZlrJr4gXzRtJW4yO/magic/converter.c
#            code written in C code by Mr. Doon


import bpy
import os
import json
import struct
import math
import sys
import re
import string
import random
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


# < = litel endian
# f = float32
# I = uint32

VER_STR = struct.Struct("<fffIIffII")

#--------------------------------------------------------
def acak_nama(jum=15):
    pil = string.ascii_uppercase + string.digits + string.ascii_lowercase
    return ''.join(random.choices(pil, k=jum))

def aman_nama(nama):
    nama = str(re.sub(r'[<>;.,:"/\\|?*\s]', '_', nama))
    return nama

def cek_id(nama, sobj):
    id = "basis"
    for b in sobj:
        if nama == b["name"]:
            id = str(b["id"])
            break
    return id

def cek_parent(nama, sobj):
    for b in sobj:
        if nama == b["name"]:
            return str(b["parent"])
    return ""
    
def cek_loc(nama, sobj):
    for b in sobj:
        if nama == b["name"]:
            return b["loc"]["x"], b["loc"]["y"], b["loc"]["z"]
    return 0, 0, 0
    
def pos_persiap(): #bikin semua perubahan persiapan export diulang ke awal
    if bpy.app.timers.is_registered(kembalikan):
        bpy.app.timers.unregister(kembalikan)
    bpy.app.timers.register(kembalikan, first_interval=0.2)
    
def atur_enable_collection(atur):
    def proses_collection(coll):
        coll.exclude = atur
        for child in coll.children:
            proses_collection(child)
    
    root_layer = bpy.context.view_layer.layer_collection
    for child in root_layer.children:
        proses_collection(child)
    
def atur_enabel_view():
    def proses_collection(coll):
        coll.hide_viewport = False #view
        
        name = coll.name
        coll_data = bpy.data.collections[name]
        coll_data.hide_viewport = False #Viewport (ikon monitor)
        for child in coll.children:
            proses_collection(child)
            
    root_layer = bpy.context.view_layer.layer_collection
    for child in root_layer.children:
        proses_collection(child)
        
    for obj in bpy.context.view_layer.objects:
        if obj.type == 'MESH':
            obj.hide_viewport = False
            
def atur_disable_view():
    hidcoll = []
    def proses_collection(coll, status = False):
        st = status
        name = coll.name
        coll_data = bpy.data.collections[name]
        if coll.hide_viewport == True or status or coll_data.hide_viewport == True:
            coll.hide_viewport = True #view
            coll_data.hide_viewport = True #Viewport (ikon monitor)
            st = True
            hidcoll.append(name)
            
        for child in coll.children:
            proses_collection(child, st)
            
    root_layer = bpy.context.view_layer.layer_collection
    for child in root_layer.children:
        proses_collection(child)
        
    for o in bpy.context.view_layer.objects:
        obj = bpy.data.objects.get(o.name)
        hid = any(oc.name in hidcoll for oc in obj.users_collection)
        if hid:
            obj.hide_viewport = True

def atur_select_collection():
    def proses_collection(coll):
        name = coll.name
        coll_data = bpy.data.collections[name]
        coll_data.hide_select = False
        for child in coll.children:
            proses_collection(child)
            
    root_layer = bpy.context.view_layer.layer_collection
    for child in root_layer.children:
        proses_collection(child)
        
def atur_object_persiapan(context, sobj):
    #hapus parent
    bpy.ops.object.select_all(action='DESELECT')
    for o in sobj:
        obj = bpy.data.objects.get(o["name"])
        obj.select_set(True)
        context.view_layer.objects.active = obj
        break
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    
    #applay rotasi dan ukuran   
    bpy.ops.object.select_all(action='DESELECT')
    for o in sobj:
        obj = bpy.data.objects.get(o["name"])
        if obj.type in ('MESH', 'EMPTY', 'CURVE', 'SURFACE', 'META', 'CURVES', 'GREASEPENCIL',
                        'LATTICE', 'ARMATURE'):
            obj.select_set(True)
            context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

def cari_tex_filter(filter_mat): #{"mat", "tex_id_file", "tex_name"}
    fmat = []
    img_list = []
    for mt in filter_mat:
        mat = bpy.data.materials.get(mt)
        img_name = None
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    if node.image:
                        img_name = node.image.name
                        break
        if img_name:
            ada = False
            for iml in img_list: #cek apakah sudah ada di list
                if iml["tex_name"] == img_name:
                    tulis = {"mat": mt, "tex_id_file": iml["tex_id_file"], "tex_name": img_name}
                    fmat.append(tulis)
                    ada = True
                    break
            if ada:
                continue
            
            #bikin baru kalo belum
            tex_id_file = aman_nama(img_name) + acak_nama(jum=10)
            img = bpy.data.images.get(img_name)
            if img.source == 'FILE':
                if img.packed_file:
                    tulis = {"mat": mt, "tex_id_file": tex_id_file, "tex_name": img_name}
                    catat = {"tex_id_file": tex_id_file, "tex_name": img_name}
                    fmat.append(tulis)
                    img_list.append(catat)
                else:
                    if img.filepath:
                        fpath = bpy.path.abspath(img.filepath)
                        if os.path.exists(fpath):
                            tulis = {"mat": mt, "tex_id_file": tex_id_file, "tex_name": img_name}
                            catat = {"tex_id_file": tex_id_file, "tex_name": img_name}
                            fmat.append(tulis)
                            img_list.append(catat)
            elif img.source == 'GENERATED':
                tulis = {"mat": mt, "tex_id_file": tex_id_file, "tex_name": img_name}
                catat = {"tex_id_file": tex_id_file, "tex_name": img_name}
                fmat.append(tulis)
                img_list.append(catat)
                continue
                    
    return fmat

def cari_tex_id(mats, obj_name):
    obj = bpy.data.objects.get(obj_name)
    if not obj or not obj.material_slots:
        return ""
    
    for slot in obj.material_slots:
        if slot.material:
            mth_obj = slot.material.name
            for mat in mats:
                if mth_obj == mat["mat"]:
                    print(obj_name + " texture: " + mat["tex_id_file"])
                    return mat["tex_id_file"]
    return ""

def tentukan_parent(obj_name, sobj):
    obj = bpy.data.objects.get(obj_name)
    
    if obj.parent:
        parent = obj.parent
        for o in sobj: # bila parent ada di sobj
            if parent.name == o["name"]:
                return o["id"]
            
        # lanjut bila parent gak ada di sobj
        return tentukan_parent(parent.name, sobj)
    else:
        return ""

def loc_relatif(name, id_parent, sobj):
    obj = bpy.data.objects.get(name)
    for b in sobj:
        if id_parent == b["id"]:
            obj_parent = bpy.data.objects.get(b["name"])
            break
        
    matrix_relatif = obj_parent.matrix_world.inverted() @ obj.matrix_world
    return matrix_relatif.translation

def loc_mip_space(vextor):
    # Blender  mi  json  * 16.0
    #    x     z    y
    #    y     x    x
    #    z     y    z
    v_x, v_y, v_z = vextor
    
    x = v_y * 16.0
    y = v_x * 16.0
    z = v_z * 16.0
    
    return x, y, z
        
def export_data(context, vobj, sobj, mats, base_fpath, aturan): #, use_setting):
    #bersihin jalur
    fpath = bpy.path.abspath(base_fpath)
    
    # persiapan bikin folder awal
    fold = os.path.splitext(bpy.path.basename(fpath))[0]
    fold = aman_nama(fold)
    if fold.replace('_', '') == '':
        fold = "export_miproject"
            
    exp_dir = os.path.dirname(fpath)
    exp_fold = os.path.join(exp_dir, fold)
    if not os.path.exists(exp_fold):
        os.makedirs(exp_fold)
        
    #-------------------------
    #vobj = {"name" : obj.name, "tex": "", "meshcache": ""}
    #sobj = {"name", "id", "parent", "loc"}
    #mats = {"mat", "tex_id_file", "tex_name"}
    
    #mendaftar lokasi dan parent
    for o in sobj:
        if o["parent"]:
            ox, oy, oz = loc_mip_space(loc_relatif(o["name"], o["parent"], sobj))
        else:
            obj = bpy.data.objects.get(o["name"])
            ox, oy, oz = loc_mip_space(obj.matrix_world.translation)
            
        o["loc"] = {
            "x" : ox,
            "y" : oy,
            "z" : oz
        }
    
    #mengextrak ply dan meshcache
    for o in vobj:
        #export meshcache
        nid = aman_nama(o["name"]) + cek_id(o["name"], sobj) #nama file meshcache
        vco, ico, ver, indc = mesh_to_meshcache(o["name"], aturan["apply_mod"]) #hitung mesh
        mece = os.path.join(exp_fold, f"{nid}.schematic.meshcache")
        tulis_mece(mece, vco, ico, ver, indc) #tulis meshcache
        
        o["meshcache"] = f"{nid}.schematic"
        o["tex"] = cari_tex_id(mats, o["name"])
    
    #mengextrak texture
    base_tex = base_tex_buat(exp_fold) #buat base texture
    tex = export_tex(exp_fold, mats) #jadi daftar nama + extensi
        
    #menulis file miproject
    mip = os.path.join(exp_fold, f"{fold}.miproject")
    mext_mip(mip, fold, vobj, sobj, tex, base_tex, aturan)
    
#bikin miproject
def mext_mip(file, name, vobj, sobj, mat_tex, base_tex, aturan):
    print("create .miproject")
    # Blender  mi  json  * 16.0
    #    x     z    y
    #    y     x    x
    #    z     y    z
            
    data = {
        "format": 34,
        "created_in": "Exporter to Miproject",
        "project": {
            "name": name,
            "author": aturan["author"],
            "description": aturan["desk"],
            "video_width": 1280,
            "video_height": 720,
            "render_settings": "performance",
            "tempo": 24
            },
        "templates": [],
        "timelines": [],
        "resources": []
    }
    
    #tambah_texture
    def add_tex(name_tex):
        resource = {
            "id": os.path.splitext(name_tex)[0],
            "type": "blocksheet",
            "filename": str(name_tex),
            "material_format": 2
        
        }
        data["resources"].append(resource)
        
    #tambah texture resource 
    add_tex(base_tex) #base_texture
    for mt in mat_tex: # texture
        add_tex(mt)
    
    #tambahin mesh
    catat_mesh = []
    for o in vobj: #o = {"name", "tex", "meshcache"}
        
        ox, oy, oz = cek_loc(o["name"], sobj)
        
        #cek parent
        parent = cek_parent(o["name"], sobj)
        if not parent:
            parent = "root"
        
        #cek texture
        tex = os.path.splitext(base_tex)[0]
        if o["tex"]:
            tex = o["tex"]
            
        resource = {
            "id": cek_id(o["name"], sobj) + "res",
            "type": "scenery",
            "filename": o["meshcache"],
            "scenery_tl_add": True,
            "material_format": 2
        }
        
        templates = {
            "id": cek_id(o["name"], sobj) + "temp",
            "type": "scenery",
            "name": o["name"],
            "scenery": cek_id(o["name"], sobj) + "res",
            "block":{
                "tex": tex,
                "tex_material": "default",
                "tex_normal": "default",
                "repeat_enable": False,
                "repeat": [ 1, 1, 1 ]
            }
        }
        
        timelines = {
            "id": cek_id(o["name"], sobj),
            "type": "scenery",
            "name": "",
            "temp": cek_id(o["name"], sobj) + "temp",
            "default_values": {
                "POS_X": ox,
                "POS_Y": oy,
                "POS_Z": oz
            },
            "keyframes": {
                "0": {
                    "POS_X": ox,
                    "POS_Y": oy,
                    "POS_Z": oz
                }
            },
            "parent": parent,
            "backfaces": aturan["backfaces"]
        }
        
        data["resources"].append(resource)
        data["templates"].append(templates)
        data["timelines"].append(timelines)
        catat_mesh.append(o["name"])
        
    #tambah folder
    for o in sobj: #{"name", "id", "parent", "loc"}
        if o["name"] in catat_mesh:
            continue
        
        parent = o["parent"]
        if not parent:
            parent = "root"
            
        timelines = {
            "id": o["id"],
            "type": "folder",
            "name": o["name"],
            "temp": "null",
            "default_values": {
                "POS_X": o["loc"]["x"],
                "POS_Y": o["loc"]["y"],
                "POS_Z": o["loc"]["z"]
            },
            "keyframes": {
                "0": {
                    "POS_X": o["loc"]["x"],
                    "POS_Y": o["loc"]["y"],
                    "POS_Z": o["loc"]["z"]
                }
            },
            "parent": parent
        }
        
        data["timelines"].append(timelines)
    
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
def base_tex_buat(exp_fold):
    nid = acak_nama(jum=15)
    name = f"base_texture_miproject_{nid}"
    
    #bikin texture
    bpy.ops.image.new(
        name = name,
        width = 2048,
        height = 2048,
        color = (1.0, 1.0, 1.0, 1.0),
        alpha = True,
        generated_type='BLANK',
        float = False,
        use_stereo_3d=False,
        tiled=False
    )
    
    #atur image
    img = bpy.data.images.get(name)
    img.file_format = 'PNG'
    
    #simpan
    fname = f"{name}.png"
    fpath = os.path.join(exp_fold, fname)
    img.save(filepath=fpath, save_copy=True)
    
    return fname
        
def export_tex(exp_fold, mats): #mats = {"mat", "tex_id_file", "tex_name"}
    texture = []
    ada = []
    for mat in mats:
        if mat["tex_name"] in ada:
            continue
        
        #simpan
        img = bpy.data.images.get(mat["tex_name"])
        name = mat["tex_id_file"]
        fname = f"{name}.png"
        fpath = os.path.join(exp_fold, fname)
        img.save(filepath=fpath, save_copy=True)
        
        texture.append(fname)
        ada.append(mat["tex_name"])
    
    return texture
        
def mesh_to_meshcache(obj_name, apply_mod = False):
    obj = bpy.data.objects.get(obj_name)
    if apply_mod:
        depg = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depg)
    else:
        obj_eval = obj
    mesh = obj_eval.to_mesh()
    mesh.calc_loop_triangles()
    
    ver = []
    indic = []
    uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
    
    print(obj_name + " Calculate mesh")
    #---------------------sctukture
    # mesh
    # |- Vertex
    # |    |- v.co (kordinat)
    # |    |- v.normal
    # |        
    # |- loops (Penghubung vertex - face)
    # |    |- loop.vertex_index (index ke vertex)
    # |        
    # |- loop_triangles
    # |   |- til.loops (daftar index untuk 3 vertex triangles)
    # |        
    # |- uv_layer
    #     |-uv_layer.data 
    #          |- uv (index berdasarkan til.loops)
    #              |- uv.x
    #              |- uv.y
    #
    #--------------------data hasil
    # vco : jumlah vertex
    #
    # ico : jumlah index
    #
    # ver : (
    #   x, y, z,
    #   normal,
    #   0xFFFFFFFF,
    #   uv_u, uv_v,
    #   0,
    #   0
    # )
    #
    # indic : [0, 1, 2
    #        3, 4, 5
    #        .......] setiap 3 index = 1 triangle
    
    for til in mesh.loop_triangles:
        loops_til = til.loops
        
        # Baiki index triangle (biar gak kebalik)
        order = [0, 2 ,1]
        
        for i in order:
            li = loops_til[i]
            loop = mesh.loops[li]
            v = mesh.vertices[loop.vertex_index]
                
            # Blender  mi  * 16.0
            #    x     z   
            #    y     x  
            #    z     y  
                
            #kordinat vertex
            x, y, z = v.co
            x = (-x * 16.0) + 8.0 #z
            y = (y * 16.0) + 8.0 #x
            z = z * 16.0 #y
            
            #normal
            nx, ny, nz = v.normal
            nx = (nx + 1.0) *0.5
            ny = (ny + 1.0) *0.5
            nz = (nz + 1.0) *0.5
            
            nbx = int(round(nx * 255)) & 0xFF
            nby = int(round(ny * 255)) & 0xFF
            nbz = int(round(nz * 255)) & 0xFF
            
            normal = nbx | (nby << 8) | (nbz << 16)
            
            #uv
            if uv_layer:
                uv = uv_layer[li].uv
                uv_u = uv.x
                uv_v = -uv.y
            else:
                uv_u, uv_v = 0.0, 0.0
                
            ver.append(VER_STR.pack(
                x, y, z,
                normal,
                0xFFFFFFFF,
                uv_u, uv_v,
                0,
                0
            ))
            
    #index (urut karesa sesuai perloop)
    indic = list(range(len(ver))) #[0, 1, 2, ....] setiap 3 index = 1 triangle
    
    vco = len(ver)
    ico = len(indic)
    
    obj_eval.to_mesh_clear()
    print(f"{vco} vertex")
    print(f"{int(ico/3)} triangles face")
    
    return vco, ico, ver, indic

# tulis mesh
def tulis_mece(path, vco, ico, ver, indc):
    with open(path, "wb") as f:
        #Header
        f.write(struct.pack("<Q", 2)) # format index
        f.write(struct.pack("<Q", 1)) # dim x
        f.write(struct.pack("<Q", 1)) # dim y
        f.write(struct.pack("<Q", 1)) # dim z
        f.write(struct.pack("<B", 1)) # mesh count
        
        #Header Mesh (big edian)
        f.write(struct.pack(">Q", vco))
        f.write(struct.pack(">Q", ico))
        
        #data vertex
        for v in ver:
            f.write(v)
            
        #data index
        for i in indc:
            f.write(struct.pack("<I", i))
        
        print("menyimpan meshcache")
        print(path)
    
#--------------------------------------------------------
class ExportMiproj(Operator, ExportHelper):
    """Export Mesh to Miproject"""
    bl_idname = "export_miproj.meshcache" 
    bl_label = "Mine-Imator (.miproject)"
    bl_options = {'REGISTER', 'UNDO'}

    # ExportHelper mix-in class uses this.
    filename_ext = ".miproject"

    filter_glob: StringProperty(
        default="*.miproject",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )
    
    onselc: BoolProperty(
        name="Selected Only",
        description="Including Selected Mesh Only",
        default=False,
    )
    
    discoll: BoolProperty(
        name="Including Disabled Collection",
        description="Including Mesh in Disabled Collection",
        default=False,
    )
    
    diview: BoolProperty(
        name="Including Disabled in Viewport",
        description="Including Mesh Disabled in Viewport",
        default=False,
    )
    
    backfaces: BoolProperty(
        name="Backfaces",
        description="Use Backfaces Mesh",
        default=False,
    )
    
    apply_mod: BoolProperty(
        name="Apply Modifiers",
        description="Use Backfaces Mesh",
        default=True,
    )
    
    author: StringProperty(
        name='Author', 
        description='Author description in miproject', 
        default=''
    )
    
    desk: StringProperty(
        name='Description', 
        description='Description miproject', 
        default=''
    )
    
    def execute(self, context):
        aturan = {
            "author" : self.author, 
            "desk" : self.desk,
            "backfaces": self.backfaces,
            "apply_mod": self.apply_mod
        }
        
        try:
            #Filter mesh yang diexport
            if self.discoll:
                atur_enable_collection(False)
                
            #bpy.ops.object.hide_view_clear()
                    
            if self.diview:
                atur_enabel_view()
            else:
                atur_disable_view()
                    
            atur_select_collection()
            
            #list object tersedia dan Mengkueri ID object
            sobj = []
            vobj = []
            obj_mth = [] #sekalian catat material yang digunakan
            for obj in context.view_layer.objects:
                
                if self.onselc and not obj.select_get():
                    continue
                
                if obj.hide_viewport == False:
                    acak = acak_nama(15)
                    id_o = {"name" : str(obj.name), "id" : acak, "parent" : "", "loc" : {} }
                    sobj.append(id_o)
                    if obj.type == 'MESH':
                        vb = {"name" : str(obj.name), "tex": "", "meshcache": ""}
                        vobj.append(vb)
                        if obj.material_slots:
                            for slot in obj.material_slots:
                                if slot.material:
                                    mth_nama = slot.material.name
                                    obj_mth.append(mth_nama) #material yang digunakan
                    
            #cek daftar tersedia
            if vobj:
                for o in vobj:
                    obj = bpy.data.objects.get(o["name"])
                    obj.hide_select = False
                    
                #list Parent Object
                for o in sobj:
                    o["parent"] = tentukan_parent(o["name"], sobj)
        
                #atur persiapan export
                atur_object_persiapan(context, sobj)
                    
                #atur daftar texture
                mats = [mat.name for mat in bpy.data.materials]
                filter_mat = []
                for mat in mats:
                    if mat in obj_mth and mat not in filter_mat:
                        filter_mat.append(mat)
                mats = cari_tex_filter(filter_mat) #{"mat", "tex_id_file", "tex_name"}
                    
                #mulai mengexport
                export_data(context, vobj, sobj, mats, self.filepath, aturan)
                print("done")
                self.report({'INFO'}, f"Export complete") 
            else:
                self.report({'ERROR'}, "None Mesh can be exported")
                   
            pos_persiap()
            return {'FINISHED'}
            
        except Exception as e: 
            self.report({'ERROR'}, f"{e}")
            print(e)
            pos_persiap()
            return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        
        col = layout.column()
        col.label(text="Including")
        col.prop(self, "onselc")
        col.prop(self, "discoll")
        col.prop(self, "diview")
        
        col = layout.column()
        col.label(text="Mesh")
        col.prop(self, "apply_mod")
        col.prop(self, "backfaces")
        
        col = layout.column()
        col.label(text="Miproject settings")
        col.prop(self, "author")
        col.prop(self, "desk")
        
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Spesial Thanks to:", icon='INFO')
        col.label(text="Yogaindo CR", icon='BLANK1')
        col.label(text="Mr. Doon", icon='BLANK1')
        col.label(text="Aryl Animasi", icon='BLANK1')
        col.label(text="SweetTaky", icon='BLANK1')
        col.label(text="Tcalya", icon='BLANK1')
        col.label(text="Raffsimation", icon='BLANK1')
        col.label(text="Pebry", icon='BLANK1')
        col.label(text="", icon='BLANK1')
        col.label(text="Thanks for survei", icon='INFO')
        col.label(text="Ytber Random Tim", icon='BLANK1')
        col.label(text="Aninextion", icon='BLANK1')
        col.label(text="Tree Animation ID", icon='BLANK1')


#-------------------------------------------------------------  
def kembalikan(): #semua perubahan persiapan export diulang ke awal
    bpy.ops.ed.undo()
    bpy.app.timers.unregister(kembalikan)

def menu_func_exportmiproj(self, context):
    self.layout.operator(ExportMiproj.bl_idname, text="Mine-Imator (.miproject)")
    
    
#---------------------------------------------------------------
def register():
    bpy.utils.register_class(ExportMiproj)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_exportmiproj)

def unregister():
    bpy.utils.unregister_class(ExportMiproj)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_exportmiproj)
    
    
if __name__ == "__main__":
    register()

