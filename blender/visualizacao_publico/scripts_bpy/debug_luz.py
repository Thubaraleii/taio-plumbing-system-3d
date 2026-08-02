import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\blender\visualizacao_publico\cena_publico_teste.blend")
scene = bpy.context.scene
print("view_transform:", scene.view_settings.view_transform)
print("exposure:", scene.view_settings.exposure)
print("look:", scene.view_settings.look)
sol = bpy.data.objects.get("sol_principal")
print("sun energy:", sol.data.energy if sol else None)
world = scene.world
print("world use_nodes", world.use_nodes)
if world.use_nodes:
    bg = world.node_tree.nodes.get("Background")
    if bg:
        print("world bg color/strength", bg.inputs[0].default_value[:], bg.inputs[1].default_value)
print("eevee use_raytracing:", getattr(scene.eevee, "use_raytracing", "N/A"))
