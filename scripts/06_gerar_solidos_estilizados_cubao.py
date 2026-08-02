"""
Gera uma segunda versao dos solidos de sill/dique, so pra composicao do
"cubao" (visualizacao publico/estilizada, ver blender/visualizacao_publico/)
-- NAO tem apego cientifico, diferente de 05_gerar_solidos_visualizacao.py
(que usa espessura real medida em campo).

- sill_diabasio: espessura fixa e exagerada (ESPESSURA_SILL_ESTILIZADA),
  bem maior que a real (~27m), pra dar a sensacao de "profundidade" no
  cubo sem tentar ser preciso.
- dique: em vez de espessura fixa, o fundo vai ate BASE_Z_ABSOLUTA (a
  mesma cota usada como piso do cubao nos scripts de visualizacao) --
  fica "inteirico" atravessando o bloco todo, representando o conduto
  que corta toda a sequencia.

Reusa a mesma logica de triangulacao/extrusao de
05_gerar_solidos_visualizacao.py (poligono -> topo drapeado na topografia
+ paredes), so muda como a base e calculada.

Saida: exports/meshes/sill_diabasio_estilizado.obj, dique_estilizado.obj

Uso:
    python scripts/06_gerar_solidos_estilizados_cubao.py
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

# mesma cota (metros, elevacao real) usada como piso do "cubao" nos
# visualizadores -- se mudar aqui, mudar tambem em viewer_3d.py (PROFUNDIDADE_CAIXA
# soma em cima do Z minimo, entao ajuste os dois pra baterem) e no script bpy do Blender.
# piso do "cubao" -- rebaixado pra caber a espessura real das 5 formacoes
# (Rio Bonito+Palermo+Irati+Serra Alta+Teresina ~854m, ver
# visualizacao_web/gerar_visualizador_3d.py) com folga
BASE_Z_ABSOLUTA = -600.0

# 4 camadas sedimentares planas/paralelas (simplificacao estilizada, "por
# hora" -- substitui as 5 formacoes reais da CPRM que ficaram poluidas
# visualmente no cubo). Cotas em metros, mesma escala real do resto.
# Estas mesmas cotas sao usadas nos scripts de visualizacao (Blender/Plotly)
# pra desenhar as 4 fatias -- mude aqui e la se ajustar.
LIMITES_CAMADAS = [0.0, 250.0, 500.0, 750.0, 1000.0]  # base -> topo, 4 faixas, preenche o bloco inteiro

# sill de volta a posicao real (drapeado na topografia, nao mais achatado
# numa cota fixa -- a versao "concordante plana" desceu demais e ficou
# artificial). Espessura ainda exagerada (bem mais que os ~27m reais) so
# pra dar volume visivel.
ESPESSURA_SILL_ESTILIZADA = 400.0

PASSO_DENSIFICACAO = 40.0


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


def construir_solido(poligono, drapear, espessura=None, base_z_absoluto=None, topo_fixo=None):
    """Base: `espessura` (topo - espessura) OU `base_z_absoluto` (cota fixa
    pra todo mundo). Topo: drapeado na topografia real, OU `topo_fixo`
    (plano/concordante, pra sill "passando" entre camadas planas)."""
    assert (espessura is None) != (base_z_absoluto is None), "passe espessura OU base_z_absoluto, nao os dois"

    pontos_xy, triangulos_topo = triangular_interior(poligono, PASSO_DENSIFICACAO)
    n = len(pontos_xy)

    if topo_fixo is not None:
        z_topo = np.full(n, topo_fixo)
    else:
        z_topo = np.array([drapear(x, y) for x, y in pontos_xy])
    z_base = z_topo - espessura if espessura is not None else np.full(n, base_z_absoluto)

    vertices_topo = np.column_stack([pontos_xy, z_topo])
    vertices_base = np.column_stack([pontos_xy, z_base])
    vertices = np.vstack([vertices_topo, vertices_base])

    faces = list(triangulos_topo)
    faces += [(f[0] + n, f[2] + n, f[1] + n) for f in triangulos_topo]

    for i in range(n):
        a, b = i, (i + 1) % n
        faces.append((a, b, b + n))
        faces.append((a, b + n, a + n))

    return vertices, np.array(faces)


def exportar_obj(vertices, faces, destino: Path):
    with open(destino, "w") as f:
        f.write(f"# {destino.stem} - solido estilizado (cubao, sem apego cientifico)\n")
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in faces:
            f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")


def gerar(tipo: str, nome_saida: str, drapear, gdf, **kwargs):
    subset = gdf[gdf["tipo"] == tipo]
    if not len(subset):
        return
    todos_v, todos_f = [], []
    offset = 0
    for _, row in subset.iterrows():
        poligono = row.geometry
        partes = poligono.geoms if poligono.geom_type == "MultiPolygon" else [poligono]
        for parte in partes:
            v, f = construir_solido(parte, drapear, **kwargs)
            todos_v.append(v)
            todos_f.append(f + offset)
            offset += len(v)
    vertices = np.vstack(todos_v)
    faces = np.vstack(todos_f)
    destino = EXPORTS_DIR / f"{nome_saida}.obj"
    exportar_obj(vertices, faces, destino)
    print(f"  -> {destino} ({len(vertices)} vertices, {len(faces)} faces)")


def main():
    if not POLIGONO_REFERENCIA.exists():
        print(f"Nao encontrado: {POLIGONO_REFERENCIA}")
        return

    gdf = gpd.read_file(POLIGONO_REFERENCIA)
    drapear = montar_interpolador_topografia()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"sill_diabasio: posicao real (drapeado na topografia), espessura {ESPESSURA_SILL_ESTILIZADA}m")
    gerar("Soleira", "sill_diabasio_estilizado", drapear, gdf, espessura=ESPESSURA_SILL_ESTILIZADA)

    print(f"dique: inteirico ate a cota {BASE_Z_ABSOLUTA}m (piso do cubao)")
    gerar("Dique", "dique_estilizado", drapear, gdf, base_z_absoluto=BASE_Z_ABSOLUTA)

    print("\nPronto.")


if __name__ == "__main__":
    main()
