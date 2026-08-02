import bpy
import mathutils

bpy.ops.wm.open_mainfile(filepath=r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\blender\visualizacao_publico\cena_publico_teste.blend")

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    bbox = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    zs = [v.z for v in bbox]
    mats = [m.name if m else None for m in obj.data.materials]
    print(f"{obj.name}: Z[{min(zs):.1f},{max(zs):.1f}] materiais={mats}")

print()
for mat in bpy.data.materials:
    print(f"--- {mat.name} ---")
    if not mat.use_nodes:
        print("  use_nodes=False")
        continue
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        print("  SEM Principled BSDF!")
        continue
    base_color_input = bsdf.inputs.get("Base Color")
    linked = base_color_input.is_linked
    print(f"  Base Color linked={linked}", base_color_input.default_value[:] if not linked else "")
    if linked:
        from_node = base_color_input.links[0].from_node
        print(f"  ligado a: {from_node.name} ({from_node.type})")
