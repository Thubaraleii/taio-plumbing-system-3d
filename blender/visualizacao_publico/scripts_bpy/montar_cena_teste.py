"""
Script headless (bpy) para montar a cena de teste "publico/estilizada" do
modelo -- terreno real por cima, 4 camadas sedimentares planas/paralelas
por baixo (material procedural de "rocha estratificada", sem textura
externa), sill concordante cortando entre duas camadas, dique atravessando
o bloco inteiro. So pra visualizacao (sem apego cientifico) -- as
formacoes reais da CPRM (irregulares) ficaram poluidas visualmente nessa
composicao e foram trocadas por essa simplificacao "por hora".

Roda de fora do Blender (nao precisa abrir a interface):
    "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe" ^
        --background --python montar_cena_teste.py

Gera:
    blender/visualizacao_publico/cena_publico_teste.blend
    blender/visualizacao_publico/renders_teste/preview_01.png
"""
import math
from pathlib import Path

import bpy

BASE = Path(r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio")
MESHES = BASE / "exports" / "meshes"
OUT_DIR = BASE / "blender" / "visualizacao_publico"

# Centro real do modelo (UTM, EPSG:31982) -- recentraliza tudo perto da
# origem do Blender antes de exagerar/renderizar. Z_REF = cota minima
# aproximada do terreno, pra exagero vertical partir do "chao".
CENTRO_X, CENTRO_Y, Z_REF = 593463.0, 7012062.0, 165.0
EXAGERO_Z = 4.0
RESOLUCAO_GRADE_TOPO = 500  # tem que bater com RESOLUCAO em 04_exportar_topografia_para_blender.py

ALPHA_TOPO_TERRENO = 0.55

# Camadas drapeadas no relevo (profundidade abaixo da superficie real, em
# metros -- NAO cota absoluta). Cada camada k comeca em (relevo local -
# profundidade acumulada) e vai ate mais fundo -- assim sempre acompanham o
# terreno, nunca ficam "flutuando" mais altas que ele (bug da versao com
# cotas absolutas).
#
# 5 formacoes sedimentares REAIS (Bacia do Parana, Grupo Guata/Passa Dois),
# mais nova (topo) -> mais antiga (base). Espessuras da literatura (busca em
# 01/08/2026): Rio Bonito ate 269m (poco 1-BN-1-SC), Palermo ~100m
# (ESTIMATIVA -- nao confirmada, checar Loureiro 2024 ou tese de Alfredo
# Wagner/SC), Irati 40-70m (uso 55m), Serra Alta 52-100m na borda leste
# (uso 80m), Teresina 300-400m na borda leste (uso 350m). Mesmos
# valores/cores de ../../../visualizacao_web/gerar_visualizador_3d.py.
NOMES_CAMADAS = ["Teresina", "Serra Alta", "Irati", "Palermo", "Rio Bonito"]
PROFUNDIDADE_CAMADAS_REAL = [0.0, 350.0, 430.0, 485.0, 585.0, 854.0]

# trend regional (mergulho ~0.85 graus, azimute ~106 graus/ESE) extraido dos
# contatos CPRM reais -- ver ../../../../2_Banco_de_Dados/scripts_etl/
# calcular_trend_regional_camadas.py. Mesmos valores dos visualizadores web.
TREND_A, TREND_B = 0.01034, -0.00025
TREND_X0, TREND_Y0 = 592300.0, 7015058.8
Z_REF_TILT = 1053.5  # ancora o plano em boundary(prof=350) = 703.5 (media real do contato Teresina/Serra Alta)


def _cota_contato(x_real, y_real, z_terreno_exag, m):
    """Cota (ja recentralizada/exagerada) do contato de indice m. m=0 (topo
    do pacote) e SEMPRE o proprio relevo real -- nada mapeado acima da
    Teresina. m>0 sao planos inclinados (mergulho regional); o relevo real
    "erode" o que fica acima deles (min contra a cota real do terreno) --
    por isso formacoes mais antigas tambem afloram em certas areas, nao so
    a Teresina."""
    if m == 0:
        return z_terreno_exag
    tilt_real = Z_REF_TILT + TREND_A * (x_real - TREND_X0) + TREND_B * (y_real - TREND_Y0)
    contato_exag = (tilt_real - PROFUNDIDADE_CAMADAS_REAL[m] - Z_REF) * EXAGERO_Z
    return min(contato_exag, z_terreno_exag)


def _hex_para_rgba(hex_cor: str):
    hex_cor = hex_cor.lstrip("#")
    r, g, b = (int(hex_cor[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (r, g, b, 1.0)


CORES_CAMADAS = [_hex_para_rgba(h) for h in ("#D6C79A", "#8C8C86", "#3E362C", "#B5AE93", "#C9A66B")]
COR_SILL = _hex_para_rgba("#A63D2F")
COR_DIQUE = _hex_para_rgba("#1B4332")  # verde escuro

# deposito quaternario (aluviao de vale): usa a cota real do terreno como
# proxy -- so aparece onde o relevo fica abaixo do limiar (~10% mais baixo
# da area, coerente com fundo de vale). Veneer fino colado no terreno.
QUATERNARIO_LIMIAR_REAL = 450.0
QUATERNARIO_ESPESSURA_REAL = 30.0
COR_QUATERNARIO = _hex_para_rgba("#D9CB82")


def limpar_cena():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for bloco in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras, bpy.data.lights):
        for item in list(bloco):
            if item.users == 0:
                bloco.remove(item)


def importar_e_recentralizar(caminho: Path, nome: str):
    if not caminho.exists():
        print(f"aviso: {caminho} nao existe, pulando")
        return None
    # forward_axis='Y', up_axis='Z' = sem rotacao de eixo -- o .obj ja esta em
    # Z-up (X=leste, Y=norte, Z=elevacao UTM), igual ao Blender.
    bpy.ops.wm.obj_import(filepath=str(caminho), forward_axis="Y", up_axis="Z")
    objs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
    if not objs:
        return None
    obj = objs[0]
    obj.name = nome

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    obj.location = (-CENTRO_X, -CENTRO_Y, -Z_REF)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

    obj.scale.z = EXAGERO_Z
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def material_solido(nome: str, cor_rgba, alpha: float = 1.0):
    mat = bpy.data.materials.new(name=nome)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = cor_rgba
        bsdf.inputs["Roughness"].default_value = 0.6
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            mat.blend_method = "BLEND"
    return mat


def material_com_textura(nome: str, caminho_imagem: Path, alpha: float = 1.0):
    mat = bpy.data.materials.new(name=nome)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(caminho_imagem))
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha < 1.0:
        bsdf.inputs["Alpha"].default_value = alpha
        mat.blend_method = "BLEND"
    return mat


def material_estrato(nome: str, cor_base):
    """Material procedural de 'rocha estratificada' -- bandas horizontais
    (ShaderNodeTexWave) + ruido organico, sem nenhuma textura/imagem externa."""
    mat = bpy.data.materials.new(name=nome)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    saida = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    coord = nodes.new("ShaderNodeTexCoord")
    onda = nodes.new("ShaderNodeTexWave")
    ruido = nodes.new("ShaderNodeTexNoise")
    rampa = nodes.new("ShaderNodeValToRGB")
    mistura = nodes.new("ShaderNodeMixRGB")
    bump = nodes.new("ShaderNodeBump")

    onda.wave_type = "BANDS"
    onda.bands_direction = "Z"
    onda.inputs["Scale"].default_value = 45.0
    onda.inputs["Distortion"].default_value = 1.2

    ruido.inputs["Scale"].default_value = 12.0
    ruido.inputs["Detail"].default_value = 4.0

    cor_escura = tuple(c * 0.6 for c in cor_base[:3]) + (1.0,)
    cor_clara = tuple(min(c * 1.3, 1.0) for c in cor_base[:3]) + (1.0,)
    rampa.color_ramp.elements[0].position = 0.4
    rampa.color_ramp.elements[0].color = cor_escura
    rampa.color_ramp.elements[1].position = 0.6
    rampa.color_ramp.elements[1].color = cor_clara

    mistura.blend_type = "MULTIPLY"
    mistura.inputs["Fac"].default_value = 0.25

    links.new(coord.outputs["Object"], onda.inputs["Vector"])
    links.new(coord.outputs["Object"], ruido.inputs["Vector"])
    links.new(onda.outputs["Fac"], rampa.inputs["Fac"])
    links.new(rampa.outputs["Color"], mistura.inputs["Color1"])
    links.new(ruido.outputs["Color"], mistura.inputs["Color2"])
    links.new(mistura.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(onda.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.25
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85

    links.new(bsdf.outputs["BSDF"], saida.inputs["Surface"])
    return mat


def ler_grade_obj(caminho: Path, n: int):
    flat = []
    with open(caminho) as f:
        for linha in f:
            if linha.startswith("v "):
                _, x, y, z = linha.split()
                flat.append((float(x), float(y), float(z)))
    assert len(flat) == n * n, f"esperava {n*n} vertices, achei {len(flat)}"
    return [flat[i * n:(i + 1) * n] for i in range(n)]


def construir_terreno_topo(caminho_obj: Path, n: int):
    """So a superficie do topo (real, texturizada) -- sem paredes/solido,
    as camadas planas por baixo agora fazem esse papel."""
    grade = ler_grade_obj(caminho_obj, n)

    def recentralizar(x, y, z):
        return (x - CENTRO_X, y - CENTRO_Y, (z - Z_REF) * EXAGERO_Z)

    grade_r = [[recentralizar(*grade[i][j]) for j in range(n)] for i in range(n)]

    verts, uvs, faces = [], [], []
    for i in range(n):
        for j in range(n):
            verts.append(grade_r[i][j])
            uvs.append((j / (n - 1), i / (n - 1)))
    for i in range(n - 1):
        for j in range(n - 1):
            v00, v01, v11, v10 = i * n + j, i * n + j + 1, (i + 1) * n + j + 1, (i + 1) * n + j
            faces.append((v00, v01, v11))
            faces.append((v00, v11, v10))

    mesh = bpy.data.meshes.new("topografia_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    uv_layer = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            uv_layer.data[loop_idx].uv = uvs[mesh.loops[loop_idx].vertex_index]

    obj = bpy.data.objects.new("topografia", mesh)
    bpy.context.collection.objects.link(obj)
    mat_topo = material_com_textura("mat_topo_textura", MESHES / "topografia_textura.png", alpha=ALPHA_TOPO_TERRENO)
    obj.data.materials.append(mat_topo)

    xs = [v[0] for row in grade_r for v in row]
    ys = [v[1] for row in grade_r for v in row]
    return obj, grade_r, (min(xs), max(xs), min(ys), max(ys))


def _perimetro(grade_r, n):
    """Pontos (x,y,z_terreno) ao longo do perimetro da grade, em ordem
    (as 4 bordas), pra clipar as paredes das camadas pela topografia real."""
    pontos = []
    pontos += [grade_r[0][j] for j in range(n)]
    pontos += [grade_r[n - 1][j] for j in range(n)]
    pontos += [grade_r[i][0] for i in range(n)]
    pontos += [grade_r[i][n - 1] for i in range(n)]
    return pontos


def construir_camadas(grade_r, n):
    """So as paredes do perimetro, drapeadas no relevo real: cada camada k
    comeca em (relevo local - profundidade acumulada) e vai ate mais fundo.
    Tampas de topo/fundo foram testadas e descartadas -- ver comentario
    mais abaixo."""
    perimetro = _perimetro(grade_r, n)
    n_camadas = len(PROFUNDIDADE_CAMADAS_REAL) - 1

    for k in range(n_camadas):
        verts, faces = [], []

        # paredes: 4 lados, cada um com N segmentos seguindo o perimetro,
        # topo e base sempre relativos a cota real do terreno naquele ponto
        # + trend regional (contato 0 = topo do pacote fica preso no
        # terreno, sem trend; os demais recebem o mergulho regional).
        offset_por_lado = [0, n, 2 * n, 3 * n]
        for lado in range(4):
            ini = offset_por_lado[lado]
            for idx in range(n - 1):
                p0 = perimetro[ini + idx]
                p1 = perimetro[ini + idx + 1]
                x0r, y0r = p0[0] + CENTRO_X, p0[1] + CENTRO_Y
                x1r, y1r = p1[0] + CENTRO_X, p1[1] + CENTRO_Y
                t0, b0 = _cota_contato(x0r, y0r, p0[2], k), _cota_contato(x0r, y0r, p0[2], k + 1)
                t1, b1 = _cota_contato(x1r, y1r, p1[2], k), _cota_contato(x1r, y1r, p1[2], k + 1)
                base_idx = len(verts)
                verts += [(p0[0], p0[1], b0), (p1[0], p1[1], b1), (p1[0], p1[1], t1), (p0[0], p0[1], t0)]
                faces.append((base_idx, base_idx + 1, base_idx + 2))
                faces.append((base_idx, base_idx + 2, base_idx + 3))

        # tampa de fundo (drapeada, grade inteira -- nao so o perimetro, pra
        # acompanhar o relevo no meio tambem). SEM tampa de topo: o topo da
        # camada 1 e a propria superficie do terreno (ja coberta por ele), e
        # o topo das demais coincide exatamente com o fundo da camada acima
        # -- nao duplica geometria.
        fundo_idx = {}
        for i in range(n):
            for j in range(n):
                x, y, z_terreno = grade_r[i][j]
                xr, yr = x + CENTRO_X, y + CENTRO_Y
                fundo_idx[(i, j)] = len(verts)
                verts.append((x, y, _cota_contato(xr, yr, z_terreno, k + 1)))
        for i in range(n - 1):
            for j in range(n - 1):
                v00, v01 = fundo_idx[(i, j)], fundo_idx[(i, j + 1)]
                v11, v10 = fundo_idx[(i + 1, j + 1)], fundo_idx[(i + 1, j)]
                faces.append((v00, v11, v01))
                faces.append((v00, v10, v11))

        mesh = bpy.data.meshes.new(f"camada_{k + 1}_mesh")
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(f"camada_{k + 1}", mesh)
        bpy.context.collection.objects.link(obj)

        mat = material_estrato(f"mat_camada_{k + 1}", CORES_CAMADAS[k])
        obj.data.materials.append(mat)


def construir_quaternario(grade_r, n):
    """Veneer fino (so topo+fundo, sem paredes -- e bem fino, a lacuna nas
    bordas praticamente nao aparece) cobrindo so as celulas onde a cota REAL
    (nao recentralizada) do terreno fica abaixo de QUATERNARIO_LIMIAR_REAL."""
    verts, faces = [], []
    for i in range(n - 1):
        for j in range(n - 1):
            cantos = [grade_r[i][j], grade_r[i][j + 1], grade_r[i + 1][j + 1], grade_r[i + 1][j]]
            cotas_reais = [Z_REF + v[2] / EXAGERO_Z for v in cantos]
            if max(cotas_reais) > QUATERNARIO_LIMIAR_REAL:
                continue
            espessura = QUATERNARIO_ESPESSURA_REAL * EXAGERO_Z
            topo = [(v[0], v[1], v[2]) for v in cantos]
            fundo = [(v[0], v[1], v[2] - espessura) for v in cantos]
            base_idx = len(verts)
            verts += topo + fundo
            faces.append((base_idx, base_idx + 1, base_idx + 2))
            faces.append((base_idx, base_idx + 2, base_idx + 3))
            faces.append((base_idx + 4, base_idx + 6, base_idx + 5))
            faces.append((base_idx + 4, base_idx + 7, base_idx + 6))

    if not faces:
        print("aviso: nenhuma celula abaixo do limiar de quaternario, nada gerado")
        return None

    mesh = bpy.data.meshes.new("quaternario_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("deposito_quaternario", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material_solido("mat_quaternario", COR_QUATERNARIO))
    return obj


def escolher_engine_eevee():
    itens = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    for candidato in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        if candidato in itens:
            return candidato
    return itens[0]


def main():
    limpar_cena()

    topo, grade_r, _bbox_xy = construir_terreno_topo(MESHES / "topografia.obj", RESOLUCAO_GRADE_TOPO)
    construir_camadas(grade_r, RESOLUCAO_GRADE_TOPO)
    construir_quaternario(grade_r, RESOLUCAO_GRADE_TOPO)

    sill = importar_e_recentralizar(MESHES / "sill_diabasio_estilizado.obj", "sill_diabasio_estilizado")
    dique = importar_e_recentralizar(MESHES / "dique_estilizado.obj", "dique_estilizado")

    if sill:
        sill.data.materials.clear()
        sill.data.materials.append(material_solido("mat_sill", COR_SILL))
    if dique:
        dique.data.materials.clear()
        dique.data.materials.append(material_solido("mat_dique", COR_DIQUE))

    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1200))
    alvo = bpy.context.object
    alvo.name = "alvo_camera"

    bpy.ops.object.camera_add(location=(-15000, -34000, 15000))
    camera = bpy.context.object
    camera.name = "camera_publico"
    camera.data.clip_start = 10
    camera.data.clip_end = 200000
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = alvo
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 15000))
    sol = bpy.context.object
    sol.name = "sol_principal"
    sol.data.energy = 3.0
    sol.rotation_euler = (math.radians(55), 0, math.radians(-60))

    # luz de preenchimento -- sem isso a parede de corte voltada pra camera
    # (oposta ao sol principal) fica quase sem luz direta e some no render
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 15000))
    preenchimento = bpy.context.object
    preenchimento.name = "luz_preenchimento"
    preenchimento.data.energy = 1.3
    preenchimento.rotation_euler = (math.radians(65), 0, math.radians(120))

    scene = bpy.context.scene
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = True

    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for espaco in area.spaces:
                if espaco.type == "VIEW_3D":
                    espaco.clip_end = 200000

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "renders_teste").mkdir(exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "cena_publico_teste.blend"))
    print(f"Salvo: {OUT_DIR / 'cena_publico_teste.blend'}")

    scene.render.engine = escolher_engine_eevee()
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.filepath = str(OUT_DIR / "renders_teste" / "preview_01.png")
    bpy.ops.render.render(write_still=True)
    print(f"Render de teste: {scene.render.filepath}")


main()
