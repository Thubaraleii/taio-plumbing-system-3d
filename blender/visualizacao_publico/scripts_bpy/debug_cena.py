import bpy
import mathutils

caminho_blend = r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\blender\visualizacao_publico\cena_publico_teste.blend"
bpy.ops.wm.open_mainfile(filepath=caminho_blend)

for obj in bpy.data.objects:
    print(f"--- {obj.name} ({obj.type}) ---")
    print("  location:", obj.location)
    print("  scale:", obj.scale)
    if obj.type == "MESH":
        bbox = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        xs = [v.x for v in bbox]; ys = [v.y for v in bbox]; zs = [v.z for v in bbox]
        print(f"  bbox world: X[{min(xs):.1f},{max(xs):.1f}] Y[{min(ys):.1f},{max(ys):.1f}] Z[{min(zs):.1f},{max(zs):.1f}]")
        print("  n_verts:", len(obj.data.vertices))
    if obj.type == "CAMERA":
        print("  clip_start/end:", obj.data.clip_start, obj.data.clip_end)
        print("  world matrix translation:", obj.matrix_world.translation)
        print("  constraints:", [c.type for c in obj.constraints])
        for c in obj.constraints:
            if c.type == "TRACK_TO":
                print("    target:", c.target.name if c.target else None, "target loc:", c.target.location if c.target else None)
    if obj.type == "LIGHT":
        print("  light type/energy:", obj.data.type, obj.data.energy)

scene = bpy.context.scene
print("scene.camera:", scene.camera.name if scene.camera else None)
print("render engine:", scene.render.engine)
print("world:", scene.world.name if scene.world else None)
if scene.world:
    print("  use_nodes:", scene.world.use_nodes)
