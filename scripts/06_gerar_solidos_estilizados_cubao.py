"""
Gera uma segunda versao dos solidos de sill/dique, so pra composicao do
"cubao" (visualizacao publico/estilizada, ver blender/visualizacao_publico/)
-- NAO tem apego cientifico, diferente de 05_gerar_solidos_visualizacao.py
(que usa espessura real medida em campo).

- sill_diabasio: base = topo real da formacao Serra Alta (mesmo plano de
  mergulho regional + erosao usado nos visualizadores cientificos), com
  piso minimo de ESPESSURA_MINIMA_SILL (~27m, mediana de campo) onde a
  Serra Alta fica rasa demais perto de onde o sill aflora.
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
# artificial).
ESPESSURA_SILL_ESTILIZADA = 400.0  # OBSOLETO (10/08/2026) -- ver elevacao_serra_alta/
# ESPESSURA_MINIMA_SILL abaixo; a base do sill deixou de ser um offset fixo.

PASSO_DENSIFICACAO = 40.0

# base REAL do sill = topo da formacao Serra Alta, nao mais um offset fixo
# exagerado -- mesmo plano de mergulho regional + erosao contra a topografia
# ja usado nos visualizadores cientificos (ver TREND_A/TREND_B/Z_REF_TILT em
# visualizacao_web/gerar_visualizador_3d.py e gerar_secao_interativa.py;
# as 4 faixas de encaixante deste script (LIMITES_CAMADAS) continuam
# simplificadas/planas, sem relacao com isso -- so o sill fica mais fiel).
TREND_A, TREND_B = 0.01034, -0.00025
TREND_X0, TREND_Y0 = 592300.0, 7015058.8
Z_REF_TILT = 1053.5
PROFUNDIDADE_SERRA_ALTA = 350.0
ESPESSURA_MINIMA_SILL = 27.0  # mediana real medida em campo -- piso pra nao afinar
# demais/inverter onde a Serra Alta fica rasa perto de onde o sill aflora.


def elevacao_serra_alta(x, y, drapear):
    plano = Z_REF_TILT + TREND_A * (x - TREND_X0) + TREND_B * (y - TREND_Y0) - PROFUNDIDADE_SERRA_ALTA
    return min(plano, drapear(x, y))


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


def construir_solido(poligono, drapear, espessura=None, base_z_absoluto=None, topo_fixo=None,
                      base_fn=None, espessura_minima=None):
    """Base: `espessura` (topo - espessura) OU `base_z_absoluto` (cota fixa
    pra todo mundo) OU `base_fn(x,y)` (base geologica, ver elevacao_serra_alta
    -- usa o minimo entre base_fn e topo-espessura_minima, pra nao afinar
    demais/inverter onde a base geologica fica rasa). Topo: drapeado na
    topografia real, OU `topo_fixo` (plano/concordante, pra sill "passando"
    entre camadas planas)."""
    assert sum(x is not None for x in (espessura, base_z_absoluto, base_fn)) == 1, \
        "passe exatamente um de: espessura, base_z_absoluto, base_fn"

    pontos_xy, triangulos_topo = triangular_interior(poligono, PASSO_DENSIFICACAO)
    n = len(pontos_xy)

    if topo_fixo is not None:
        z_topo = np.full(n, topo_fixo)
    else:
        z_topo = np.array([drapear(x, y) for x, y in pontos_xy])

    if base_fn is not None:
        z_geologica = np.array([base_fn(x, y) for x, y in pontos_xy])
        piso_minimo = z_topo - (espessura_minima or 0.0)
        z_base = np.minimum(z_geologica, piso_minimo)
    elif espessura is not None:
        z_base = z_topo - espessura
    else:
        z_base = np.full(n, base_z_absoluto)

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

    print("sill_diabasio: posicao real (drapeado na topografia), base = topo da Serra Alta")
    gerar("Soleira", "sill_diabasio_estilizado", drapear, gdf,
          base_fn=lambda x, y: elevacao_serra_alta(x, y, drapear), espessura_minima=ESPESSURA_MINIMA_SILL)

    print(f"dique: inteirico ate a cota {BASE_Z_ABSOLUTA}m (piso do cubao)")
    gerar("Dique", "dique_estilizado", drapear, gdf, base_z_absoluto=BASE_Z_ABSOLUTA)

    print("\nPronto.")


if __name__ == "__main__":
    main()
