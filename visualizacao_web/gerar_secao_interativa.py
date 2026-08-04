"""Visualizador 2D interativo (Plotly, HTML autonomo) da secao transversal
estilizada -- mapa em planta do lado (clicavel -- clique escolhe a posicao
da linha de corte) e a secao transversal do lado, sincronizados via
slider/frames. A linha de corte pode ser rotacionada (botoes: horizontal,
vertical, 2 diagonais) -- pra cada angulo, o slider desliza a linha
perpendicularmente cobrindo toda a extensao do modelo. Mesma paleta/dados
estilizados do cubao 3D (gerar_visualizador_3d.py) e da secao estatica em
../scripts/07_gerar_secao_transversal.py.

Uso:
    python visualizacao_web/gerar_secao_interativa.py

Gera:
    visualizacao_web/secao_interativa.html
"""
import base64
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import rasterio.features
from affine import Affine
from plotly.subplots import make_subplots
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator, griddata
from shapely.geometry import LineString, Point, shape as shapely_shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

BASE = Path(r"C:\Users\thuba\Desktop\Mestrado\1_Modelo_3D_Taio")
TOPO_NPY = BASE / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
POLIGONO_REFERENCIA = BASE.parent / "2_Banco_de_Dados" / "dados_base" / "poligon_intrusiva.shp"
POLIGONOS_CPRM_GEOJSON = BASE.parent / "2_Banco_de_Dados" / "saida_processada" / "formacoes_cprm_poligonos.geojson"
OSM_RIOS_GEOJSON = BASE.parent / "2_Banco_de_Dados" / "saida_processada" / "osm_rios.geojson"
OSM_ESTRADAS_GEOJSON = BASE.parent / "2_Banco_de_Dados" / "saida_processada" / "osm_estradas.geojson"
OSM_LUGARES_GEOJSON = BASE.parent / "2_Banco_de_Dados" / "saida_processada" / "osm_lugares.geojson"
PONTOS_CAMPO_GPKG = (
    BASE.parent / "2_Banco_de_Dados" / "Unificação" / "GPKG_Novos" / "pontos_unificados_completo.gpkg"
)
PONTOS_ESTRUTURAIS_GPKG = (
    BASE.parent / "2_Banco_de_Dados" / "Unificação" / "GPKG_Novos" / "nuvem_pontos_direcoes.gpkg"
)
LOGO_PATH = Path(__file__).parent / "assets" / "logo_gstech.jpg"
OUT_HTML = Path(__file__).parent / "secao_interativa.html"

# identidade visual GS Tech (marca do usuario, aplicada por cima do produto --
# nao mexe em nada do modelo/dados). Mesma paleta de
# ../visualizacao_web/gerar_visualizador_3d.py, manter as duas em sincronia.
MARCA_ROXO_ESCURO = "#2D0A4A"
MARCA_ROXO = "#7B2FFF"
MARCA_AZUL = "#2E6F95"
MARCA_NAVY = "#1B1F2E"
MARCA_CINZA_CLARO = "#F2F2F2"
MARCA_FONTE = "Montserrat, Arial, sans-serif"


def logo_base64():
    if not LOGO_PATH.exists():
        return None
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")

X_MIN, X_MAX = 582500.0, 604500.0
Y_MIN, Y_MAX = 6995000.0, 7029000.0
CX, CY = (X_MIN + X_MAX) / 2, (Y_MIN + Y_MAX) / 2

# angulos de corte disponiveis (graus, 0 = leste, sentido anti-horario --
# mesma convencao de vetor direcao (cos,sin)). Um botao por angulo; o
# slider desliza a linha perpendicularmente a ela, cobrindo a extensao real
# do modelo (calculado abaixo via projecao dos 4 cantos do bbox).
ANGULOS = [
    ("Horizontal (O↔L)", 0.0),
    ("Diagonal (SO↔NE)", 45.0),
    ("Vertical (S↔N)", 90.0),
    ("Diagonal (SE↔NO)", 135.0),
]
PASSO_POSICAO = 1000.0  # espacamento fixo (m) entre posicoes do slider -- cobre o mapa todo
N_AMOSTRAS = 300
RESOLUCAO_MAPA = 150

# 5 formacoes sedimentares REAIS (Bacia do Parana, Grupo Guata/Passa Dois),
# mais nova (topo) -> mais antiga (base). Espessuras da literatura (busca em
# 01/08/2026): Rio Bonito ate 269m (poco 1-BN-1-SC), Palermo ~100m
# (ESTIMATIVA -- nao confirmada), Irati 40-70m (uso 55m), Serra Alta 52-100m
# na borda leste (uso 80m), Teresina 300-400m na borda leste (uso 350m).
# Mesmos valores/cores de ../visualizacao_web/gerar_visualizador_3d.py.
NOMES_CAMADAS = ["Teresina", "Serra Alta", "Irati", "Palermo", "Rio Bonito"]
CORES_CAMADAS = ["#D6C79A", "#8C8C86", "#3E362C", "#B5AE93", "#C9A66B"]
PROFUNDIDADE_CAMADAS = [0.0, 350.0, 430.0, 485.0, 585.0, 854.0]

# trend regional: plano bruto do contato real Teresina/Serra Alta (CPRM,
# n=627) -- ver ../../2_Banco_de_Dados/scripts_etl/calcular_trend_regional_camadas.py
# e o comentario equivalente em gerar_visualizador_3d.py.
TREND_A, TREND_B = 0.01034, -0.00025
TREND_X0, TREND_Y0 = 592300.0, 7015058.8
Z_REF_TILT = 1053.5  # ancora o plano em boundary(prof=350) = 703.5 (media real do contato Teresina/Serra Alta)
COR_SILL = "#A63D2F"
COR_DIQUE = "#1B4332"  # verde escuro
COR_QUATERNARIO = "#D9CB82"
# pontos de campo (catalogo unificado, ver PONTOS_CAMPO_GPKG) -- mesma paleta
# das formacoes/sill/dique quando a litologia bate, cinza neutro pro resto.
CORES_LITOLOGIA_CAMPO = {
    "sill_diabasio": COR_SILL, "sill_diabasio_cprm": COR_SILL,
    "dique": COR_DIQUE, "dique_cprm": COR_DIQUE,
    "encaixante_teresina": CORES_CAMADAS[0], "encaixante_serra_alta": CORES_CAMADAS[1],
    "encaixante_irati": CORES_CAMADAS[2], "encaixante_palermo": CORES_CAMADAS[3],
    "encaixante_rio_bonito": CORES_CAMADAS[4],
}
COR_LITOLOGIA_PADRAO = "#999999"
# dados estruturais (fraturas/falhas/diques inferidos/acamamento etc., ver
# PONTOS_ESTRUTURAIS_GPKG) -- cor por classificacao, cobre todas as categorias
# do catalogo (nao so fratura_falha, que foi so o pedido inicial do usuario).
CORES_CLASSIFICACAO_ESTRUTURAL = {
    "acamamento_sedimentar": "#C9A66B",
    "fratura_falha": "#D64545",
    "dique_provavel_relevo_positivo": "#2E7D5B",
    "dique_confirmado_mapa": COR_DIQUE,
    "falha_ou_dique_ambiguo_relevo_negativo": "#E8A33D",
    "contato_sill_encaixante": "#A63D2F",
    "fabrica_interna_intrusao": "#7B2FFF",
}
COR_CLASSIFICACAO_PADRAO = "#999999"
ESPESSURA_SILL = 400.0
QUATERNARIO_LIMIAR = 450.0
QUATERNARIO_ESPESSURA = 30.0
BASE_Z_ABSOLUTA = -600.0  # piso do "cubao" -- rebaixado pra caber a espessura real das 5 formacoes

CORES_HIPSOMETRICAS = ["#A66A2C", "#C6924A", "#D8C88C", "#9FC1A3", "#4F9AA8"]
COLORSCALE_HIPSOMETRICO = [[i / (len(CORES_HIPSOMETRICAS) - 1), cor] for i, cor in enumerate(CORES_HIPSOMETRICAS)]

# mapa geologico real (CPRM) como alternativa a hipsometria no mapa em planta
# -- mesmos poligonos/paleta de ../visualizacao_web/gerar_visualizador_3d.py
# (gerados por ../../2_Banco_de_Dados/scripts_etl/exportar_poligonos_cprm.py).
# Aqui e so contorno 2D (fill="toself" do Scatter), sem drapeado/triangulacao
# -- o mapa em planta nao tem relevo 3D pra seguir.
ORDEM_FORMACOES = NOMES_CAMADAS + [
    "Serra Geral (sill/dique)", "Aluvião quaternário", "K_TPS_SILL", "K_TPS_DIQUE", "Outros",
]
CORES_FORMACOES = CORES_CAMADAS + ["#A63D2F", "#D9CB82", COR_SILL, COR_DIQUE, "#CCCCCC"]
CORES_FORMACOES_MAPA = dict(zip(ORDEM_FORMACOES, CORES_FORMACOES))


def montar_elevador():
    xyz = np.load(TOPO_NPY)
    linear = LinearNDInterpolator(xyz[:, :2], xyz[:, 2])
    nearest = NearestNDInterpolator(xyz[:, :2], xyz[:, 2])

    def elevacao(x, y):
        z = linear(x, y)
        if np.isnan(z):
            z = nearest(x, y)
        return float(z)

    return elevacao, xyz


