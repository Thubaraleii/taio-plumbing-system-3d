import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\blender\visualizacao_publico\cena_publico_teste.blend")
scene = bpy.context.scene
scene.view_settings.view_transform = "Standard"

for nome in ["topografia", "sill_diabasio_estilizado", "dique_estilizado"]:
    obj = bpy.data.objects.get(nome)
    if obj:
        obj.hide_render = True

scene.render.filepath = r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio\blender\visualizacao_publico\renders_teste\preview_isolado.png"
bpy.ops.render.render(write_still=True)
print("renderizado isolado")
