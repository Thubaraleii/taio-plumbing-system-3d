"""
Gera malhas SOLIDAS (com espessura real) dos lobos de sill/dique, so para
visualizacao -- NAO substitui as superficies finas calculadas pelo GemPy
(sill_diabasio.obj / dique.obj em exports/meshes/), que continuam sendo o
resultado "de verdade" do modelo implicito.

Pega cada poligono de dados_base/poligon_intrusiva.shp (o mesmo usado para
recortar as superficies em 03_exportar_obj_para_blender.py), preenche o
interior com triangulos (topo), drapeia na topografia real, e extrude para
baixo pela espessura medida em campo (pontos_unificados/pontos_unificados.csv,
coluna espessura_m) -- cria um "prisma" solido com o contorno exato do
poligono em planta.

Espessura usada (mediana das medidas de campo, ver ANALISE em
pontos_unificados): sill_diabasio ~27m (variacao real 6-130m, ainda poucos
pontos por lobo pra individualizar), dique ~6m (variacao 3-12m).

Saida: exports/meshes/sill_diabasio_solido.obj, dique_solido.obj

Uso:
    python scripts/05_gerar_solidos_visualizacao.py
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from scipy.spatial import Delaunay
from shapely.geometry import Point
from shapely.prepared import prep

BASE = Path(__file__).parent.parent
POLIGONO_REFERENCIA = BASE.parent / "2_Banco_de_Dados" / "dados_base" / "poligon_intrusiva.shp"
TOPO_NPY = BASE / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
EXPORTS_DIR = BASE / "exports" / "meshes"

# tipo (coluna do shapefile) -> (nome da formacao, espessura tipica em m)
CONFIG = {
    "Soleira": ("sill_diabasio_solido", 27.0),
    "Dique": ("dique_solido", 6.0),
}
PASSO_DENSIFICACAO = 40.0  # m -- espacamento de pontos ao longo do contorno pra triangular o interior


def montar_interpolador_topografia():
    xyz = np.load(TOPO_NPY)
    linear = LinearNDInterpolator(xyz[:, :2], xyz[:, 2])
    nearest = NearestNDInterpolator(xyz[:, :2], xyz[:, 2])

    def drapear(x, y):
        z = linear(x, y)
        if np.isnan(z):
            z = nearest(x, y)
        return float(z)

    return drapear


def densificar_contorno(poligono, passo: float):
    linha = poligono.exterior
    comprimento = linha.length
    n = max(int(comprimento // passo), 3)
    return [linha.interpolate(d).coords[0][:2] for d in np.linspace(0, comprimento, n, endpoint=False)]


def triangular_interior(poligono, passo: float):
    """Triangulacao (Delaunay + filtro pelo poligono) do interior -- nao e
    uma triangulacao restrita de verdade, mas com contorno bem denso fica
    uma aproximacao boa o suficiente pra visualizacao."""
    contorno = densificar_contorno(poligono, passo)
    pontos = np.array(contorno)
    delaunay = Delaunay(pontos)
    mascara = prep(poligono)
    triangulos = []
    for simplex in delaunay.simplices:
        centroide = pontos[simplex].mean(axis=0)
        if mascara.contains(Point(centroide)):
            triangulos.append(simplex)
    return pontos, np.array(triangulos)


def construir_solido(poligono, espessura: float, drapear):
    pontos_xy, triangulos_topo = triangular_interior(poligono, PASSO_DENSIFICACAO)
    n = len(pontos_xy)

    z_topo = np.array([drapear(x, y) for x, y in pontos_xy])
    vertices_topo = np.column_stack([pontos_xy, z_topo])
    vertices_base = np.column_stack([pontos_xy, z_topo - espessura])
    vertices = np.vstack([vertices_topo, vertices_base])

    faces = list(triangulos_topo)  # topo (indices 0..n-1)
    faces += [(f[0] + n, f[2] + n, f[1] + n) for f in triangulos_topo]  # base, invertida (normal pra baixo)

    # paredes laterais: pontos_xy sao exatamente o anel externo, em ordem
    # (veio direto de densificar_contorno), entao range(n) ja percorre o anel
    for i in range(n):
        a, b = i, (i + 1) % n
        faces.append((a, b, b + n))
        faces.append((a, b + n, a + n))

    return vertices, np.array(faces)


def exportar_obj(vertices, faces, destino: Path):
    with open(destino, "w") as f:
        f.write(f"# {destino.stem} - solido de visualizacao (contorno digitalizado + espessura de campo)\n")
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in faces:
            f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")


def main():
    if not POLIGONO_REFERENCIA.exists():
        print(f"Nao encontrado: {POLIGONO_REFERENCIA}")
        return

    gdf = gpd.read_file(POLIGONO_REFERENCIA)
    drapear = montar_interpolador_topografia()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for tipo, (nome_saida, espessura) in CONFIG.items():
        subset = gdf[gdf["tipo"] == tipo]
        if not len(subset):
            continue
        print(f"{tipo}: {len(subset)} poligono(s), espessura {espessura}m")

        todos_v, todos_f = [], []
        offset = 0
        for _, row in subset.iterrows():
            poligono = row.geometry
            partes = poligono.geoms if poligono.geom_type == "MultiPolygon" else [poligono]
            for parte in partes:
                v, f = construir_solido(parte, espessura, drapear)
                todos_v.append(v)
                todos_f.append(f + offset)
                offset += len(v)

        vertices = np.vstack(todos_v)
        faces = np.vstack(todos_f)
        destino = EXPORTS_DIR / f"{nome_saida}.obj"
        exportar_obj(vertices, faces, destino)
        print(f"  -> {destino} ({len(vertices)} vertices, {len(faces)} faces)")

    print("\nPronto. Importa junto com os outros .obj no Blender (mesma pasta exports/meshes/).")


if __name__ == "__main__":
    main()