def faixas_contiguas(mask):
    """Lista de (i0,i1) pra cada trecho CONTIGUO de True em mask -- um corpo
    (sill/dique/quaternario) pode cruzar a linha em varios pontos separados
    (16 diques hoje, nao mais so 2), entao nao da pra so pegar do primeiro
    ao ultimo True (isso conectava pontos bem distantes com um bloco solido
    gigante e falso preenchendo os vazios no meio -- bug real, achado
    testando a secao com o dado atualizado)."""
    faixas = []
    inicio = None
    for i, v in enumerate(mask):
        if v and inicio is None:
            inicio = i
        elif not v and inicio is not None:
            faixas.append((inicio, i))
            inicio = None
    if inicio is not None:
        faixas.append((inicio, len(mask)))
    return faixas


def banda_toself(dists, topo, base, mask=None):
    if mask is not None:
        faixas = faixas_contiguas(mask)
        if not faixas:
            return np.array([np.nan]), np.array([np.nan])
        xs, ys = [], []
        for k, (i0, i1) in enumerate(faixas):
            if k > 0:
                xs.append(np.nan)
                ys.append(np.nan)
            d, t, b = dists[i0:i1], topo[i0:i1], base[i0:i1]
            xs.extend(np.concatenate([d, d[::-1]]))
            ys.extend(np.concatenate([t, b[::-1]]))
        return np.array(xs), np.array(ys)
    x = np.concatenate([dists, dists[::-1]])
    y = np.concatenate([topo, base[::-1]])
    return x, y


def linhas_para_scatter_xy(gdf):
    """Todas as linhas (rios/estradas) de um GeoDataFrame como um unico par
    x,y pra um Scatter mode='lines' -- cada trecho separado por NaN (mesma
    logica de sub-caminhos separados usada em poligono_para_scatter_xy/
    faixas_contiguas). Um trace so, em vez de um por feature, pra nao
    multiplicar o numero de traces (rios sozinho tem quase 6 mil trechos)."""
    xs, ys = [], []
    primeiro = True
    for geom in gdf.geometry:
        partes = geom.geoms if hasattr(geom, "geoms") else [geom]
        for parte in partes:
            if not primeiro:
                xs.append(np.nan)
                ys.append(np.nan)
            primeiro = False
            coords = np.array(parte.coords)
            xs.extend(coords[:, 0])
            ys.extend(coords[:, 1])
    return np.array(xs), np.array(ys)


def poligono_para_scatter_xy(geom):
    """Contorno de um poligono/multipoligono (COM buracos) como x,y pra um
    Scatter com fill='toself' -- cada anel (exterior + buracos) vira um
    sub-caminho separado por NaN. Os buracos so viram buraco de verdade se
    o anel externo e os internos girarem em sentidos opostos (regra
    "nonzero" do preenchimento do Plotly) -- por isso usa shapely.orient()
    pra forcar essa convencao, independente de como veio no shapefile.
    Sem isso, formacoes com buraco (ex.: Teresina/Serra Alta/Rio Bonito, que
    tem sill/dique "por dentro") ficavam com o buraco preenchido solido,
    cobrindo o que devia aparecer por baixo."""
    partes = geom.geoms if hasattr(geom, "geoms") else [geom]
    xs, ys = [], []
    primeiro = True
    for parte in partes:
        parte = orient(parte, sign=1.0)
        for anel in [parte.exterior] + list(parte.interiors):
            if not primeiro:
                xs.append(np.nan)
                ys.append(np.nan)
            primeiro = False
            coords = np.array(anel.coords)
            xs.extend(coords[:, 0])
            ys.extend(coords[:, 1])
    return np.array(xs), np.array(ys)


def poligono_quaternario_mapa(mx, my, mz):
    """Poligoniza a mascara do deposito quaternario (mesmo limiar/fonte real
    da secao -- QUATERNARIO_LIMIAR sobre a topografia real) na resolucao da
    grade do mapa (mx,my,mz), pra desenhar no mapa em planta junto com o
    resto do mapa geologico (a CPRM/litologia nao mapeia aluviao dentro
    dessa extensao -- fica de fora do geojson -- entao usa a mesma logica
    ja usada na secao, nao um dado novo)."""
    mask = (mz <= QUATERNARIO_LIMIAR)
    if not mask.any():
        return None
    n_y, n_x = mask.shape
    dx = (X_MAX - X_MIN) / (n_x - 1)
    dy = (Y_MAX - Y_MIN) / (n_y - 1)
    transform = Affine.translation(X_MIN - dx / 2, Y_MIN - dy / 2) * Affine.scale(dx, dy)
    formas = rasterio.features.shapes(mask.astype(np.uint8), mask=mask, transform=transform)
    poligonos = [shapely_shape(geom) for geom, valor in formas if valor == 1]
    if not poligonos:
        return None
    return unary_union(poligonos)


def cobertura_bbox(vx, vy, cx, cy, fator=1.0):
    """Projeta os 4 cantos do bbox do modelo no vetor (vx,vy) -- da o
    intervalo [min,max] que cobre a extensao inteira nessa direcao,
    qualquer que seja o angulo. fator<1 encolhe o intervalo em torno do
    centro (usado no deslocamento perpendicular -- as pontas do bbox
    projetado ficam com so uma lasca de terreno, pouco uteis no slider)."""
    cantos = [(X_MIN, Y_MIN), (X_MIN, Y_MAX), (X_MAX, Y_MIN), (X_MAX, Y_MAX)]
    projs = [(x - cx) * vx + (y - cy) * vy for x, y in cantos]
    lo, hi = min(projs), max(projs)
    if fator != 1.0:
        centro, meia = (lo + hi) / 2, (hi - lo) / 2 * fator
        lo, hi = centro - meia, centro + meia
    return lo, hi


def amostrar_linha(cx_linha, cy_linha, dx, dy, s_vals, elevacao, sill_geom, dique_geom):
    xs = cx_linha + s_vals * dx
    ys = cy_linha + s_vals * dy
    dists = (s_vals - s_vals[0]) / 1000
    terreno = np.array([elevacao(x, y) for x, y in zip(xs, ys)])
    dentro_sill = np.array([sill_geom.contains(Point(x, y)) for x, y in zip(xs, ys)])
    dentro_dique = np.array([dique_geom.contains(Point(x, y)) for x, y in zip(xs, ys)])

    # contato 0 = sempre o relevo real (Teresina afloraria sempre no seu
    # lugar); contatos > 0 sao planos inclinados, erodidos pelo relevo real
    # onde ficam acima dele (ver comentario equivalente em gerar_visualizador_3d.py).
    tilt = Z_REF_TILT + TREND_A * (xs - TREND_X0) + TREND_B * (ys - TREND_Y0)
    contatos = [terreno if m == 0 else np.minimum(tilt - PROFUNDIDADE_CAMADAS[m], terreno)
                for m in range(len(PROFUNDIDADE_CAMADAS))]

    dados = {}
    espessuras = []
    for k in range(len(PROFUNDIDADE_CAMADAS) - 1):
        dados[f"camada{k}"] = banda_toself(dists, contatos[k], contatos[k + 1])
        espessuras.append(float(np.mean(contatos[k] - contatos[k + 1])))  # media ao longo da linha (m)
    dados["espessuras"] = espessuras

    dados["quaternario"] = banda_toself(dists, terreno, terreno - QUATERNARIO_ESPESSURA, terreno <= QUATERNARIO_LIMIAR)
    dados["sill"] = banda_toself(dists, terreno, terreno - ESPESSURA_SILL, dentro_sill)
    dados["dique"] = banda_toself(dists, terreno, np.full_like(terreno, BASE_Z_ABSOLUTA), dentro_dique)
    dados["terreno"] = (dists, terreno)
    dados["linha_mapa"] = (np.array([xs[0], xs[-1]]), np.array([ys[0], ys[-1]]))
    return dados


def calcular_cruzamentos(xs, ys, gdf, sindex, elevacao):
    """Pontos onde a linha de corte atual (xs,ys, ja amostrada) cruza as
    features de um GeoDataFrame (rios ou estradas) -- usa o indice espacial
    (sindex) pra so testar intersecao real contra os poucos candidatos perto
    da linha, nao contra todas as milhares de features. Devolve lista de
    (distancia_km_no_perfil, elevacao_real, nome) -- so cruzamentos com nome
    real no OSM (sem nome vira pin demais, poluia o grafico -- usuario testou
    "todos" e pediu pra voltar a so nomeados)."""
    linha = LineString(zip(xs, ys))
    candidatos = list(sindex.query(linha))
    vistos = set()
    cruzamentos = []
    for i in candidatos:
        geom = gdf.geometry.iloc[i]
        inter = linha.intersection(geom)
        if inter.is_empty:
            continue
        pontos = list(inter.geoms) if hasattr(inter, "geoms") else [inter]
        for pt in pontos:
            if pt.geom_type != "Point":
                continue
            # posicao ao longo do perfil: projeta o ponto de intersecao no
            # mesmo parametro usado pra "dists" (distancia real desde xs[0]/ys[0])
            s = math.hypot(pt.x - xs[0], pt.y - ys[0])
            s_km = s / 1000
            nome = gdf["name"].iloc[i] if "name" in gdf.columns else None
            if not (isinstance(nome, str) and nome.strip()):
                continue  # so cruzamentos com nome -- sem nome ficava poluido demais (todo trecho vira pin)
            chave = (round(s_km, 2), nome)
            if chave in vistos:
                continue
            vistos.add(chave)
            cruzamentos.append((s_km, float(elevacao(pt.x, pt.y)), nome))
    cruzamentos.sort(key=lambda c: c[0])

    # funde cruzamentos consecutivos do MESMO rio/estrada que caem muito perto
    # um do outro -- um curso d'agua sinuoso pode cruzar a linha reta varias
    # vezes numa curva fechada (poucas centenas de metros), o que duplicava o
    # mesmo nome empilhado/ilegivel no grafico (bug reportado pelo usuario).
    # So a distancia importa aqui, nao a elevacao (fica igual/parecida mesmo).
    LIMIAR_FUSAO_KM = 0.5
    fundidos = []
    for c in cruzamentos:
        if fundidos and fundidos[-1][2] == c[2] and (c[0] - fundidos[-1][0]) < LIMIAR_FUSAO_KM:
            continue  # mesmo nome, perto do anterior -- mantem so a primeira ocorrencia
        fundidos.append(c)
    return fundidos


