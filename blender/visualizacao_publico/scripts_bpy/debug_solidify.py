import bpy
from pathlib import Path

MESHES = Path(r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\exports\meshes")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

bpy.ops.wm.obj_import(filepath=str(MESHES / "topografia.obj"), forward_axis="Y", up_axis="Z")
topo = bpy.context.selected_objects[0]
print("apos import:", len(topo.data.vertices), "vertices")
print("bbox local (min/max por eixo):")
xs = [v.co.x for v in topo.data.vertices]
ys = [v.co.y for v in topo.data.vertices]
zs = [v.co.z for v in topo.data.vertices]
print(" X", min(xs), max(xs))
print(" Y", min(ys), max(ys))
print(" Z", min(zs), max(zs))

bpy.ops.object.select_all(action="DESELECT")
topo.select_set(True)
bpy.context.view_layer.objects.active = topo
mod = topo.modifiers.new(name="SOLIDIFY", type="SOLIDIFY")
mod.thickness = 1400
mod.offset = -1
mod.use_rim = True
mod.use_rim_only = False
bpy.ops.object.modifier_apply(modifier=mod.name)

print("apos solidify:", len(topo.data.vertices), "vertices,", len(topo.data.polygons), "faces")
xs = [v.co.x for v in topo.data.vertices]
ys = [v.co.y for v in topo.data.vertices]
zs = [v.co.z for v in topo.data.vertices]
print(" X", min(xs), max(xs))
print(" Y", min(ys), max(ys))
print(" Z", min(zs), max(zs))
