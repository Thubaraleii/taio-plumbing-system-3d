"""
Recalcula o modelo GemPy (reaproveitando o script 02) e exporta cada
superficie como um arquivo .obj separado, pronto para importar no Blender
(File > Import > Wavefront (.obj)).

Nota: a funcao gp.save_model/load_model do GemPy ainda esta em
desenvolvimento e nao preserva as malhas calculadas (so a definicao do
modelo) — por isso este script recalcula o modelo do zero chamando o
script 02 em vez de tentar reabrir o .gempy salvo. Se voce mudou algo no
script 02 (extensao, formacoes, pontos), o efeito ja aparece aqui
automaticamente.

Tambem aplica um recorte duro (em planta, XY) nas superficies que tem
poligono de referencia digitalizado (dados_base/poligon_intrusiva.shp):
sill_diabasio fica limitado a uniao dos poligonos 'Soleira', dique a uniao
dos poligonos 'Dique'. O GemPy interpola um campo continuo em toda a
extensao do modelo e pode extrapolar mal longe dos pontos de controle -- o
poligono digitalizado (satelite/mapa) e o que garante que a malha final nao
"estoure" pra fora de onde o corpo foi realmente identificado, mesmo que o
campo potencial sozinho sugerisse mais longe. Formacoes sem poligono
(a sequencia sedimentar) saem sem recorte.

Uso:
    python scripts/03_exportar_obj_para_blender.py
"""
import importlib.util
from pathlib import Path

import geopandas as gpd
import numpy as np

BASE = Path(__file__).parent.parent
EXPORTS_DIR = BASE / "exports" / "meshes"

POLIGONO_REFERENCIA = BASE.parent / "2_Banco_de_Dados" / "dados_base" / "poligon_intrusiva.shp"
FORMACAO_PARA_TIPO_POLIGONO = {"sill_diabasio": "Soleira", "dique": "Dique"}


def carregar_mascaras():
    """Retorna {formation: shapely (Multi)Polygon} com a uniao dos poligonos
    digitalizados de cada formacao, ou {} se o arquivo nao existir ainda."""
    if not POLIGONO_REFERENCIA.exists():
        return {}
    gdf = gpd.read_file(POLIGONO_REFERENCIA)
    mascaras = {}
    for formacao, tipo in FORMACAO_PARA_TIPO_POLIGONO.items():
        subset = gdf[gdf["tipo"] == tipo]
        if len(subset):
            mascaras[formacao] = subset.union_all()
    return mascaras


def recortar_malha(vertices, faces, mascara):
    """Mantem so os triangulos cujo centroide (X,Y) cai dentro da mascara."""
    from shapely.geometry import Point
    from shapely.prepared import prep

    mascara_preparada = prep(mascara)
    tri_verts = vertices[faces]
    centroides = tri_verts[:, :, :2].mean(axis=1)
    mantidos = np.array([mascara_preparada.contains(Point(c)) for c in centroides])
    return faces[mantidos]


def _carregar_modulo_02():
    caminho = Path(__file__).parent / "02_montar_modelo_gempy.py"
    spec = importlib.util.spec_from_file_location("montar_modelo_gempy", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def compactar_malha(vertices, faces):
    """Remove vertices que ficaram sem nenhum triangulo depois do recorte,
    renumerando os indices das faces."""
    usados = np.unique(faces)
    remap = {antigo: novo for novo, antigo in enumerate(usados)}
    faces_novas = np.array([[remap[i] for i in face] for face in faces])
    return vertices[usados], faces_novas


def exportar_obj(vertices, edges, nome_arquivo: Path):
    """Escreve uma malha (vertices Nx3, faces triangulares Mx3) em formato OBJ."""
    with open(nome_arquivo, "w") as f:
        f.write(f"# {nome_arquivo.stem} - exportado do GemPy\n")
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in edges:
            # OBJ usa indices comecando em 1
            f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")


def main():
    print("Recalculando o modelo (via script 02)...")
    modulo_02 = _carregar_modulo_02()
    geo_model = modulo_02.main()

    if geo_model is None:
        print("Nao foi possivel montar o modelo (veja mensagens acima). Nada exportado.")
        return

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # elements_names inclui tambem o "basement" (embasamento), que e a unidade
    # mais antiga/de fundo e nao gera malha propria (fica implicito). Por isso
    # so pareamos os N primeiros nomes com as N malhas calculadas.
    nomes_superficies = geo_model.structural_frame.elements_names
    meshes = geo_model.solutions.dc_meshes

    mascaras = carregar_mascaras()
    if mascaras:
        print(f"Recorte duro ativo para: {list(mascaras.keys())} (dados_base/poligon_intrusiva.shp)")

    print(f"\nExportando {len(meshes)} superficie(s) para .obj...")
    for nome, mesh in zip(nomes_superficies[: len(meshes)], meshes):
        destino = EXPORTS_DIR / f"{nome}.obj"
        # O GemPy calcula internamente em coordenadas normalizadas/reescaladas;
        # aplicamos a transformacao inversa para voltar as coordenadas reais
        # (mesmo sistema UTM do raster/shapefiles), senao o modelo nao bate
        # com o terreno/ortomosaico quando importado no Blender.
        vertices_reais = geo_model.input_transform.apply_inverse(mesh.vertices)
        faces = mesh.edges

        if nome in mascaras:
            n_antes = len(faces)
            faces = recortar_malha(vertices_reais, faces, mascaras[nome])
            vertices_reais, faces = compactar_malha(vertices_reais, faces)
            print(f"  {nome}: recorte manteve {len(faces)}/{n_antes} triangulos dentro do poligono")

        exportar_obj(vertices_reais, faces, destino)
        print(f"  {nome} -> {destino}  ({len(vertices_reais)} vertices, {len(faces)} faces)")

    print(f"\nPronto. Abra o Blender e importe os .obj de: {EXPORTS_DIR}")
    print("File > Import > Wavefront (.obj) — pode selecionar varios arquivos de uma vez.")


if __name__ == "__main__":
    main()