_CHAVES_CAMADAS = [f"camada{k}" for k in range(len(PROFUNDIDADE_CAMADAS) - 1)]
ORDEM_TRACES = ["linha_mapa"] + _CHAVES_CAMADAS + ["quaternario", "sill", "dique", "terreno"]
CORES_TRACES = {chave: CORES_CAMADAS[k] for k, chave in enumerate(_CHAVES_CAMADAS)}
CORES_TRACES.update({"quaternario": COR_QUATERNARIO, "sill": COR_SILL, "dique": COR_DIQUE})
NOMES_TRACES = {chave: NOMES_CAMADAS[k] for k, chave in enumerate(_CHAVES_CAMADAS)}
NOMES_TRACES.update({
    "quaternario": "Depósito quaternário", "sill": "Soleira", "dique": "Dique",
})
# ordem estratigrafica da legenda, igual ao 3D (gerar_visualizador_3d.py): deposito
# quaternario, depois sill/dique, depois as 5 formacoes sedimentares reais.
# ordem da legenda: ponto (localidades) -> linha (rios/estradas) -> poligono
# (deposito/soleira/dique/formacoes), ranks 1-3 reservados pros dois primeiros
# grupos (ver LEGENDRANK_OSM mais abaixo).
LEGENDRANK_TRACES = {"quaternario": 4, "sill": 5, "dique": 6}
LEGENDRANK_TRACES.update({chave: 7 + k for k, chave in enumerate(_CHAVES_CAMADAS)})
LEGENDRANK_OSM = {"lugares": 1, "rios": 2, "estradas": 3}


