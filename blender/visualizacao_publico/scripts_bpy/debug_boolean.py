import bpy
from pathlib import Path

MESHES = Path(r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\exports\meshes")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

bpy.ops.wm.obj_import(filepath=str(MESHES / "topografia.obj"), forward_axis="Y", up_axis="Z")
topo = bpy.context.selected_objects[0]

bpy.ops.object.select_all(action="DESELECT")
topo.select_set(True)
bpy.context.view_layer.objects.active = topo
mod = topo.modifiers.new(name="SOLIDIFY", type="SOLIDIFY")
mod.thickness = 500
mod.offset = -1
mod.use_rim = True
bpy.ops.object.modifier_apply(modifier=mod.name)
print("apos solidify:", len(topo.data.vertices), "verts", len(topo.data.polygons), "faces")

# bbox real (coordenadas UTM, nao recentralizadas aqui)
xs = [v.co.x for v in topo.data.vertices]
ys = [v.co.y for v in topo.data.vertices]
cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
print("centro real:", cx, cy, "bbox X", min(xs), max(xs), "Y", min(ys), max(ys))

bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, 700))
cortador = bpy.context.object
cortador.scale = (30000, 30000, 6000)

for solver in ["EXACT", "FLOAT"]:
    topo_copia = topo.copy()
    topo_copia.data = topo.data.copy()
    bpy.context.collection.objects.link(topo_copia)

    bpy.ops.object.select_all(action="DESELECT")
    topo_copia.select_set(True)
    bpy.context.view_layer.objects.active = topo_copia
    mod_bool = topo_copia.modifiers.new(name="BOOLEAN", type="BOOLEAN")
    mod_bool.operation = "DIFFERENCE"
    mod_bool.object = cortador
    mod_bool.solver = solver
    bpy.ops.object.modifier_apply(modifier=mod_bool.name)
    print(f"solver={solver}: {len(topo_copia.data.vertices)} verts, {len(topo_copia.data.polygons)} faces")
