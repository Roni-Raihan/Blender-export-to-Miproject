
bl_info = {
    "name": "Export to Miproject",
    "author": "Roni Raihan - TRPHB Animation",
    "version": (0, 3),
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
import numpy as np
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatVectorProperty
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

#--------------------------------------------------------
class extomi_jalan():
    def __init__(self):
        self.ex_obj = []
        self.ex_tex = []
        self.exp_fold = None
        self.bt_name = None
        self.mip_name = None
        self.tex_eror = []
    
    def atur_folder(self, base_fpath):
        #bersihin jalur
        fpath = bpy.path.abspath(base_fpath)
    
        # persiapan bikin folder awal
        self.mip_name = os.path.splitext(bpy.path.basename(fpath))[0]
        self.mip_name = aman_nama(self.mip_name)
        if self.mip_name.replace('_', '') == '':
            self.mip_name = "export_miproject"
        
        exp_dir = os.path.dirname(fpath)
        self.exp_fold = os.path.join(exp_dir, self.mip_name)
        if not os.path.exists(self.exp_fold):
            os.makedirs(self.exp_fold)
        print(f"{self.exp_fold}")
    
    def atur_daftar_export_object(self, context, pilihan_obj):
        daftar_col = []
        def catat_collection(col):
            for child in col.children:
                catat_collection(child)
        
            #filter collection disabled
            if not pilihan_obj["discoll"] and col.exclude:
                return
        
            daftar_col.append(col.name)
    
        for col in context.view_layer.layer_collection.children:
            catat_collection(col)
        daftar_col.append("Scene Collection")
       
        #Catat Obj
        for obj in context.scene.objects:
            ex_o = {"name": obj.name,
                    "type": obj.type,
                    "UID": acak_nama(jum=15),
                    "save_name": f"{aman_nama(obj.name)}_",
                    "parent": "", #isi dengan UID parent
                    "loc_relatif": {"x": 0, "y": 0, "z": 0}, #langsung ubah jadi locasi mineimator space
                    "tex": "",
                    "meshcache_file": ""
                    }
        
            # cek filter only selected object
            if pilihan_obj["onselc"] and not obj.select_get():
                continue
        
            if pilihan_obj["discoll"]:
                self.ex_obj.append(ex_o)
            else:
                for obj_col in obj.users_collection:
                    if obj_col.name in daftar_col:
                        self.ex_obj.append(ex_o)
                        break
        if self.ex_obj:
            return True
        else:
            return False
        
    def atur_parent_object(self):
        def tentukan_parent(obj_name, ex_obj):
            obj = bpy.data.objects.get(obj_name)
            if obj.parent:
                parent = obj.parent
                for o in ex_obj:
                    if parent.name == o["name"]:
                        return f"{o['save_name']}{o['UID']}"
                
                # lanjut bila parent gak ada di daf_o
                return tentukan_parent(parent.name, ex_obj)
            else:
                return "root"
        
        def loc_relatif(o, ex_obj):
            obj = bpy.data.objects.get(o["name"])
            if o["parent"] == "root":
                ox, oy, oz = loc_mip_space(obj.matrix_world.translation)
            
            else:
                obj_parent = None
                for b in ex_obj:
                    if o["parent"] == f"{b['save_name']}{b['UID']}":
                        obj_parent = bpy.data.objects.get(b["name"])
                        break
                    
                if obj_parent is None:
                    ox, oy, oz = loc_mip_space(obj.matrix_world.translation)
                else:
                    obj_parent_loc = obj_parent.matrix_world.translation
                    obj_loc = obj.matrix_world.translation
                    relatif = obj_loc - obj_parent_loc
                    ox, oy, oz = loc_mip_space(relatif)
            return {"x" : ox, "y" : oy, "z" : oz}
            
        for o in self.ex_obj:
            o["parent"] = tentukan_parent(o["name"], self.ex_obj)
        
        for o in self.ex_obj:
            o["loc_relatif"] = loc_relatif(o, self.ex_obj)
        
    def export_atur_texture(self, bt_color):
        def base_tex_buat(warna=(1.0, 1.0, 1.0)):
            nid = acak_nama(jum=15)
            name = f"base_texture_miproject_{nid}"
    
            # Buat image langsung tanpa operator
            img = bpy.data.images.new(name, width=64, height=64, alpha=True)
    
            # Isi pixel
            r, g, b = warna
            pixels = [r, g, b, 1.0] * (64 * 64)
            img.pixels = pixels
    
            # Simpan
            img.file_format = 'PNG'
            fname = f"{name}.png"
            fpath = os.path.join(self.exp_fold, fname)
            img.save(filepath=fpath, save_copy=True)
    
            # Hapus dari data setelah disimpan
            bpy.data.images.remove(img)
            
            return fname
        
        def export_tex(tex_name):
            try:
                img = bpy.data.images.get(tex_name)
                name = f"{aman_nama(tex_name)}_{acak_nama(jum=15)}"
                fname = f"{name}.png"
                fpath = os.path.join(self.exp_fold, fname)
                img.save(filepath=fpath, save_copy=True)
                
                print("Texture successfully exported:")
                print(f"{tex_name} | {fname}")
                return fname
            
            except Exception as e:
                self.tex_eror.append(tex_name)
                print(f"Cannot export: {tex_name}")
                print(e)
                return None
        
        def cari_texture(mat):
            if mat.use_nodes:
                for node in mat.node_tree.nodes:  #loop ke semua node
                    if node.type == 'TEX_IMAGE':  #cari node texture
                        if node.image:            #cek apakah ada gambarnya
                            img = node.image
                            
                            if img.source == 'FILE': #cek tipe gambar
                                if img.packed_file:  #apakah sudah di paket
                                    return node.image.name
                                
                                else:   #kalo gak dipaket
                                    if img.filepath:
                                        imgfpath = bpy.path.abspath(img.filepath)
                                        if os.path.exists(imgfpath): #cek gambarnya apakah ada
                                            return node.image.name
                                        else:
                                            print(f"Mising {imgfpath}")
                                    
                            elif img.source == 'GENERATED':
                                return node.image.name
                return None
        
        self.bt_name = base_tex_buat(bt_color)
        daftar_mat = [] #{"name": "", "tex": ""}
        for mat in bpy.data.materials:
            tex = cari_texture(mat)
            if tex:
                daftar_mat.append({"name": mat.name, "tex": tex})
                
        ada_tex = []
        for mat in daftar_mat:
            if mat["tex"] in ada_tex:
                continue
            file_tex = export_tex(mat["tex"])
            if file_tex:
                self.ex_tex.append({"name": mat["tex"],
                                    "file": file_tex
                                    })
            ada_tex.append(mat["tex"])
                
        for o in self.ex_obj:
            obj = bpy.data.objects.get(o["name"])
            tex = os.path.splitext(self.bt_name)[0]
            for slot in obj.material_slots:
                if slot.material:
                    mat = slot.material.name
                    for m in daftar_mat:
                        if mat == m["name"]:
                            for t in self.ex_tex:
                                if m["tex"] == t["name"]:
                                    tex = t["file"]
                                    break
                            break
                    if tex != os.path.splitext(self.bt_name)[0]:
                        break
            o["tex"] = tex
            
    def export_meshcache(self, o, apply_mod = False):
        #self.ex_obj#--------------
        #"name": obj.name,
        #"type": obj.type,
        #"UID": acak_nama(jum=15),
        #"save_name": f"{aman_nama(obj.name)}_",
        #"parent": "", #isi dengan UID parent
        #"loc_relatif": {"x": 0, "y": 0, "z": 0}, #langsung ubah jadi locasi mineimator space
        #"tex": "",
        #"meshcache_file": ""
        
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
        #----------------------------------------

        print(f"Calculate {o['name']}")
        obj = bpy.data.objects.get(o["name"])
        
        if apply_mod:
            depg = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depg)
        else:
            obj_eval = obj
        mesh = obj_eval.to_mesh()
        mesh.calc_loop_triangles()
        
        uv_layer = mesh.uv_layers.active.data if mesh.uv_layers.active else None
        
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().normalized()
        origin = matrix.translation
        
        vertex_count = len(mesh.loop_triangles) * 3
        
        # kumpulkan semua vertex ke buffer
        buf = bytearray()
        for til in mesh.loop_triangles:
            for i in [0, 2, 1]:
                li = til.loops[i]
                loop = mesh.loops[li]
                v = mesh.vertices[loop.vertex_index]
                
                # koordinat
                co_rel = matrix @ v.co - origin
                
                # Blender  mi  * 16.0
                    #    x     z   
                    #    y     x  
                    #    z     y
                    
                x = (-co_rel.x * 16.0) + 8.0
                y = (co_rel.y * 16.0) + 8.0
                z = co_rel.z * 16.0
                
                # normal
                nx, ny, nz = normal_matrix @ v.normal
                nbx = int(round(((nx + 1.0) * 0.5) * 255)) & 0xFF
                nby = int(round(((ny + 1.0) * 0.5) * 255)) & 0xFF
                nbz = int(round(((nz + 1.0) * 0.5) * 255)) & 0xFF
                normal = nbx | (nby << 8) | (nbz << 16)
                
                # uv
                if uv_layer:
                    uv = uv_layer[li].uv
                    uv_u, uv_v = uv.x, -uv.y
                else:
                    uv_u, uv_v = 0.0, 0.0
            
                buf += VER_STR.pack(x, y, z, normal, 0xFFFFFFFF, uv_u, uv_v, 0, 0)
                
        obj_eval.to_mesh_clear()
        
        # index sekaligus
        index_buf = struct.pack(f"<{vertex_count}I", *range(vertex_count))
        
        # tulis ke file — seminimal mungkin write call
        fpath = os.path.join(self.exp_fold, f"{o['save_name']}{o['UID']}.schematic.meshcache")
        with open(fpath, "wb") as f:
            f.write(struct.pack("<QQQQB", 2, 1, 1, 1, 1))
            f.write(struct.pack(">QQ", vertex_count, vertex_count))
            f.write(buf)
            f.write(index_buf)
            
        print(f"{vertex_count // 3} triangles — {fpath}")
        return f"{o['save_name']}{o['UID']}.schematic"
    
    def export_meshcache_dengan_numpy(self, o, apply_mod = False, normal_mode = 'SMOOTH'):
        #self.ex_obj#--------------
        #"name": obj.name,
        #"type": obj.type,
        #"UID": acak_nama(jum=15),
        #"save_name": f"{aman_nama(obj.name)}_",
        #"parent": "", #isi dengan UID parent
        #"loc_relatif": {"x": 0, "y": 0, "z": 0}, #langsung ubah jadi locasi mineimator space
        #"tex": "",
        #"meshcache_file": ""
        
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
        #----------------------------------------
        
        print(f"Calculate {o['name']}")
        obj = bpy.data.objects.get(o["name"])
        
        if apply_mod:
            depg = bpy.context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depg)
        else:
            obj_eval = obj
    
        mesh = obj_eval.to_mesh()
        mesh.calc_loop_triangles()
        
        #Hitung origin object pake np
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().normalized()
        origin = np.array(matrix.translation, dtype=np.float32)
        mat = np.array(matrix, dtype=np.float32).T  # 4x4
        nmat = np.array(normal_matrix, dtype=np.float32).T  # 3x3
        
        tri_count = len(mesh.loop_triangles)
        vertex_count = tri_count * 3
        
        #Ambil semua data sekaligus via foreach_get
        
        # koordinat semua vertex
        vco = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", vco)
        vco = vco.reshape(-1, 3)
        
        # normal semua vertex
        vnor = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
        mesh.vertices.foreach_get("normal", vnor)
        vnor = vnor.reshape(-1, 3)
    
        # loop triangle — vertex index dan loop index
        tri_loops = np.empty(tri_count * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("loops", tri_loops)
        tri_loops = tri_loops.reshape(-1, 3)  # (tri_count, 3)
    
        tri_verts = np.empty(tri_count * 3, dtype=np.int32)
        mesh.loop_triangles.foreach_get("vertices", tri_verts)
        tri_verts = tri_verts.reshape(-1, 3)  # (tri_count, 3)
            
        
        # uv
        has_uv = mesh.uv_layers.active is not None
        if has_uv:
            uv_data = np.empty(len(mesh.loops) * 2, dtype=np.float32)
            mesh.uv_layers.active.data.foreach_get("uv", uv_data)
            uv_data = uv_data.reshape(-1, 2)  # (loop_count, 2)
            
            
        # --- Normal sesuai mode (dibaca sebelum winding di-reorder) ---
        if normal_mode == 'FLAT':
            tri_nor = np.empty(tri_count * 3, dtype=np.float32)
            mesh.loop_triangles.foreach_get("normal", tri_nor)
            tri_nor = tri_nor.reshape(-1, 3)  # (tri_count, 3)
        elif normal_mode == 'AUTO':
            cn = np.empty(len(mesh.loops) * 3, dtype=np.float32)
            mesh.corner_normals.foreach_get("vector", cn)
            cn = cn.reshape(-1, 3)  # (loop_count, 3)
        else:  # 'SMOOTH'
            vnor = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
            mesh.vertices.foreach_get("normal", vnor)
            vnor = vnor.reshape(-1, 3)  # (vertex_count_mesh, 3)
            
        # --- Reorder winding [0, 2, 1] ---
        order = np.array([0, 2, 1])
        tri_loops = tri_loops[:, order]   # (tri_count, 3)
        tri_verts = tri_verts[:, order]   # (tri_count, 3)
    
        # flatten — jadi (vertex_count,)
        loop_idx = tri_loops.reshape(-1)   # index ke mesh.loops
        vert_idx = tri_verts.reshape(-1)   # index ke mesh.vertices
    
        # --- Transformasi koordinat ---
        # ambil koordinat per vertex yang dipakai
        coords = vco[vert_idx]  # (vertex_count, 3)
    
        # transform ke world space: lebih proper pakai mat 4x4:
        ones = np.ones((vertex_count, 1), dtype=np.float32)
        coords_h = np.hstack([coords, ones])  # (vertex_count, 4)
        coords_world = (coords_h @ mat)[:, :3]  # (vertex_count, 3)
    
        # kurangi origin (object space relative)
        coords_rel = coords_world - origin
    
        # konversi ke MI space
        mx = (-coords_rel[:, 0] * 16.0) + 8.0
        my = (coords_rel[:, 1] * 16.0) + 8.0
        mz = coords_rel[:, 2] * 16.0
    
        # --- Transformasi normal ---
        if normal_mode == 'FLAT':
            normals = np.repeat(tri_nor, 3, axis=0)   # 1 normal face -> 3 vertex
        elif normal_mode == 'AUTO':
            normals = cn[loop_idx]                    # (vertex_count, 3)
        else:  # 'SMOOTH'
            normals = vnor[vert_idx]                  # (vertex_count, 3)
        normals_world = normals @ nmat
    
        nx = ((normals_world[:, 0] + 1.0) * 0.5 * 255).astype(np.uint32) & 0xFF
        ny = ((normals_world[:, 1] + 1.0) * 0.5 * 255).astype(np.uint32) & 0xFF
        nz = ((normals_world[:, 2] + 1.0) * 0.5 * 255).astype(np.uint32) & 0xFF
        packed_normal = nx | (ny << 8) | (nz << 16)
        
        # --- UV ---
        if has_uv:
            uv = uv_data[loop_idx]  # (vertex_count, 2)
            uv_u = uv[:, 0]
            uv_v = -uv[:, 1]
        else:
            uv_u = np.zeros(vertex_count, dtype=np.float32)
            uv_v = np.zeros(vertex_count, dtype=np.float32)
            
        # --- Pack ke buffer ---
        # format per vertex: x, y, z, normal, 0xFFFFFFFF, uv_u, uv_v, 0, 0
        color = np.full(vertex_count, 0xFFFFFFFF, dtype=np.uint32)
        pad = np.zeros(vertex_count, dtype=np.uint32)
    
        # susun kolom sesuai VER_STR: <fffIIffII
        buf = np.zeros(vertex_count, dtype=np.dtype([
            ('x', '<f4'), ('y', '<f4'), ('z', '<f4'),
            ('normal', '<u4'), ('color', '<u4'),
            ('uv_u', '<f4'), ('uv_v', '<f4'),
            ('pad1', '<u4'), ('pad2', '<u4'),
        ]))
        
        buf['x'] = mx
        buf['y'] = my
        buf['z'] = mz
        buf['normal'] = packed_normal
        buf['color'] = color
        buf['uv_u'] = uv_u
        buf['uv_v'] = uv_v
    
        obj_eval.to_mesh_clear()
        
        # index
        index_buf = np.arange(vertex_count, dtype=np.uint32)
    
        # --- Tulis file ---
        fpath = os.path.join(self.exp_fold, f"{o['save_name']}{o['UID']}.schematic.meshcache")
        with open(fpath, "wb") as f:
            f.write(struct.pack("<QQQQB", 2, 1, 1, 1, 1))
            f.write(struct.pack(">QQ", vertex_count, vertex_count))
            f.write(buf.tobytes())
            f.write(index_buf.tobytes())
    
        print(f"{vertex_count // 3} triangles — {fpath}")
        return f"{o['save_name']}{o['UID']}.schematic"

    def generate_mip(self, aturan):
        print("create .miproject")
        # Blender  mi  json  * 16.0
        #    x     z    y
        #    y     x    x
        #    z     y    z
        #self.ex_obj =  "name": obj.name,
        #               "type": obj.type,
        #               "UID": acak_nama(jum=15),
        #               "save_name": f"{aman_nama(obj.name)}_",
        #               "parent": "", #isi dengan UID parent
        #               "loc_relatif": {"x": 0, "y": 0, "z": 0}, #langsung ubah jadi locasi mineimator space
        #               "tex": "",
        #               "meshcache_file": ""
        #self.ex_tex = {"name": mat["tex"], "file": file_tex}
        #self.exp_fold = None
        #self.bt_name = None
        #self.mip_name = None
        
        data = {
            "format": 34,
            "created_in": "Exporter to Miproject by TRPHB Animation Add-on",
            "project": {
                "name": self.mip_name,
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
        add_tex(self.bt_name) #base_texture
        for t in self.ex_tex: # texture
            add_tex(t["file"])
            
        #tambah object
        for o in self.ex_obj:
            if o["type"] == 'MESH':
                resource = {
                    "id": f"{o['save_name']}{o['UID']}_res",
                    "type": "scenery",
                    "filename": o["meshcache_file"],
                    "scenery_tl_add": True,
                    "material_format": 2
                }
                
                templates = {
                    "id": f"{o['save_name']}{o['UID']}_temp",
                    "type": "scenery",
                    "name": o["name"],
                    "scenery": f"{o['save_name']}{o['UID']}_res",
                    "block":{
                        "tex": os.path.splitext(o["tex"])[0],
                        "tex_material": "default",
                        "tex_normal": "default",
                        "repeat_enable": False,
                        "repeat": [ 1, 1, 1 ]
                    }
                }
        
                timelines = {
                    "id": f"{o['save_name']}{o['UID']}",
                    "type": "scenery",
                    "name": "",
                    "temp": f"{o['save_name']}{o['UID']}_temp",
                    "default_values": {
                        "POS_X": o["loc_relatif"]["x"],
                        "POS_Y": o["loc_relatif"]["y"],
                        "POS_Z": o["loc_relatif"]["z"]
                    },
                    "keyframes": {
                        "0": {
                            "POS_X": o["loc_relatif"]["x"],
                            "POS_Y": o["loc_relatif"]["y"],
                            "POS_Z": o["loc_relatif"]["z"]
                        }
                    },
                    "parent": o["parent"],
                    "backfaces": aturan["backfaces"]
                }
        
                data["resources"].append(resource)
                data["templates"].append(templates)
                data["timelines"].append(timelines)
            
            else:
                timelines = {
                    "id": f"{o['save_name']}{o['UID']}",
                    "type": "folder",
                    "name": o["name"],
                    "temp": "null",
                    "default_values": {
                        "POS_X": o["loc_relatif"]["x"],
                        "POS_Y": o["loc_relatif"]["y"],
                        "POS_Z": o["loc_relatif"]["z"]
                    },
                    "keyframes": {
                        "0": {
                            "POS_X": o["loc_relatif"]["x"],
                            "POS_Y": o["loc_relatif"]["y"],
                            "POS_Z": o["loc_relatif"]["z"]
                        }
                    },
                    "parent": o["parent"]
                }
                
                data["timelines"].append(timelines)
                
        fmip = os.path.join(self.exp_fold, f"{self.mip_name}.miproject")
        with open(fmip, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
            
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
    
    #~~~~~~~~~~~~~~
    
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
    
    #~~~~~~~~~~~~~~~
    
    backfaces: BoolProperty(
        name="Backfaces",
        description="Use Backfaces Mesh",
        default=False,
    )
    
    apply_mod: BoolProperty(
        name="Apply Modifiers",
        description="Apply Modifiers",
        default=True,
    )
    
    shade_mode: EnumProperty(
        name="Shading",
        description="Shading for mesh and shadows",
        items=[
            ('AUTO', "Auto", "Use own shading: flat/smooth, sharp edges, custom normals"),
            ('FLAT', "Flat", "Every face is shaded independently"),
            ('SMOOTH', "Smooth", "Average normals per vertex (old behavior)")
        ],
        default='AUTO',
    )
    
    bt_color: FloatVectorProperty(
        name="Base Texture Color",
        description="Color for Generated Base Texture",
        default=(1.0, 1.0, 1.0),
        min=0,
        max=1,
        subtype='COLOR'
    )
    
    author: StringProperty(
        name='Author', 
        description='Author description in miproject', 
        default=''
    )
    
    desk: StringProperty(
        name='Description', 
        description='Description miproject', 
        default='Exporter to Miproject by TRPHB Animation Add-on'
    )
    
    def execute(self, context):
        aturan = {
            "author" : self.author, 
            "desk" : self.desk,
            "backfaces": self.backfaces,
        }
        
        pilihan_obj = {
            "onselc" : self.onselc,
            "discoll" : self.discoll,
        }
        
        exporter = extomi_jalan()
        
        #pilah object apa aja yang di export
        ada = exporter.atur_daftar_export_object(context, pilihan_obj)
        if not ada:
            self.report({'ERROR'}, "None object can export")
            return {'CANCELLED'}
        exporter.atur_parent_object()#atur dan cari parent
        
        #export
        exporter.atur_folder(self.filepath)#atur folder
        exporter.export_atur_texture(self.bt_color)#export texture
        for o in exporter.ex_obj:
            if o["type"] == 'MESH':#export meshcache
                o["meshcache_file"] = exporter.export_meshcache_dengan_numpy(o, self.apply_mod, self.shade_mode) #exporter.export_meshcache(o, self.apply_mod)
                
        #Generate Miproject
        exporter.generate_mip(aturan)
        
        
        if len(exporter.tex_eror) > 0:
            et = ", ".join(exporter.tex_eror)
            self.report({'WARNING'}, f"Scene Was Exported Successfully, But Some Textures Could Not Be Exported: {et}")
        else:
            self.report({'INFO'}, "Successful Export")
        print("Done")
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        col = layout.column()
        col.label(text="Including")
        col.prop(self, "onselc")
        col.prop(self, "discoll")
        
        col = layout.column()
        col.label(text="Mesh")
        col.prop(self, "shade_mode")
        col.prop(self, "apply_mod")
        col.prop(self, "backfaces")
        
        col.label(text="Base Texture")
        col.prop(self, "bt_color", text="Color")
        
        col = layout.column()
        col.label(text="Miproject settings")
        col.prop(self, "author")
        col.prop(self, "desk")
        
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Addon By Roni Raihan", icon='INFO')
        col.label(text="From TRPHB Animation", icon='BLANK1')
        row = col.row()
        row.operator("extomi.trphb_page", icon='URL')
        row.operator("extomi.github", icon='URL')
        
        col.label(text="", icon='BLANK1')
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
        
class EXTOMI_OT_open_trphb_page(Operator):
    bl_idname = "extomi.trphb_page"
    bl_label = "TRPHB Animation"
    
    def execute(self, context):
        import webbrowser
        webbrowser.open("https://www.youtube.com/c/TRPHBAnimation")  # ganti URL-nya
        return {'FINISHED'}
    
class EXTOMI_OT_open_github(Operator):
    bl_idname = "extomi.github"
    bl_label = "Github"
    
    def execute(self, context):
        import webbrowser
        webbrowser.open("https://github.com/Roni-Raihan/Blender-export-to-Miproject")  # ganti URL-nya
        return {'FINISHED'}

#-------------------------------------------------------------  
def menu_func_exportmiproj(self, context):
    self.layout.operator(ExportMiproj.bl_idname, text="Mine-Imator (.miproject)")


#---------------------------------------------------------------
def register():
    bpy.utils.register_class(ExportMiproj)
    bpy.utils.register_class(EXTOMI_OT_open_trphb_page)
    bpy.utils.register_class(EXTOMI_OT_open_github)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_exportmiproj)

def unregister():
    bpy.utils.unregister_class(ExportMiproj)
    bpy.utils.unregister_class(EXTOMI_OT_open_trphb_page)
    bpy.utils.unregister_class(EXTOMI_OT_open_github)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_exportmiproj)
    
    
if __name__ == "__main__":
    register()