def main():
    elevacao, xyz = montar_elevador()
    gdf = gpd.read_file(POLIGONO_REFERENCIA)
    sill_geom = gdf[gdf["tipo"] == "Soleira"].geometry.union_all()
    dique_geom = gdf[gdf["tipo"] == "Dique"].geometry.union_all()

    print("Montando mapa em planta...")
    mx, my = np.meshgrid(np.linspace(X_MIN, X_MAX, RESOLUCAO_MAPA), np.linspace(Y_MIN, Y_MAX, RESOLUCAO_MAPA))
    mz = griddata(xyz[:, :2], xyz[:, 2], (mx, my), method="linear")
    mz_nearest = griddata(xyz[:, :2], xyz[:, 2], (mx, my), method="nearest")
    mz = np.where(np.isnan(mz), mz_nearest, mz)

    angulos_info = []
    for nome, theta_deg in ANGULOS:
        rad = np.radians(theta_deg)
        dx, dy = np.cos(rad), np.sin(rad)
        px, py = -np.sin(rad), np.cos(rad)
        s_min, s_max = cobertura_bbox(dx, dy, CX, CY)
        t_min, t_max = cobertura_bbox(px, py, CX, CY)
        n_pos = int(np.floor((t_max - t_min) / PASSO_POSICAO)) + 1
        t_vals = t_min + np.arange(n_pos) * PASSO_POSICAO
        if t_vals[-1] < t_max:
            t_vals = np.append(t_vals, t_max)  # ultimo passo (pode ser < 1000m) pra cobrir ate a borda
        angulos_info.append(dict(
            nome=nome, dx=dx, dy=dy, px=px, py=py,
            s_vals=np.linspace(s_min, s_max, N_AMOSTRAS),
            t_vals=t_vals,
        ))

    gdf_rios_cx = gpd.read_file(OSM_RIOS_GEOJSON) if OSM_RIOS_GEOJSON.exists() else None
    gdf_estradas_cx = gpd.read_file(OSM_ESTRADAS_GEOJSON) if OSM_ESTRADAS_GEOJSON.exists() else None

    print(f"Pre-calculando {len(ANGULOS)} angulos, passo de {PASSO_POSICAO:.0f}m...")
    todas_secoes = []
    todas_pins_rios = []
    todas_pins_estradas = []
    for info in angulos_info:
        secoes_angulo = []
        pins_rios_angulo = []
        pins_estradas_angulo = []
        for t in info["t_vals"]:
            cx_linha, cy_linha = CX + t * info["px"], CY + t * info["py"]
            secao = amostrar_linha(cx_linha, cy_linha, info["dx"], info["dy"], info["s_vals"],
                                    elevacao, sill_geom, dique_geom)
            secoes_angulo.append(secao)
            xs_linha = cx_linha + info["s_vals"] * info["dx"]
            ys_linha = cy_linha + info["s_vals"] * info["dy"]
            if gdf_rios_cx is not None:
                pins_rios_angulo.append(calcular_cruzamentos(xs_linha, ys_linha, gdf_rios_cx, gdf_rios_cx.sindex, elevacao))
            else:
                pins_rios_angulo.append([])
            if gdf_estradas_cx is not None:
                pins_estradas_angulo.append(calcular_cruzamentos(xs_linha, ys_linha, gdf_estradas_cx, gdf_estradas_cx.sindex, elevacao))
            else:
                pins_estradas_angulo.append([])
        todas_secoes.append(secoes_angulo)
        todas_pins_rios.append(pins_rios_angulo)
        todas_pins_estradas.append(pins_estradas_angulo)

    n_pos_inicial = len(angulos_info[0]["t_vals"])
    inicial = todas_secoes[0][n_pos_inicial // 2]

    fig = make_subplots(
        rows=2, cols=2, column_widths=[0.22, 0.78], row_heights=[0.76, 0.24],
        horizontal_spacing=0.06, vertical_spacing=0.14,
        specs=[[{}, {}], [{"colspan": 2}, None]],
        subplot_titles=("Mapa (clique p/ mover)", "Seção transversal", "Espessura das formações na linha atual"),
    )
    for ann in fig.layout.annotations:  # titulos dos subplots -- estiliza pra tema escuro antes de adicionar o resto
        ann.font = dict(color=MARCA_CINZA_CLARO, size=14, family=MARCA_FONTE)

    fig.add_trace(go.Heatmap(
        x=mx[0, :], y=my[:, 0], z=mz, colorscale=COLORSCALE_HIPSOMETRICO,
        showscale=False, hoverinfo="none",  # "skip" tambem exclui o trace do hit-test de clique
    ), row=1, col=1)

    # poligonos do mapa geologico real (CPRM) no mapa em planta -- logo
    # depois do heatmap (nao depois da linha do perfil!), senao desenham por
    # cima da linha tracejada e escondem ela. Comecam invisiveis (modo
    # padrao = hipsometria). So estatico, nao muda com o corte -- o mapa em
    # planta mostra a area inteira sempre.
    idx_geo_mapa_inicio = 1
    gdf_formacoes = gpd.read_file(POLIGONOS_CPRM_GEOJSON)
    print(f"Mapa geologico real: {len(gdf_formacoes)} formacoes")
    for row in gdf_formacoes.itertuples():
        gx, gy = poligono_para_scatter_xy(row.geometry)
        fig.add_trace(go.Scatter(
            x=gx, y=gy, mode="lines", line=dict(width=0), fill="toself",
            fillcolor=CORES_FORMACOES_MAPA.get(row.formacao, "#CCCCCC"),
            name=row.formacao, showlegend=False, visible=False, hoverinfo="none",
        ), row=1, col=1)

    # deposito quaternario tambem no mapa em planta -- a litologia CPRM nao
    # mapeia aluviao dentro dessa extensao (fica de fora do geojson), entao
    # poligoniza a MESMA mascara/limiar real ja usada na secao (nao e um
    # dado novo, so o mesmo proxy representado como poligono).
    poli_quat = poligono_quaternario_mapa(mx, my, mz)
    n_geo_mapa = len(gdf_formacoes) + (1 if poli_quat is not None else 0)
    if poli_quat is not None:
        gx, gy = poligono_para_scatter_xy(poli_quat)
        fig.add_trace(go.Scatter(
            x=gx, y=gy, mode="lines", line=dict(width=0), fill="toself",
            fillcolor=COR_QUATERNARIO, name="Depósito quaternário",
            showlegend=False, visible=False, hoverinfo="none",
        ), row=1, col=1)
    idx_geo_mapa_fim = idx_geo_mapa_inicio + n_geo_mapa - 1

    # camadas de referencia do OpenStreetMap (rios, estradas, localidades) --
    # depois da geologia (desenham por cima da cor do terreno) e antes da
    # linha do perfil (que precisa continuar visivel por cima de tudo no
    # mapa). Um toggle so ("OSM: ON/OFF"), independente do modo de cor.
    idx_osm_inicio = len(fig.data)
    if OSM_RIOS_GEOJSON.exists():
        gdf_rios = gpd.read_file(OSM_RIOS_GEOJSON)
        rx, ry = linhas_para_scatter_xy(gdf_rios)
        fig.add_trace(go.Scatter(
            x=rx, y=ry, mode="lines", line=dict(color="#2E6F95", width=1),
            name="Rios (OSM)", showlegend=True, visible=False, hoverinfo="none",
            legendrank=LEGENDRANK_OSM["rios"], legendgroup="rios",
        ), row=1, col=1)
    if OSM_ESTRADAS_GEOJSON.exists():
        gdf_estradas = gpd.read_file(OSM_ESTRADAS_GEOJSON)
        rx, ry = linhas_para_scatter_xy(gdf_estradas)
        fig.add_trace(go.Scatter(
            x=rx, y=ry, mode="lines", line=dict(color="#4A4A4A", width=1),
            name="Estradas (OSM)", showlegend=True, visible=False, hoverinfo="none",
            legendrank=LEGENDRANK_OSM["estradas"], legendgroup="estradas",
        ), row=1, col=1)
    # localidades: sem rotulo permanente no mapa (usuario pediu mapa sem
    # rotulo), mas ganham um marcador GRANDE/em destaque (estrela dourada) --
    # o nome do municipio so no hover, pra nao poluir mas ainda ficar visivel
    # e reconhecivel de cara. Mesmo legendgroup da versao "pin" da secao (nao
    # duplica entrada na legenda, so essa e a da secao ligam/desligam juntas).
    localidades_dados = []
    if OSM_LUGARES_GEOJSON.exists():
        gdf_lugares = gpd.read_file(OSM_LUGARES_GEOJSON)
        localidades_dados = list(zip(gdf_lugares["name"], gdf_lugares.geometry.x, gdf_lugares.geometry.y))
        fig.add_trace(go.Scatter(
            x=[x for _, x, _ in localidades_dados], y=[y for _, _, y in localidades_dados],
            mode="markers", marker=dict(size=14, color=MARCA_ROXO, symbol="triangle-down",
                                          line=dict(color=MARCA_CINZA_CLARO, width=1.5)),
            text=[nome for nome, _, _ in localidades_dados], hoverinfo="text",
            showlegend=False, visible=False, legendgroup="lugares",
        ), row=1, col=1)

    # rios/estradas NAO viram rotulo no mapa (usuario pediu mapa sem rotulo)
    # -- em vez disso ficam disponiveis pro JS projetar como "pin" na SECAO
    # (row=1,col=2): uma linha condutora fina subindo da topografia real ate
    # um pouco acima dela, com o marcador+nome na ponta (estilo pin de
    # mapa). Localidades sao projetadas continuamente (qualquer deslocamento/
    # angulo, ver atualizarPins); rios/estradas usam cruzamento real da linha
    # de corte (precomputado por posicao em calcular_cruzamentos, so existe
    # nos PASSO_POSICAO discretos). 2 traces por tipo (linha condutora +
    # marcador/texto), todas comecam vazias, JS preenche no load e a cada
    # mudanca de angulo/posicao.
    ESTILO_PIN = {
        "lugares": dict(cor=MARCA_ROXO, simbolo="triangle-down"),
        "rios": dict(cor="#2E6F95", simbolo="circle"),
        "estradas": dict(cor="#4A4A4A", simbolo="square"),
    }
    idx_pin_traces = {}
    for tipo in ("lugares", "rios", "estradas"):
        estilo = ESTILO_PIN[tipo]
        idx_pin_traces[f"{tipo}_linha"] = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines", line=dict(color=estilo["cor"], width=1.5, dash="dot"),
            showlegend=False, visible=False, hoverinfo="none", legendgroup=tipo,
        ), row=1, col=2)
        idx_pin_traces[f"{tipo}_marcador"] = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="markers+text", textposition="top center",
            textfont=dict(size=9, color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
            marker=dict(color=estilo["cor"], symbol=estilo["simbolo"], line=dict(color=MARCA_CINZA_CLARO, width=1)),
            name={"lugares": "Localidades (OSM)", "rios": "Rios (OSM)", "estradas": "Estradas (OSM)"}[tipo],
            showlegend=(tipo == "lugares"), visible=False, hoverinfo="none",
            legendrank=LEGENDRANK_OSM[tipo], legendgroup=tipo,
        ), row=1, col=2)
    idx_osm_fim = len(fig.data) - 1

    # pontos de campo (catalogo unificado, 308 pontos reais medidos em campo) --
    # no mapa em planta (coloridos por litologia_padronizada, popup no hover) E
    # como "pin" na SECAO (projetados na linha de corte atual, mesmo esquema
    # das localidades OSM -- ver atualizarPins). Toggle proprio ("Campo:
    # ON/OFF"), independente do OSM.
    idx_pontos_campo = None
    idx_campo_pin_linha = None
    idx_campo_pin_marcador = None
    campo_dados_secao = []
    if PONTOS_CAMPO_GPKG.exists():
        gdf_campo = gpd.read_file(PONTOS_CAMPO_GPKG)
        cores_campo = [CORES_LITOLOGIA_CAMPO.get(lit, COR_LITOLOGIA_PADRAO) for lit in gdf_campo["litologia_padronizada"]]
        hover_campo = [
            f"<b>{row.ponto_id}</b> ({row.id_original})<br>"
            f"Litologia: {row.litologia_padronizada}<br>"
            f"Tipo: {row.tipo_ponto}<br>"
            f"Qualidade: {row.qualidade_dado}<br>"
            f"Z: {row.Z_m:.0f} m<br>"
            f"{(row.descricao_campo or '')[:120]}"
            for row in gdf_campo.itertuples()
        ]
        idx_pontos_campo = len(fig.data)
        fig.add_trace(go.Scatter(
            x=gdf_campo.geometry.x, y=gdf_campo.geometry.y, mode="markers",
            marker=dict(size=6, color=cores_campo, line=dict(color=MARCA_CINZA_CLARO, width=0.5)),
            text=hover_campo, hoverinfo="text",
            name="Pontos de Campo", showlegend=False, visible=False, legendgroup="campo",
        ), row=1, col=1)
        campo_dados_secao = [
            (row.ponto_id, row.geometry.x, row.geometry.y,
             CORES_LITOLOGIA_CAMPO.get(row.litologia_padronizada, COR_LITOLOGIA_PADRAO), hover)
            for row, hover in zip(gdf_campo.itertuples(), hover_campo)
        ]
        idx_campo_pin_linha = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines", line=dict(color=MARCA_CINZA_CLARO, width=1, dash="dot"),
            showlegend=False, visible=False, hoverinfo="none", legendgroup="campo",
        ), row=1, col=2)
        idx_campo_pin_marcador = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="markers+text", textposition="top center",
            textfont=dict(size=9, color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
            marker=dict(symbol="diamond", line=dict(color=MARCA_CINZA_CLARO, width=1)),
            name="Pontos de Campo", showlegend=True, visible=False, hoverinfo="text",
            legendrank=0, legendgroup="campo",
        ), row=1, col=2)

    # dados estruturais -- duas categorias: "fratura_falha" (dado de campo,
    # tem dip medido de verdade) e "falha_ou_dique_ambiguo_relevo_negativo"
    # (lineamento de satelite, so azimute, dip_deg sempre NaN -- ja
    # documentado no projeto). Como nem toda linha tem mergulho confiavel,
    # NAO usa o esquema de "pin" com balao inclinado por mergulho -- em vez
    # disso e um risco vertical fino (preto) cortando a secao inteira, com um
    # simbolo de falha (X) numa altura fixa, na posicao onde a linha de corte
    # atual cruza o ponto/lineamento.
    CLASSIFICACOES_ESTRUTURAL_ALVO = ["falha_ou_dique_ambiguo_relevo_negativo", "fratura_falha"]
    estrutural_dados_secao = []
    if PONTOS_ESTRUTURAIS_GPKG.exists():
        gdf_estrut = gpd.read_file(PONTOS_ESTRUTURAIS_GPKG)
        gdf_estrut = gdf_estrut[gdf_estrut["classificacao"].isin(CLASSIFICACOES_ESTRUTURAL_ALVO)]
        for row in gdf_estrut.itertuples():
            dip_txt = f"{row.dip_deg:.0f}°" if pd.notna(row.dip_deg) else "não medido"
            hover = (
                f"<b>{row.ponto_id}</b><br>"
                f"Classificação: {row.classificacao}<br>"
                f"Formação: {row.formacao}<br>"
                f"Azimute: {row.azimute_ou_strike_deg:.0f}°<br>"
                f"Mergulho: {dip_txt}<br>"
                f"Fonte: {row.fonte_dado}"
            )
            estrutural_dados_secao.append((row.geometry.x, row.geometry.y, hover))
        # a trace so e adicionada mais abaixo, DEPOIS do loop de ORDEM_TRACES --
        # senao (ordem de insercao 2D = ordem de desenho) o risco ficava
        # ESCONDIDO atras das camadas/terreno, que sao desenhados depois dela.

    idx_trace_terreno = None
    for chave in ORDEM_TRACES:
        x, y = inicial[chave]
        if chave == "linha_mapa":
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color="black", width=2, dash="dash"), showlegend=False), row=1, col=1)
        elif chave == "terreno":
            idx_trace_terreno = len(fig.data)
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=MARCA_CINZA_CLARO, width=1.5), showlegend=False), row=1, col=2)
        else:
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", line=dict(width=0), fill="toself",
                fillcolor=CORES_TRACES[chave], name=NOMES_TRACES[chave], legendrank=LEGENDRANK_TRACES[chave],
            ), row=1, col=2)

    # risco estrutural (fratura/falha + falha-ou-dique de relevo negativo) --
    # so agora, DEPOIS do loop de ORDEM_TRACES (terreno/camadas/quaternario/
    # sill/dique), pra desenhar por CIMA deles (ordem de insercao = ordem de
    # desenho em 2D) -- antes ficava escondido atras das camadas. Duas
    # traces: o risco vertical fino em si, e um simbolo de falha (X --
    # duas barras cruzadas, convencao geologica padrao de simbolo de falha
    # em secao) desenhado numa altura fixa junto a cada linha.
    idx_estrutural_risco = None
    idx_estrutural_simbolo = None
    if estrutural_dados_secao:
        idx_estrutural_risco = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines", line=dict(color="black", width=1),
            name="Falha/Fratura", showlegend=True, visible=False,
            hoverinfo="text", legendgroup="estrutural",
        ), row=1, col=2)
        idx_estrutural_simbolo = len(fig.data)
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines", line=dict(color="black", width=4),
            showlegend=False, visible=False, hoverinfo="none", legendgroup="estrutural",
        ), row=1, col=2)

    # escala grafica + seta norte no mapa em planta -- elementos cartograficos
    # padrao, adicionados por ULTIMO (depois de todas as traces usadas nos
    # frames) pra nao interferir nos indices do corte/geologia acima.
    comprimento_escala = 5000.0  # 5 km
    esc_x0 = X_MIN + (X_MAX - X_MIN) * 0.05
    esc_x1 = esc_x0 + comprimento_escala
    esc_y = Y_MIN + (Y_MAX - Y_MIN) * 0.04
    tick = (Y_MAX - Y_MIN) * 0.012
    esc_x_lista = [esc_x0, esc_x0, None, esc_x0, esc_x1, None, esc_x1, esc_x1]
    esc_y_lista = [esc_y - tick, esc_y + tick, None, esc_y, esc_y, None, esc_y - tick, esc_y + tick]
    # preto com contorno branco (linha branca mais grossa por baixo) -- fica
    # legivel em qualquer parte do mapa, seja hipsometria ou geologia.
    fig.add_trace(go.Scatter(
        x=esc_x_lista, y=esc_y_lista, mode="lines", line=dict(color="white", width=5),
        showlegend=False, hoverinfo="none",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=esc_x_lista, y=esc_y_lista, mode="lines", line=dict(color="black", width=2),
        showlegend=False, hoverinfo="none",
    ), row=1, col=1)
    fig.add_annotation(
        x=(esc_x0 + esc_x1) / 2, y=esc_y + (Y_MAX - Y_MIN) * 0.03, xref="x", yref="y",
        text=f"{comprimento_escala / 1000:.0f} km", showarrow=False,
        font=dict(size=11, color="black"), xanchor="center",
    )

    norte_x = X_MAX - (X_MAX - X_MIN) * 0.10
    norte_y0 = Y_MAX - (Y_MAX - Y_MIN) * 0.24
    norte_y1 = Y_MAX - (Y_MAX - Y_MIN) * 0.13
    fig.add_annotation(
        x=norte_x, y=norte_y1, ax=norte_x, ay=norte_y0, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="black", text="",
    )
    fig.add_annotation(
        x=norte_x, y=norte_y1 + (Y_MAX - Y_MIN) * 0.025, xref="x", yref="y",
        text="N", showarrow=False, font=dict(size=13, color="black"),
    )

    # direcao real (O/L/S/N/etc.) nas pontas da secao transversal -- extraida
    # do nome do angulo ("Horizontal (O↔L)" -> "O" na ponta esquerda/dists=0,
    # "L" na direita/dists=comprimento). Atualiza via JS quando o angulo muda
    # (irParaAngulo), igual o range do eixo X.
    def extrair_direcoes(nome):
        miolo = nome.split("(")[1].rstrip(")")
        return miolo.split("↔")
    y_direcao = 1100.0  # perto do topo do eixo Y da secao (range ate 1150)
    comprimento0_km = (angulos_info[0]["s_vals"][-1] - angulos_info[0]["s_vals"][0]) / 1000
    dir0_inicial, dir1_inicial = extrair_direcoes(ANGULOS[0][0])
    idx_anotacao_dir0 = len(fig.layout.annotations)
    fig.add_annotation(
        x=0, y=y_direcao, xref="x2", yref="y2", text=dir0_inicial, showarrow=False,
        font=dict(size=13, color=MARCA_CINZA_CLARO), xanchor="left",
    )
    idx_anotacao_dir1 = len(fig.layout.annotations)
    fig.add_annotation(
        x=comprimento0_km, y=y_direcao, xref="x2", yref="y2", text=dir1_inicial, showarrow=False,
        font=dict(size=13, color=MARCA_CINZA_CLARO), xanchor="right",
    )

    # heatmap + poligonos de geologia (+ quaternario) + camadas OSM + pontos de campo (se existir) --
    # nenhuma dessas traces muda entre frames, entao os frames de corte comecam logo depois delas.
    # NOTA: o risco estrutural NAO entra aqui -- suas traces sao adicionadas
    # DEPOIS do loop de ORDEM_TRACES (de proposito, pra desenhar por cima),
    # entao ficam fora do intervalo animado por frame, nao antes dele.
    if idx_pontos_campo is not None:
        n_traces_fixas = idx_campo_pin_marcador + 1
    else:
        n_traces_fixas = idx_osm_fim + 1
    frames = []
    for a, secoes_angulo in enumerate(todas_secoes):
        for p, secao in enumerate(secoes_angulo):
            dados_frame = [go.Scatter(x=secao[chave][0], y=secao[chave][1]) for chave in ORDEM_TRACES]
            frames.append(go.Frame(
                data=dados_frame, name=f"{a}_{p}",
                traces=list(range(n_traces_fixas, n_traces_fixas + len(ORDEM_TRACES))),
            ))
    fig.frames = frames

    # grafico de barras da espessura das formacoes na linha atual (em vez de
    # so texto -- mais facil de comparar magnitude entre as 5 formacoes,
    # bar chart e a escolha certa aqui pq sao valores em metros comparaveis,
    # nao proporcao de um todo tipo pizza). Atualizado via JS (Plotly.restyle
    # em y/text) quando o angulo/posicao muda -- nao faz parte do sistema de
    # frames do corte, e uma trace fixa a parte.
    idx_trace_barra = len(fig.data)
    fig.add_trace(go.Bar(
        x=NOMES_CAMADAS, y=inicial["espessuras"], marker_color=CORES_CAMADAS,
        marker_line=dict(color=MARCA_ROXO, width=1),
        text=[f"{e:.0f}m" for e in inicial["espessuras"]], textposition="outside",
        textfont=dict(color=MARCA_CINZA_CLARO), showlegend=False, hoverinfo="none",
    ), row=2, col=1)

    COR_PAINEL = "#3A3A46"  # fundo cinza dos graficos (secao + barras), diferente do navy da pagina -- mais facil de ler
    eixo_escuro = dict(gridcolor="#54545f", zerolinecolor="#6a6a75", color=MARCA_CINZA_CLARO)
    fig.update_xaxes(showticklabels=False, row=1, col=1, range=[X_MIN, X_MAX], scaleanchor="y1", scaleratio=1, constrain="domain")
    fig.update_yaxes(showticklabels=False, row=1, col=1, range=[Y_MIN, Y_MAX], constrain="domain")
    comprimento0_km = (angulos_info[0]["s_vals"][-1] - angulos_info[0]["s_vals"][0]) / 1000
    fig.update_xaxes(title_text="Distância ao longo da seção (km)", row=1, col=2, range=[0, comprimento0_km], **eixo_escuro)
    fig.update_yaxes(title_text="Elevação (m)", row=1, col=2, range=[-600, 1150], **eixo_escuro)
    fig.update_xaxes(row=2, col=1, **eixo_escuro)
    fig.update_yaxes(title_text="Espessura (m)", row=2, col=1, range=[0, 400], **eixo_escuro)

    fig.update_layout(
        title=dict(
            text="<b>Modelo 2D Taió Plumbing System</b> — Seção transversal interativa",
            font=dict(family=MARCA_FONTE, size=24, color=MARCA_CINZA_CLARO),
            x=0.03, xanchor="left",
        ),
        paper_bgcolor=MARCA_NAVY, plot_bgcolor=COR_PAINEL,
        font=dict(family=MARCA_FONTE, color=MARCA_CINZA_CLARO),
        height=840,
        legend=dict(x=1.01, y=0.94, bgcolor="rgba(45,10,74,0.75)", bordercolor=MARCA_ROXO, borderwidth=1,
                    font=dict(color=MARCA_CINZA_CLARO)),
        margin=dict(l=50, r=180, t=70, b=220),
        updatemenus=[
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.5, y=-0.38, xanchor="center", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[dict(label=nome, method="skip") for nome, _ in ANGULOS] + [
                    dict(label="Mapa: Hipsometria", method="restyle",
                         args=[{"visible": [True] + [False] * n_geo_mapa}, [0] + list(range(idx_geo_mapa_inicio, idx_geo_mapa_fim + 1))]),
                    dict(label="Mapa: Geologia (CPRM real)", method="restyle",
                         args=[{"visible": [False] + [True] * n_geo_mapa}, [0] + list(range(idx_geo_mapa_inicio, idx_geo_mapa_fim + 1))]),
                    dict(label="Tema: Escuro", method="skip"),
                    dict(label="Tema: Claro", method="skip"),
                ],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.5, y=-0.46, xanchor="center", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[
                    dict(label="OSM: ON", method="restyle",
                         args=[{"visible": True}, list(range(idx_osm_inicio, idx_osm_fim + 1))]),
                    dict(label="OSM: OFF", method="restyle",
                         args=[{"visible": False}, list(range(idx_osm_inicio, idx_osm_fim + 1))]),
                ] + ([
                    dict(label="Campo: ON", method="restyle",
                         args=[{"visible": True}, [idx_pontos_campo, idx_campo_pin_linha, idx_campo_pin_marcador]]),
                    dict(label="Campo: OFF", method="restyle",
                         args=[{"visible": False}, [idx_pontos_campo, idx_campo_pin_linha, idx_campo_pin_marcador]]),
                ] if idx_pontos_campo is not None else []) + ([
                    dict(label="Estrutura: ON", method="restyle",
                         args=[{"visible": True}, [idx_estrutural_risco, idx_estrutural_simbolo]]),
                    dict(label="Estrutura: OFF", method="restyle",
                         args=[{"visible": False}, [idx_estrutural_risco, idx_estrutural_simbolo]]),
                ] if idx_estrutural_risco is not None else []),
            ),
        ],
        sliders=[dict(
            active=n_pos_inicial // 2,
            currentvalue=dict(prefix="Deslocamento perpendicular ao corte: ", font=dict(color=MARCA_CINZA_CLARO)),
            pad=dict(t=30),
            bgcolor=MARCA_ROXO_ESCURO, activebgcolor=MARCA_ROXO, bordercolor=MARCA_ROXO,
            font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
            steps=[
                dict(
                    method="animate",
                    args=[[f"0_{p}"], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
                    label=f"{angulos_info[0]['t_vals'][p]:+.0f} m",
                )
                for p in range(n_pos_inicial)
            ],
        )],
    )

    angulos_js = ",\n        ".join(
        "{dx:%.6f, dy:%.6f, px:%.6f, py:%.6f, s0:%.3f, compKm:%.3f, dir0:'%s', dir1:'%s', t:[%s]}" % (
            info["dx"], info["dy"], info["px"], info["py"], info["s_vals"][0],
            (info["s_vals"][-1] - info["s_vals"][0]) / 1000,
            *extrair_direcoes(info["nome"]),
            ",".join(f"{t:.2f}" for t in info["t_vals"]),
        )
        for info in angulos_info
    )
    espessuras_js = ",\n        ".join(
        "[" + ",\n         ".join("[" + ",".join(f"{e:.1f}" for e in secao["espessuras"]) + "]" for secao in secoes_angulo) + "]"
        for secoes_angulo in todas_secoes
    )
    nomes_camadas_js = ",".join(f"'{nome}'" for nome in NOMES_CAMADAS)
    localidades_js = ",".join(
        "{nome:%r, x:%.1f, y:%.1f}" % (str(nome), x, y) for nome, x, y in localidades_dados
    )
    campo_js = ",".join(
        "{nome:%r, x:%.1f, y:%.1f, cor:%r, hover:%r}" % (str(nome), x, y, cor, hover)
        for nome, x, y, cor, hover in campo_dados_secao
    )
    estrutural_js = ",".join(
        "{x:%.1f, y:%.1f, hover:%r}" % (x, y, hover) for x, y, hover in estrutural_dados_secao
    )

    def cruzamentos_js(todas_pins):
        return ",\n        ".join(
            "[" + ",\n         ".join(
                "[" + ",".join("{s:%.3f,z:%.1f,nome:%r}" % (s, z, str(nome)) for s, z, nome in pos) + "]"
                for pos in pins_angulo
            ) + "]"
            for pins_angulo in todas_pins
        )

    pins_rios_js = cruzamentos_js(todas_pins_rios)
    pins_estradas_js = cruzamentos_js(todas_pins_estradas)
    logo_b64 = logo_base64()
    marca_html = f"""
    (function() {{
        var style = document.createElement('style');
        style.textContent = 'body {{ background: {MARCA_NAVY}; margin: 0; }}';
        document.head.appendChild(style);
        var logo = document.createElement('img');
        logo.src = 'data:image/jpeg;base64,{logo_b64}';
        logo.style.cssText = 'position:fixed; top:14px; right:18px; width:64px; height:64px; ' +
            'border-radius:50%; border:2px solid {MARCA_ROXO}; box-shadow:0 0 10px rgba(123,47,255,0.6); z-index:1000;';
        document.body.appendChild(logo);
        var atribuicao = document.createElement('div');
        atribuicao.textContent = 'Criado por Afonso Henrique de Jesus';
        atribuicao.style.cssText = 'position:fixed; bottom:6px; left:14px; color:{MARCA_CINZA_CLARO}; ' +
            'opacity:0.55; font-family:{MARCA_FONTE}; font-size:11px; z-index:1000;';
        document.body.appendChild(atribuicao);
    }})();
    """ if logo_b64 else ""

    post_script = f"""
    {marca_html}
    (function() {{
        var CX = {CX}, CY = {CY};
        var ANGULOS = [
        {angulos_js}
        ];
        var ESPESSURAS = [
        {espessuras_js}
        ];
        var NOMES_CAMADAS = [{nomes_camadas_js}];
        var LOCALIDADES = [{localidades_js}];
        var PONTOS_CAMPO_SECAO = [{campo_js}];
        var ESTRUTURAL_SECAO = [{estrutural_js}];
        var PINS_RIOS = [
        {pins_rios_js}
        ];
        var PINS_ESTRADAS = [
        {pins_estradas_js}
        ];
        var LIMIAR_PIN_M = 2000;  // so vira pin se a linha de corte passar a menos de 2km da localidade
        var LIMIAR_PIN_CAMPO_M = 400;  // pontos de campo sao 308 -- limiar bem mais apertado que localidades
        var ALTURA_PIN_M = 60;  // marcador fica esse tanto (metros) acima da topografia real
        var IDX_TRACE_BARRA = {idx_trace_barra};
        var IDX_TRACE_TERRENO = {idx_trace_terreno};
        var IDX_PIN_LUGARES_LINHA = {idx_pin_traces["lugares_linha"]};
        var IDX_PIN_LUGARES_MARCADOR = {idx_pin_traces["lugares_marcador"]};
        var IDX_PIN_RIOS_LINHA = {idx_pin_traces["rios_linha"]};
        var IDX_PIN_RIOS_MARCADOR = {idx_pin_traces["rios_marcador"]};
        var IDX_PIN_ESTRADAS_LINHA = {idx_pin_traces["estradas_linha"]};
        var IDX_PIN_ESTRADAS_MARCADOR = {idx_pin_traces["estradas_marcador"]};
        var IDX_CAMPO_PIN_LINHA = {idx_campo_pin_linha};
        var IDX_CAMPO_PIN_MARCADOR = {idx_campo_pin_marcador};
        var IDX_ESTRUTURAL_RISCO = {idx_estrutural_risco};
        var IDX_ESTRUTURAL_SIMBOLO = {idx_estrutural_simbolo};
        var LIMIAR_ESTRUTURAL_M = 400;  // mesmo limiar apertado dos pontos de campo
        var Y_MIN_SECAO = -600;  // fundo fixo do risco -- o topo agora segue a topografia real
        var GAP_SIMBOLO_KM = 0.025;  // buffer/gap entre cada meia-seta e o risco vertical
        var ALTURA_SIMBOLO_M = 90;  // variacao vertical (altura) de cada meia-seta, em metros
        var OFFSET_SIMBOLO_M = 70;  // deslocamento vertical entre as duas metades (efeito "fatiado")
        var IDX_ANOTACAO_DIR0 = {idx_anotacao_dir0};
        var IDX_ANOTACAO_DIR1 = {idx_anotacao_dir1};
        var IDX_ANOTACOES_SUBTITULO = [0, 1, 2];
        var anguloAtual = 0;
        var gd = document.getElementsByClassName('plotly-graph-div')[0];

        // tema claro/escuro -- escala/norte ja tem contorno branco+preto
        // (nao muda com o tema), heatmap/geologia/camadas/sill/dique tem
        // cor propria (nao muda). So a "moldura" (fundo, grade, texto).
        var TEMA = {{
            escuro: {{
                paper: '{MARCA_NAVY}', painel: '{COR_PAINEL}', texto: '{MARCA_CINZA_CLARO}',
                grid: '#54545f', zerogrid: '#6a6a75', legendBg: 'rgba(45,10,74,0.75)',
                botaoBg: '{MARCA_ROXO_ESCURO}',
            }},
            claro: {{
                paper: '{MARCA_CINZA_CLARO}', painel: '#FFFFFF', texto: '{MARCA_NAVY}',
                grid: '#D0D0D8', zerogrid: '#B8B8C4', legendBg: 'rgba(255,255,255,0.85)',
                botaoBg: '#EDE3FF',
            }},
        }};

        function aplicarTema(nome) {{
            var t = TEMA[nome];
            var patch = {{
                paper_bgcolor: t.paper, plot_bgcolor: t.painel,
                'font.color': t.texto,
                'legend.bgcolor': t.legendBg, 'legend.font.color': t.texto,
                'title.font.color': t.texto,
                'updatemenus[0].bgcolor': t.botaoBg, 'updatemenus[0].font.color': t.texto,
                'updatemenus[1].bgcolor': t.botaoBg, 'updatemenus[1].font.color': t.texto,
                'sliders[0].bgcolor': t.botaoBg, 'sliders[0].font.color': t.texto,
                'sliders[0].currentvalue.font.color': t.texto,
                'xaxis2.color': t.texto, 'xaxis2.gridcolor': t.grid, 'xaxis2.zerolinecolor': t.zerogrid,
                'yaxis2.color': t.texto, 'yaxis2.gridcolor': t.grid, 'yaxis2.zerolinecolor': t.zerogrid,
                'xaxis3.color': t.texto, 'xaxis3.gridcolor': t.grid, 'xaxis3.zerolinecolor': t.zerogrid,
                'yaxis3.color': t.texto, 'yaxis3.gridcolor': t.grid, 'yaxis3.zerolinecolor': t.zerogrid,
            }};
            IDX_ANOTACOES_SUBTITULO.concat([IDX_ANOTACAO_DIR0, IDX_ANOTACAO_DIR1]).forEach(function(idx) {{
                patch['annotations[' + idx + '].font.color'] = t.texto;
            }});
            Plotly.relayout(gd, patch);
            Plotly.restyle(gd, {{'line.color': t.texto}}, [IDX_TRACE_TERRENO]);
            Plotly.restyle(gd, {{'textfont.color': t.texto}}, [IDX_TRACE_BARRA]);
            // rotulos dos pins (nome da localidade/rio/estrada na secao) tambem
            // tem cor propria fixa na criacao -- sem isso ficavam ilegiveis no
            // tema claro (texto claro sobre fundo claro).
            Plotly.restyle(gd, {{'textfont.color': t.texto}},
                [IDX_PIN_LUGARES_MARCADOR, IDX_PIN_RIOS_MARCADOR, IDX_PIN_ESTRADAS_MARCADOR]);
            document.body.style.background = t.paper;
        }}

        // elevacao real (interpolada) do terreno numa distancia x (km) do
        // perfil ATUAL -- usa a propria trace do terreno (ja reflete o
        // angulo/posicao em exibicao), busca linear (poucas centenas de
        // pontos, ok pra rodar a cada mudanca de angulo/slider).
        function interpolarElevacao(xKm) {{
            var tr = gd._fullData[IDX_TRACE_TERRENO];
            var tx = tr.x, ty = tr.y;
            var n = tx.length;
            if (xKm <= tx[0]) return ty[0];
            if (xKm >= tx[n - 1]) return ty[n - 1];
            for (var i = 0; i < n - 1; i++) {{
                if (tx[i] <= xKm && xKm <= tx[i + 1]) {{
                    var frac = (tx[i + 1] === tx[i]) ? 0 : (xKm - tx[i]) / (tx[i + 1] - tx[i]);
                    return ty[i] + frac * (ty[i + 1] - ty[i]);
                }}
            }}
            return ty[n - 1];
        }}

        var LIMIAR_SOBREPOSICAO_KM = 0.5;  // pins mais pertos que isso escalonam de altura
        var N_NIVEIS_ALTURA = 4;  // 1x,2x,3x,4x ALTURA_PIN_M, depois volta pro 1x

        // escalona a altura (multiplo de ALTURA_PIN_M) de cada ponto -- pontos
        // ja ordenados por x: sobe 1 nivel toda vez que o proximo esta perto
        // do anterior (< LIMIAR_SOBREPOSICAO_KM), reseta quando abre espaco.
        // Evita rotulo grudado em rotulo quando varios pins caem perto (ver
        // screenshot que o usuario mandou -- "Estrada Estrada Sao..." ilegivel).
        // localidade (municipio) fica sempre em destaque -- maior e mais alta
        // que rio/estrada por perto, mesmo dentro do mesmo cluster de
        // sobreposicao (pedido explicito do usuario).
        var BOOST_LUGARES_NIVEIS = 2;

        function atribuirAlturas(pontosOrdenados) {{
            var nivel = 0;
            pontosOrdenados.forEach(function(p, i) {{
                if (i > 0 && (p.x - pontosOrdenados[i - 1].x) < LIMIAR_SOBREPOSICAO_KM) {{
                    nivel = (nivel + 1) % N_NIVEIS_ALTURA;
                }} else {{
                    nivel = 0;
                }}
                var nivelFinal = nivel + (p.tipo === 'lugares' ? N_NIVEIS_ALTURA + BOOST_LUGARES_NIVEIS : 0);
                p.altura = ALTURA_PIN_M * (nivelFinal + 1);
            }});
        }}

        // monta a linha condutora (base na topografia real, ponta na altura
        // escalonada) + DOIS marcadores por pin: um pequeno exatamente na
        // posicao/elevacao real do cruzamento (a "posicao" pedida, nao so o
        // rotulo flutuando) e o marcador estilizado (com o nome) na ponta da
        // linha condutora, estilo balao de mapa.
        function restylarPins(idxLinha, idxMarcador, pontos, corTipo, simboloTipo, tamanhoTopo) {{
            var lx = [], ly = [], mx = [], my = [], texts = [], sizes = [], symbols = [], cores = [], hovers = [];
            pontos.forEach(function(p, i) {{
                if (i > 0) {{ lx.push(NaN); ly.push(NaN); }}
                var topo = p.z + p.altura;
                var cor = p.cor || corTipo;  // pontos de campo tem cor propria (por litologia)
                lx.push(p.x, p.x);
                ly.push(p.z, topo);
                // ponto na posicao real (pequeno, sem rotulo)
                mx.push(p.x); my.push(p.z); texts.push(''); sizes.push(5); symbols.push('circle'); cores.push(cor); hovers.push('');
                // ponto na ponta da linha condutora (estilizado, com o nome) --
                // localidade fica maior (tamanhoTopo), em destaque sobre rio/estrada.
                // popup no hover so pra quem tem dado (p.hover, ex.: pontos de campo).
                mx.push(p.x); my.push(topo); texts.push(p.nome); sizes.push(tamanhoTopo); symbols.push(simboloTipo); cores.push(cor);
                hovers.push(p.hover || p.nome);
            }});
            Plotly.restyle(gd, {{x: [lx], y: [ly]}}, [idxLinha]);
            Plotly.restyle(gd, {{
                x: [mx], y: [my], text: [texts], hovertext: [hovers],
                'marker.size': [sizes], 'marker.symbol': [symbols], 'marker.color': [cores],
            }}, [idxMarcador]);
        }}

        // projeta cada localidade na linha de corte ATUAL (angulo a, deslocamento
        // perpendicular offsetT) -- decompoe o vetor CX,CY->localidade na base
        // ortonormal (dx,dy)/(px,py): a componente ao longo de (dx,dy) da a
        // posicao na secao (mesmo "s" usado pra amostrar o perfil, indepen-
        // dente de offsetT); a componente ao longo de (px,py) da a distancia
        // perpendicular da localidade ATE a linha center (CX,CY) -- subtraindo
        // offsetT da isso vira a distancia ate a linha JA deslocada. So vira
        // pin se essa distancia perpendicular for pequena (LIMIAR_PIN_M). Rios
        // e estradas usam cruzamento real pre-calculado (PINS_RIOS/PINS_ESTRADAS),
        // ja tem a elevacao exata do ponto de cruzamento. As alturas sao
        // escalonadas JUNTAS (localidade+rio+estrada perto uma da outra
        // tambem colidem no grafico), depois cada tipo e restilizado separado.
        function atualizarPins(a, p) {{
            var info = ANGULOS[a];
            var offsetT = info.t[p];
            var lugares = [];
            LOCALIDADES.forEach(function(loc) {{
                var vx = loc.x - CX, vy = loc.y - CY;
                var s = vx * info.dx + vy * info.dy;
                var tLoc = vx * info.px + vy * info.py;
                var perp = tLoc - offsetT;
                if (Math.abs(perp) <= LIMIAR_PIN_M) {{
                    var xKm = (s - info.s0) / 1000;
                    lugares.push({{x: xKm, z: interpolarElevacao(xKm), nome: loc.nome, tipo: 'lugares'}});
                }}
            }});
            var rios = (PINS_RIOS[a][p] || []).map(function(c) {{ return {{x: c.s, z: c.z, nome: c.nome, tipo: 'rios'}}; }});
            var estradas = (PINS_ESTRADAS[a][p] || []).map(function(c) {{ return {{x: c.s, z: c.z, nome: c.nome, tipo: 'estradas'}}; }});

            // pontos de campo: mesma projecao continua das localidades, mas com
            // limiar bem mais apertado (LIMIAR_PIN_CAMPO_M) -- sao 308 pontos, um
            // limiar igual ao das localidades inundaria a secao de pins.
            var campo = [];
            PONTOS_CAMPO_SECAO.forEach(function(pt) {{
                var vx = pt.x - CX, vy = pt.y - CY;
                var s = vx * info.dx + vy * info.dy;
                var tLoc = vx * info.px + vy * info.py;
                var perp = tLoc - offsetT;
                if (Math.abs(perp) <= LIMIAR_PIN_CAMPO_M) {{
                    var xKm = (s - info.s0) / 1000;
                    campo.push({{x: xKm, z: interpolarElevacao(xKm), nome: pt.nome, cor: pt.cor, hover: pt.hover, tipo: 'campo'}});
                }}
            }});

            var todos = lugares.concat(rios, estradas, campo);
            todos.sort(function(a, b) {{ return a.x - b.x; }});
            atribuirAlturas(todos);

            restylarPins(IDX_PIN_LUGARES_LINHA, IDX_PIN_LUGARES_MARCADOR,
                todos.filter(function(pt) {{ return pt.tipo === 'lugares'; }}), '{MARCA_ROXO}', 'triangle-down', 15);
            restylarPins(IDX_PIN_RIOS_LINHA, IDX_PIN_RIOS_MARCADOR,
                todos.filter(function(pt) {{ return pt.tipo === 'rios'; }}), '#2E6F95', 'circle', 9);
            restylarPins(IDX_PIN_ESTRADAS_LINHA, IDX_PIN_ESTRADAS_MARCADOR,
                todos.filter(function(pt) {{ return pt.tipo === 'estradas'; }}), '#4A4A4A', 'square', 9);
            restylarPins(IDX_CAMPO_PIN_LINHA, IDX_CAMPO_PIN_MARCADOR,
                todos.filter(function(pt) {{ return pt.tipo === 'campo'; }}), '{COR_LITOLOGIA_PADRAO}', 'diamond', 9);
        }}

        // risco vertical fino cortando a secao -- projeta cada lineamento/
        // ponto estrutural na linha de corte ATUAL igual as localidades
        // (mesma decomposicao ortonormal), mas SEM elevacao/altura de pin:
        // e uma linha reta que vai do fundo da secao (Y_MIN_SECAO) ATE a
        // topografia real naquele x (interpolarElevacao) -- nao ultrapassa
        // o relevo, so risca por baixo dele. Sem inclinacao por mergulho de
        // proposito pros pontos sem dip medido (lineamento de satelite).
        // desenha uma meia-seta: cabo vertical (90 graus, paralelo ao proprio
        // risco) de (x,y0) a (x,y1), mais UMA farpa curta no head (lado
        // externo, longe do risco) formando a ponta -- sem farpa do lado de
        // dentro, pra nao ficar com a seta "cheia"/dobrada em cima da linha.
        var LARGURA_FARPA_KM = 0.045, ALTURA_FARPA_M = 45;
        function adicionarMeiaSeta(xs, ys, x, y0, y1, ladoFarpa) {{
            if (xs.length > 0) {{ xs.push(NaN); ys.push(NaN); }}
            xs.push(x, x); ys.push(y0, y1);
            var dirYFarpa = (y1 > y0) ? -1 : 1;
            xs.push(NaN, x, x + ladoFarpa * LARGURA_FARPA_KM);
            ys.push(NaN, y1, y1 + dirYFarpa * ALTURA_FARPA_M);
        }}

        function atualizarEstrutural(a, offsetT) {{
            var info = ANGULOS[a];
            var xs = [], ys = [], hovers = [];
            var xsSimbolo = [], ysSimbolo = [];
            ESTRUTURAL_SECAO.forEach(function(pt) {{
                var vx = pt.x - CX, vy = pt.y - CY;
                var s = vx * info.dx + vy * info.dy;
                var tLoc = vx * info.px + vy * info.py;
                var perp = tLoc - offsetT;
                if (Math.abs(perp) <= LIMIAR_ESTRUTURAL_M) {{
                    var xKm = (s - info.s0) / 1000;
                    var yTopo = interpolarElevacao(xKm);
                    if (xs.length > 0) {{ xs.push(NaN); ys.push(NaN); hovers.push(''); }}
                    xs.push(xKm, xKm); ys.push(Y_MIN_SECAO, yTopo);
                    hovers.push(pt.hover, pt.hover);
                    // simbolo de falha logo abaixo da topografia -- uma seta
                    // "fatiada" pelo risco: meia-seta subindo do lado esquerdo
                    // (desgrudada da linha, com um pequeno buffer/gap) apontando
                    // pra cima, e a outra metade descendo do lado direito
                    // apontando pra baixo -- como se a seta tivesse sido cortada
                    // e deslocada pelo proprio risco (convencao geologica padrao
                    // de simbolo de falha em secao).
                    var yCentro = yTopo - 120;
                    // cabo vertical de cada lado (90 graus, igual ao risco) --
                    // esquerda sobe, direita desce -- com a farpa apontando
                    // pra fora (longe da linha).
                    adicionarMeiaSeta(xsSimbolo, ysSimbolo, xKm - GAP_SIMBOLO_KM,
                        yCentro - OFFSET_SIMBOLO_M / 2, yCentro - OFFSET_SIMBOLO_M / 2 + ALTURA_SIMBOLO_M, -1);
                    adicionarMeiaSeta(xsSimbolo, ysSimbolo, xKm + GAP_SIMBOLO_KM,
                        yCentro + OFFSET_SIMBOLO_M / 2, yCentro + OFFSET_SIMBOLO_M / 2 - ALTURA_SIMBOLO_M, 1);
                }}
            }});
            Plotly.restyle(gd, {{x: [xs], y: [ys], hovertext: [hovers]}}, [IDX_ESTRUTURAL_RISCO]);
            if (IDX_ESTRUTURAL_SIMBOLO !== null) {{
                Plotly.restyle(gd, {{x: [xsSimbolo], y: [ysSimbolo]}}, [IDX_ESTRUTURAL_SIMBOLO]);
            }}
        }}

        function atualizarEspessuras(a, p) {{
            var vals = ESPESSURAS[a][p];
            var rotulos = vals.map(function(v) {{ return Math.round(v) + 'm'; }});
            Plotly.restyle(gd, {{y: [vals], text: [rotulos]}}, [IDX_TRACE_BARRA]);
            atualizarPins(a, p);
            atualizarEstrutural(a, ANGULOS[a].t[p]);
        }}

        // forca o estado inicial (posicao central) -- o slider as vezes
        // "deriva" pro ultimo step sozinho no load (comportamento estranho
        // do Plotly com varios steps sem "value" explicito).
        var posMeioInicial = {n_pos_inicial // 2};
        Plotly.animate(gd, ['0_' + posMeioInicial], {{mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}}}});
        Plotly.relayout(gd, {{'sliders[0].active': posMeioInicial}});
        atualizarEspessuras(0, posMeioInicial);

        function stepsParaAngulo(a) {{
            var info = ANGULOS[a];
            var steps = [];
            for (var p = 0; p < info.t.length; p++) {{
                var rotulo = (info.t[p] >= 0 ? '+' : '') + info.t[p].toFixed(0) + ' m';
                steps.push({{
                    method: 'animate',
                    args: [[a + '_' + p], {{mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}}}}],
                    label: rotulo,
                }});
            }}
            return steps;
        }}

        function irParaAngulo(a) {{
            anguloAtual = a;
            var posMeio = Math.floor(ANGULOS[a].t.length / 2);
            var patch = {{
                'sliders[0].steps': stepsParaAngulo(a),
                'sliders[0].active': posMeio,
                'xaxis2.range': [0, ANGULOS[a].compKm],
            }};
            patch['annotations[' + IDX_ANOTACAO_DIR0 + '].text'] = ANGULOS[a].dir0;
            patch['annotations[' + IDX_ANOTACAO_DIR1 + '].x'] = ANGULOS[a].compKm;
            patch['annotations[' + IDX_ANOTACAO_DIR1 + '].text'] = ANGULOS[a].dir1;
            Plotly.relayout(gd, patch);
            Plotly.animate(gd, [a + '_' + posMeio], {{
                mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}},
            }});
            atualizarEspessuras(a, posMeio);
        }}

        gd.on('plotly_buttonclicked', function(ev) {{
            if (typeof ev.active !== 'number') return;
            if (ev.active < ANGULOS.length) {{
                irParaAngulo(ev.active);
            }} else if (ev.active === ANGULOS.length + 2) {{
                aplicarTema('escuro');
            }} else if (ev.active === ANGULOS.length + 3) {{
                aplicarTema('claro');
            }}
            // botoes "Mapa: Hipsometria/Geologia" (ANGULOS.length, +1) usam
            // method='restyle' proprio, nao precisam de JS aqui.
        }});

        // slider arrastado direto (nao via botao/clique) tambem atualiza a
        // espessura -- setTimeout deixa o Plotly terminar de aplicar o novo
        // "active" antes de ler.
        gd.on('plotly_sliderchange', function() {{
            setTimeout(function() {{ atualizarEspessuras(anguloAtual, gd.layout.sliders[0].active); }}, 0);
        }});

        gd.on('plotly_click', function(data) {{
            var ponto = data.points[0];
            var ehMapa = ponto.curveNumber === 0 || (ponto.curveNumber >= {idx_geo_mapa_inicio} && ponto.curveNumber <= {idx_geo_mapa_fim});
            if (!ehMapa) return;  // so reage a clique no mapa (heatmap ou poligonos de geologia)
            var info = ANGULOS[anguloAtual];
            var t = (ponto.x - CX) * info.px + (ponto.y - CY) * info.py;
            var melhorIdx = 0, melhorDist = Infinity;
            for (var p = 0; p < info.t.length; p++) {{
                var d = Math.abs(info.t[p] - t);
                if (d < melhorDist) {{ melhorDist = d; melhorIdx = p; }}
            }}
            Plotly.relayout(gd, {{'sliders[0].active': melhorIdx}});
            Plotly.animate(gd, [anguloAtual + '_' + melhorIdx], {{
                mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}},
            }});
            atualizarEspessuras(anguloAtual, melhorIdx);
        }});
    }})();
    """

    fig.write_html(str(OUT_HTML), include_plotlyjs="inline", full_html=True, post_script=post_script)
    print(f"Salvo em: {OUT_HTML}")


if __name__ == "__main__":
    main()
