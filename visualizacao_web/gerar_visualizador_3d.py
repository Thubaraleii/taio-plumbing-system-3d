"""Gera o visualizador 3D interativo (HTML autonomo, Plotly) do "cubao"
estilizado -- topografia real + 5 formacoes sedimentares drapeadas + deposito
quaternario + sill/dique -- pra visualizacao publico/didatica, sem apego
cientifico (o modelo fino de verdade continua em exports/meshes/, gerado
pelo GemPy). Tem uma ferramenta de corte (2 eixos, Leste-Oeste e Norte-Sul,
com slider) que remove a parte do bloco alem do plano de corte, expondo a
sequencia estratigrafica internamente -- like "picture cutaway" 3D). Roda
offline, sem servidor -- so abrir o .html no navegador.

Uso:
    python visualizacao_web/gerar_visualizador_3d.py

Gera:
    visualizacao_web/viewer_3d_taio.html
"""
import base64
from pathlib import Path

import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
from scipy.interpolate import griddata, LinearNDInterpolator, NearestNDInterpolator
from scipy.spatial import Delaunay
from shapely.geometry import Point, box
from shapely.prepared import prep

BASE = Path(__file__).parent.parent
TOPO_NPY = BASE / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
SATELITE_CACHE_DIR = BASE / "dados_entrada" / "satelite_esri"
SATELITE_CACHE_NPY = SATELITE_CACHE_DIR / "satelite_utm.npy"
SATELITE_RESOLUCAO = 2000  # resolucao (pixels/eixo) do raster UTM cacheado -- so precisa cobrir
# bem a grade de render (RESOLUCAO_GRID_TOPO no web, RESOLUCAO no Blender), nao precisa exceder
# muito a resolucao real da imagem de satelite (o cache e compartilhado pelos dois pipelines).
SATELITE_ZOOM = 17  # nivel de zoom das tiles Esri World Imagery -- 17 = boa nitidez pro Blender
# (mesh mais fina, RESOLUCAO=500 em 04_exportar_topografia_para_blender.py); pro visualizador web
# (grade de corte bem mais grossa, 63x63) o zoom real quase nao importa, a grade que limita.
POLIGONO_INTRUSIVA = BASE.parent / "2_Banco_de_Dados" / "dados_base" / "poligon_intrusiva.shp"
POLIGONOS_CPRM_GEOJSON = (
    BASE.parent / "2_Banco_de_Dados" / "saida_processada" / "formacoes_cprm_poligonos.geojson"
)
PONTOS_CAMPO_GPKG = (
    BASE.parent / "2_Banco_de_Dados" / "Unificação" / "GPKG_Novos" / "pontos_unificados_completo.gpkg"
)
LOGO_PATH = Path(__file__).parent / "assets" / "logo_gstech.jpg"
OUT_HTML = Path(__file__).parent / "viewer_3d_taio.html"

# identidade visual GS Tech (marca do usuario, aplicada por cima do produto --
# nao mexe em nada do modelo/dados) -- mesma paleta usada em
# ../visualizacao_web/gerar_secao_interativa.py, manter as duas em sincronia.
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

RESOLUCAO_GRID_TOPO = 63  # pontos por eixo, so para o render (nao afeta o GemPy) -- baixado de 250, depois 110/95/80/75/70.
# Caiu mais quando a trace de satelite (Esri) foi adicionada -- ela duplica x/y/z/surfacecolor da
# grade (mais uma "topografia" inteira, por frame de corte), estourando o limite de 100MB de novo.
# Precisou cair mais quando a ferramenta de corte ganhou 4 modos (2 eixos x 2 direcoes, ver
# MODOS_CORTE) -- cada frame de corte carrega o estado inteiro (topografia+camadas+corpos+
# decalques), entao 4 modos x N_CORTE posicoes multiplica o arquivo rapido; sem baixar a
# resolucao/densidade dos decalques o HTML passava de 100MB (limite do GitHub sem LFS).
# pra 110 quando a ferramenta de corte (frames por posicao) fez o HTML passar de 400MB
EXAGERO_Z = 6.0  # fator de exagero vertical (relevo real e sutil frente a area horizontal)
BASE_Z_ABSOLUTA = -600.0  # piso do "cubao" -- mesma cota usada em ../scripts/06_gerar_solidos_estilizados_cubao.py
COR_SILL, COR_DIQUE = "#A63D2F", "#1B4332"  # paleta exata (dique = verde escuro)
ESPESSURA_SILL_ESTILIZADA = 400.0  # mesma de ../scripts/06_gerar_solidos_estilizados_cubao.py
PASSO_DENSIFICACAO = 40.0  # mesma de ../scripts/06_gerar_solidos_estilizados_cubao.py -- so
# pro CORPO SOLIDO do sill/dique (construir_solido), mantido fino de proposito: e o dado
# cientifico mais importante sempre visivel. NAO usar pro decalque (ver PASSO_DENSIFICACAO_DECAL).
PASSO_DENSIFICACAO_DECAL = 70.0  # contorno do decalque geologico (so cor/aparencia, nao a forma
# real do corpo) -- mais grosso que PASSO_DENSIFICACAO de proposito, e o maior custo restante
# por frame de corte (ver historico de reducao de tamanho no CLAUDE.md).
PASSO_INTERIOR_DECAL = 2100.0  # grade de pontos internos pros decalques geologicos (evita
# facetas gigantes/chapadas em poligonos grandes -- ver triangular_interior). Mesma ordem
# de grandeza da resolucao da grade da topografia, sem exagerar o numero de triangulos.

# ferramenta de corte: 2 eixos (Leste-Oeste corta em X, Norte-Sul corta em Y),
# cada um com N_CORTE posicoes indo de "quase tudo cortado" ate "sem corte"
# (posicao final = modelo inteiro, igual a versao sem corte). Reaproveita a
# grade regular da topografia -- cortar e so fatiar linhas/colunas, e como
# "paredes_caixa" ja desenha a sequencia estratigrafica inteira em qualquer
# borda da grade, a nova borda cortada vira automaticamente a face exposta
# (corte reto mostrando as camadas por dentro).
N_CORTE = 5  # baixado de 13 -> 9 -> 5 (10/08/2026) -- mesmo 9 posicoes (68,8MB) ainda dava 404
# no GitHub Pages, entao o limite real e bem menor que os 100MB do git; testando valores
# menores ate achar um tamanho que o Pages realmente sirva
J_MIN_CORTE = 12  # minimo de colunas/linhas mantidas (evita um bloco degenerado no extremo)

# 5 formacoes sedimentares REAIS (Bacia do Parana, Grupo Guata/Passa Dois),
# drapeadas no relevo (profundidade abaixo da superficie real, em metros --
# NAO cota absoluta), mais nova (topo) -> mais antiga (base). Espessuras da
# literatura (busca em 01/08/2026): Rio Bonito ate 269m (poco 1-BN-1-SC,
# Barra Nova/SC), Palermo ~100m (ESTIMATIVA -- nao confirmada, checar
# Loureiro 2024 ou tese de cartografia de Alfredo Wagner/SC), Irati 40-70m
# (uso 55m, membro Taquaral+Assistencia), Serra Alta 52-100m na borda leste
# (uso 80m, SC tende ao valor mais alto), Teresina 300-400m na borda leste
# (uso 350m -- bate com a regiao de Taio). Mesmos valores/cores do script
# bpy do Blender (../blender/visualizacao_publico/scripts_bpy/montar_cena_teste.py).
NOMES_CAMADAS = ["Teresina", "Serra Alta", "Irati", "Palermo", "Rio Bonito"]
CORES_CAMADAS = ["#D6C79A", "#8C8C86", "#3E362C", "#B5AE93", "#C9A66B"]
PROFUNDIDADE_CAMADAS = [0.0, 350.0, 430.0, 485.0, 585.0, 854.0]

# pontos de campo (catalogo unificado, ver PONTOS_CAMPO_GPKG) -- coloridos pela
# mesma paleta das formacoes/sill/dique quando a litologia_padronizada bate com
# uma delas; cinza neutro pro resto (encaixante generico/indefinido).
CORES_LITOLOGIA_CAMPO = {
    "sill_diabasio": COR_SILL, "sill_diabasio_cprm": COR_SILL,
    "dique": COR_DIQUE, "dique_cprm": COR_DIQUE,
    "encaixante_teresina": CORES_CAMADAS[0], "encaixante_serra_alta": CORES_CAMADAS[1],
    "encaixante_irati": CORES_CAMADAS[2], "encaixante_palermo": CORES_CAMADAS[3],
    "encaixante_rio_bonito": CORES_CAMADAS[4],
}
COR_LITOLOGIA_PADRAO = "#999999"  # encaixante_sedimentar generico / indefinido / outros

# trend regional: plano BRUTO ajustado direto aos pontos reais de contato
# Teresina/Serra Alta (CPRM, n=627 -- o contato mais denso em dado, ver
# ../../2_Banco_de_Dados/scripts_etl/calcular_trend_regional_camadas.py).
# Usamos o plano bruto (nao o residuo pos-remocao da tendencia do relevo --
# esse residuo, ~0.85 grau, e menor que a espessura da Teresina e nunca
# afloraria outra formacao) porque ele reproduz a elevacao REAL onde o
# contato aflora, que e exatamente o que decide onde a erosao expoe as
# formacoes mais antigas -- assume mergulho paralelo (mesma inclinacao)
# pros outros 3 contatos, que nao tem dado denso o bastante individualmente.
TREND_A, TREND_B = 0.01034, -0.00025
TREND_X0, TREND_Y0 = 592300.0, 7015058.8
Z_REF_TILT = 1053.5  # ancora o plano em boundary(prof=350) = 703.5 (media real do contato)

# deposito quaternario (aluviao de vale): usa a cota real do terreno como
# proxy -- so aparece onde o relevo fica abaixo do limiar (~10% mais baixo
# da area, coerente com fundo de vale). Mesmo limiar do script bpy do Blender.
QUATERNARIO_LIMIAR_REAL = 450.0
QUATERNARIO_ESPESSURA_REAL = 30.0
COR_QUATERNARIO = "#D9CB82"

# paleta hipsometrica customizada (baixo -> alto), mesma de
# ../scripts/04_exportar_topografia_para_blender.py
CORES_HIPSOMETRICAS = ["#A66A2C", "#C6924A", "#D8C88C", "#9FC1A3", "#4F9AA8"]
COLORSCALE_HIPSOMETRICO = [[i / (len(CORES_HIPSOMETRICAS) - 1), cor] for i, cor in enumerate(CORES_HIPSOMETRICAS)]

# mapa geologico REAL (CPRM) drapeado no terreno como "decalque" vetorial
# (poligono real triangulado + elevacao real em cada vertice, ver
# construir_decal_cortado) -- NAO mais uma classificacao por grade
# (surfacecolor): numa grade grosseira (110x110, baixada por causa do
# tamanho do arquivo) os poligonos ficavam pixelados e corpos finos como
# dique sumiam/ficavam "falhados" (a malha so pega uma amostra a cada
# ~200-300m, mais largo que muitos diques). O decalque usa o poligono real
# entao fica nitido em qualquer largura. Poligonos ja dissolvidos/recortados
# em ../../2_Banco_de_Dados/scripts_etl/exportar_poligonos_cprm.py. Mesma
# paleta das camadas (+ Serra Geral/aluviao/outros/sill+dique novos --
# K_TPS_SILL/K_TPS_DIQUE, mesma cor dos corpos solidos do cubao).
ORDEM_FORMACOES = NOMES_CAMADAS + [
    "Serra Geral (sill/dique)", "Aluvião quaternário", "K_TPS_SILL", "K_TPS_DIQUE", "Outros",
]
CORES_FORMACOES = CORES_CAMADAS + ["#A63D2F", "#D9CB82", COR_SILL, COR_DIQUE, "#CCCCCC"]
CORES_FORMACOES_MAPA = dict(zip(ORDEM_FORMACOES, CORES_FORMACOES))
OFFSET_DECAL_Z = 3.0  # decalque um pouco acima do terreno, evita z-fighting

N_CAMADAS = len(PROFUNDIDADE_CAMADAS) - 1
CHAVES_GEO = [f"geo_{nome}" for nome in ORDEM_FORMACOES]
# topografia (trace 0) + camadas + quaternario + sill/dique + decalques
# geologicos -- todos regenerados por estado de corte.
ORDEM_TRACES_RESTO = (
    [chave for k in range(N_CAMADAS) for chave in (f"camada_{k}_parede", f"camada_{k}_fundo")]
    + ["quaternario_topo", "quaternario_fundo", "sill", "dique"] + CHAVES_GEO + ["topografia_satelite"]
)


def paredes_caixa(grid_x, grid_y, grid_z_topo, grid_z_base):
    """Constroi as 4 paredes verticais do perimetro da grade, do topo
    (grid_z_topo) ate a base (grid_z_base) -- os dois podem ser uma grade
    cheia (drapeada, ex.: relevo) ou uma grade constante (np.full_like) pra
    uma cota plana. Quando a grade foi cortada (fatiada), a borda cortada
    tambem vira uma "parede" aqui -- e exatamente a face do corte."""
    lados = [
        (grid_x[0, :], grid_y[0, :], grid_z_topo[0, :], grid_z_base[0, :]),
        (grid_x[-1, :], grid_y[-1, :], grid_z_topo[-1, :], grid_z_base[-1, :]),
        (grid_x[:, 0], grid_y[:, 0], grid_z_topo[:, 0], grid_z_base[:, 0]),
        (grid_x[:, -1], grid_y[:, -1], grid_z_topo[:, -1], grid_z_base[:, -1]),
    ]
    todos_x, todos_y, todos_z, todos_i, todos_j, todos_k = [], [], [], [], [], []
    offset = 0
    for lx, ly, lz_topo, lz_base in lados:
        n = len(lx)
        xs = np.concatenate([lx, lx])
        ys = np.concatenate([ly, ly])
        zs = np.concatenate([lz_topo, lz_base])
        for idx in range(n - 1):
            t0, t1, b0, b1 = idx, idx + 1, idx + n, idx + n + 1
            todos_i += [offset + t0, offset + t1]
            todos_j += [offset + t1, offset + b1]
            todos_k += [offset + b0, offset + b0]
        todos_x.append(xs); todos_y.append(ys); todos_z.append(zs)
        offset += 2 * n
    return (
        np.concatenate(todos_x), np.concatenate(todos_y), np.concatenate(todos_z),
        np.array(todos_i), np.array(todos_j), np.array(todos_k),
    )


def montar_elevador(xyz):
    linear = LinearNDInterpolator(xyz[:, :2], xyz[:, 2])
    nearest = NearestNDInterpolator(xyz[:, :2], xyz[:, 2])

    def elevacao(x, y):
        z = linear(x, y)
        if np.isnan(z):
            z = nearest(x, y)
        return float(z)

    return elevacao


def obter_satelite_utm(xmin, ymin, xmax, ymax):
    """Busca (ou le do cache local) uma imagem de satelite Esri World Imagery
    cobrindo a extensao do modelo, ja reprojetada pra UTM (EPSG:31982) --
    PLACEHOLDER ate o usuario ter um ortomosaico proprio de drone (precisao
    ~1m). A busca+reprojecao demora cerca de 1 min (rede) -- cacheada em
    SATELITE_CACHE_NPY; apagar esse arquivo forca buscar de novo (ex.: se
    trocar de zoom ou quiser atualizar a imagem)."""
    if SATELITE_CACHE_NPY.exists():
        return np.load(SATELITE_CACHE_NPY)

    import contextily as ctx

    print("Baixando imagem de satelite Esri World Imagery (~1 min, sera cacheada)...")
    gdf = gpd.GeoDataFrame(geometry=[box(xmin, ymin, xmax, ymax)], crs="EPSG:31982")
    w, s, e, n = gdf.to_crs("EPSG:4326").total_bounds
    img, ext = ctx.bounds2img(
        w, s, e, n, ll=True, zoom=SATELITE_ZOOM, source=ctx.providers.Esri.WorldImagery, n_connections=8,
    )
    src_transform = from_bounds(ext[0], ext[2], ext[1], ext[3], img.shape[1], img.shape[0])
    dst_transform = from_bounds(xmin, ymin, xmax, ymax, SATELITE_RESOLUCAO, SATELITE_RESOLUCAO)
    dst = np.zeros((3, SATELITE_RESOLUCAO, SATELITE_RESOLUCAO), dtype=np.uint8)
    reproject(
        source=np.moveaxis(img[:, :, :3], -1, 0), destination=dst,
        src_transform=src_transform, src_crs="EPSG:3857",
        dst_transform=dst_transform, dst_crs="EPSG:31982",
        resampling=Resampling.bilinear,
    )
    SATELITE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(SATELITE_CACHE_NPY, dst)
    return dst


def amostrar_satelite_rgb(raster_rgb, grid_x, grid_y, xmin, ymin, xmax, ymax):
    """Amostra (nearest, o raster ja foi reamostrado bilinear na reprojecao)
    a cor RGB do raster de satelite em cada ponto (x,y) da grade de render."""
    _, h, w = raster_rgb.shape
    col = np.clip(((grid_x - xmin) / (xmax - xmin) * (w - 1)).astype(int), 0, w - 1)
    row = np.clip(((ymax - grid_y) / (ymax - ymin) * (h - 1)).astype(int), 0, h - 1)
    return raster_rgb[0, row, col], raster_rgb[1, row, col], raster_rgb[2, row, col]


def densificar_contorno(poligono, passo: float):
    linha = poligono.exterior
    comprimento = linha.length
    n = max(int(comprimento // passo), 3)
    return [linha.interpolate(d).coords[0][:2] for d in np.linspace(0, comprimento, n, endpoint=False)]


def triangular_interior(poligono, passo: float, passo_interior: float = None):
    """Triangula o interior do poligono. So os pontos do contorno (padrao)
    deixa poligonos grandes com poucos triangulos enormes e chapados (o
    Delaunay so tem os pontos da borda pra trabalhar) -- passo_interior
    adiciona uma grade de pontos por dentro tambem, pra o drapeado
    acompanhar o relevo de verdade em vez de "esticar" por cima."""
    contorno = densificar_contorno(poligono, passo)
    pontos_lista = list(contorno)
    if passo_interior:
        minx, miny, maxx, maxy = poligono.bounds
        mascara_pt = prep(poligono)
        xs_int = np.arange(minx + passo_interior / 2, maxx, passo_interior)
        ys_int = np.arange(miny + passo_interior / 2, maxy, passo_interior)
        for x in xs_int:
            for y in ys_int:
                if mascara_pt.contains(Point(x, y)):
                    pontos_lista.append((x, y))
    pontos = np.array(pontos_lista)
    delaunay = Delaunay(pontos)
    mascara = prep(poligono)
    triangulos = [s for s in delaunay.simplices if mascara.contains(Point(pontos[s].mean(axis=0)))]
    return pontos, np.array(triangulos)


def construir_solido(poligono, elevacao_fn, espessura=None, base_absoluta=None):
    """Extrude um poligono num solido fechado (topo drapeado no relevo real +
    base plana/absoluta + paredes no perimetro) -- mesma logica de
    ../scripts/06_gerar_solidos_estilizados_cubao.py. Usada tanto pro corpo
    inteiro (extensao ampla, sem recorte) quanto por estado de corte (poligono
    ja recortado pelo plano) -- como o perimetro do poligono recortado inclui
    a nova borda reta do corte, a parede ali vira a face do corte exposta."""
    pontos_xy, triangulos_topo = triangular_interior(poligono, PASSO_DENSIFICACAO)
    if len(triangulos_topo) == 0:
        vazio = np.zeros((0, 3))
        return vazio, np.zeros((0, 3), dtype=int)
    n = len(pontos_xy)

    z_topo = np.array([elevacao_fn(x, y) for x, y in pontos_xy])
    z_base = z_topo - espessura if espessura is not None else np.full(n, base_absoluta)

    vertices = np.vstack([np.column_stack([pontos_xy, z_topo]), np.column_stack([pontos_xy, z_base])])
    faces = list(triangulos_topo) + [(f[0] + n, f[2] + n, f[1] + n) for f in triangulos_topo]
    for i in range(n):
        a, b = i, (i + 1) % n
        faces.append((a, b, b + n))
        faces.append((a, b + n, a + n))
    return vertices, np.array(faces)


def construir_corpo_cortado(gdf_corpo, elevacao_fn, eixo, valor_corte, bbox_amplo, invertido=False, **kwargs):
    """Recorta cada poligono do corpo (sill/dique, pode ter varios lobos) pelo
    semiplano do corte (mantem X<=valor ou Y<=valor, ou o lado oposto se
    invertido=True) e extrude cada pedaco resultante -- ao contrario de so
    filtrar triangulos de uma malha fixa, isso gera uma parede de verdade na
    aresta do corte (corpo aparece solido/preenchido no corte, nao vazado)."""
    xmin_a, ymin_a, xmax_a, ymax_a = bbox_amplo
    if eixo == "x":
        caixa = box(valor_corte, ymin_a, xmax_a, ymax_a) if invertido else box(xmin_a, ymin_a, valor_corte, ymax_a)
    else:
        caixa = box(xmin_a, valor_corte, xmax_a, ymax_a) if invertido else box(xmin_a, ymin_a, xmax_a, valor_corte)

    todos_v, todos_f = [], []
    offset = 0
    for geom in gdf_corpo.geometry:
        recorte = geom.intersection(caixa)
        if recorte.is_empty:
            continue
        partes = recorte.geoms if hasattr(recorte, "geoms") else [recorte]
        for parte in partes:
            if parte.geom_type != "Polygon" or parte.area < 1.0:
                continue
            v, f = construir_solido(parte, elevacao_fn, **kwargs)
            if len(v) == 0:
                continue
            todos_v.append(v)
            todos_f.append(f + offset)
            offset += len(v)

    if not todos_v:
        vazio = np.zeros((0, 3))
        return dict(x=vazio[:, 0], y=vazio[:, 1], z=vazio[:, 2], i=[], j=[], k=[])
    vertices = np.vstack(todos_v)
    faces = np.vstack(todos_f)
    return dict(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], i=faces[:, 0], j=faces[:, 1], k=faces[:, 2])


def construir_decal_plano(poligono, elevacao_fn):
    """So o topo (sem base/paredes) drapeado no relevo real, um pouco acima
    (OFFSET_DECAL_Z) pra nao dar z-fighting com a topografia -- "decalque"
    vetorial do mapa geologico real, nao uma amostragem em grade (ver
    comentario em ORDEM_FORMACOES)."""
    pontos_xy, triangulos = triangular_interior(poligono, PASSO_DENSIFICACAO_DECAL, PASSO_INTERIOR_DECAL)
    if len(triangulos) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), dtype=int)
    z = np.array([elevacao_fn(x, y) for x, y in pontos_xy]) + OFFSET_DECAL_Z
    return np.column_stack([pontos_xy, z]), triangulos


def construir_decal_cortado(geoms, elevacao_fn, eixo, valor_corte, bbox_amplo, invertido=False):
    """Mesmo recorte por semiplano de construir_corpo_cortado, mas so o topo
    (decalque plano) -- usado pros poligonos do mapa geologico real."""
    xmin_a, ymin_a, xmax_a, ymax_a = bbox_amplo
    if eixo == "x":
        caixa = box(valor_corte, ymin_a, xmax_a, ymax_a) if invertido else box(xmin_a, ymin_a, valor_corte, ymax_a)
    else:
        caixa = box(xmin_a, valor_corte, xmax_a, ymax_a) if invertido else box(xmin_a, ymin_a, xmax_a, valor_corte)

    todos_v, todos_f = [], []
    offset = 0
    for geom in geoms:
        recorte = geom.intersection(caixa)
        if recorte.is_empty:
            continue
        partes = recorte.geoms if hasattr(recorte, "geoms") else [recorte]
        for parte in partes:
            if parte.geom_type != "Polygon" or parte.area < 1.0:
                continue
            v, f = construir_decal_plano(parte, elevacao_fn)
            if len(v) == 0:
                continue
            todos_v.append(v)
            todos_f.append(f + offset)
            offset += len(v)

    if not todos_v:
        vazio = np.zeros((0, 3))
        return dict(x=vazio[:, 0], y=vazio[:, 1], z=vazio[:, 2], i=[], j=[], k=[])
    vertices = np.vstack(todos_v)
    faces = np.vstack(todos_f)
    return dict(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], i=faces[:, 0], j=faces[:, 1], k=faces[:, 2])


def montar_estado(eixo, j, invertido, grid_x, grid_y, grid_z, grid_contatos, topo_quat, fundo_quat,
                   xs, ys, gdf_sill, gdf_dique, elevacao_fn, bbox_amplo,
                   formacoes_geoms, zmin_hipso, zmax_hipso, idx_satelite):
    """Monta os dados (x,y,z / i,j,k) de todas as traces pra um estado de
    corte -- eixo='x' corta em X, eixo='y' corta em Y; invertido troca qual
    lado fica visivel (mantem X<=valor normal / X>=valor invertido, e o
    equivalente em Y); j = numero de colunas/linhas da grade mantidas."""
    if eixo == "x":
        if invertido:
            cortar = lambda g: g[:, -j:]
            valor_corte = xs[-j]
        else:
            cortar = lambda g: g[:, :j]
            valor_corte = xs[j - 1]
    else:
        if invertido:
            cortar = lambda g: g[-j:, :]
            valor_corte = ys[-j]
        else:
            cortar = lambda g: g[:j, :]
            valor_corte = ys[j - 1]

    gx, gy, gz = cortar(grid_x), cortar(grid_y), cortar(grid_z)
    dados = {
        "topografia": dict(
            x=gx, y=gy, z=gz, surfacecolor=gz,
            colorscale=COLORSCALE_HIPSOMETRICO, cmin=zmin_hipso, cmax=zmax_hipso,
        ),
    }

    for k in range(N_CAMADAS):
        gtopo, gbase = cortar(grid_contatos[k]), cortar(grid_contatos[k + 1])
        px, py, pz, pi, pj, pk = paredes_caixa(gx, gy, gtopo, gbase)
        dados[f"camada_{k}_parede"] = dict(x=px, y=py, z=pz, i=pi, j=pj, k=pk)
        dados[f"camada_{k}_fundo"] = dict(x=gx, y=gy, z=gbase)

    dados["quaternario_topo"] = dict(x=gx, y=gy, z=cortar(topo_quat))
    dados["quaternario_fundo"] = dict(x=gx, y=gy, z=cortar(fundo_quat))

    dados["sill"] = construir_corpo_cortado(gdf_sill, elevacao_fn, eixo, valor_corte, bbox_amplo,
                                              invertido=invertido, espessura=ESPESSURA_SILL_ESTILIZADA)
    dados["dique"] = construir_corpo_cortado(gdf_dique, elevacao_fn, eixo, valor_corte, bbox_amplo,
                                               invertido=invertido, base_absoluta=BASE_Z_ABSOLUTA)

    for nome in ORDEM_FORMACOES:
        dados[f"geo_{nome}"] = construir_decal_cortado(
            formacoes_geoms.get(nome, []), elevacao_fn, eixo, valor_corte, bbox_amplo, invertido=invertido)

    # sem colorscale/cmin/cmax aqui de proposito -- isso e fixo (definido uma unica vez no
    # fig.add_trace() inicial) e MUITO grande (um stop por vertice da grade, ver main()); repetir
    # em cada frame inflaria o HTML absurdamente pra nada, ja que essas props nao mudam com o corte.
    dados["topografia_satelite"] = dict(x=gx, y=gy, z=gz, surfacecolor=cortar(idx_satelite))
    return dados


def trace_de_tipo(chave, payload):
    if chave.endswith("_parede") or chave in ("sill", "dique") or chave.startswith("geo_"):
        return go.Mesh3d(**payload)
    return go.Surface(**payload)


def main():
    xyz = np.load(TOPO_NPY)
    print(f"Topografia: {xyz.shape[0]} pontos")

    xmin, xmax = xyz[:, 0].min(), xyz[:, 0].max()
    ymin, ymax = xyz[:, 1].min(), xyz[:, 1].max()
    xs = np.linspace(xmin, xmax, RESOLUCAO_GRID_TOPO)
    ys = np.linspace(ymin, ymax, RESOLUCAO_GRID_TOPO)
    grid_x, grid_y = np.meshgrid(xs, ys)
    grid_z = griddata(xyz[:, :2], xyz[:, 2], (grid_x, grid_y), method="linear")
    # preenche buracos (fora do casco convexo dos pontos) com nearest
    grid_z_nearest = griddata(xyz[:, :2], xyz[:, 2], (grid_x, grid_y), method="nearest")
    grid_z = np.where(np.isnan(grid_z), grid_z_nearest, grid_z)

    # contato 0 (topo do pacote) e SEMPRE o proprio relevo real -- nada
    # mapeado por cima da Teresina, entao onde ela existe e sempre ela que
    # aflora. Os contatos de subsuperficie (indice > 0) sao planos
    # inclinados (mergulho regional); o relevo real "erode" o pacote onde
    # o contato calculado fica acima da superficie -- a formacao rasa ali ja
    # foi erodida, expondo a de baixo (por isso outras formacoes tambem
    # afloram em certas areas, nao so a Teresina).
    grid_tilt = Z_REF_TILT + TREND_A * (grid_x - TREND_X0) + TREND_B * (grid_y - TREND_Y0)
    grid_contatos = [grid_z if m == 0 else np.minimum(grid_tilt - PROFUNDIDADE_CAMADAS[m], grid_z)
                      for m in range(len(PROFUNDIDADE_CAMADAS))]

    # topo do quaternario um pouco ACIMA do decalque geologico (OFFSET_DECAL_Z)
    # -- senao o decalque (desenhado por cima na hipotese antiga) tampava o
    # quaternario quando o modo "Geologia" tava ligado (os dois sao superficies
    # solidas na mesma posicao XY; sem esse desnivel, o Z-buffer decide por
    # cima quem fica em cima e nem sempre e o quaternario).
    OFFSET_QUATERNARIO_Z = OFFSET_DECAL_Z + 2.0
    mascara_quat = grid_z <= QUATERNARIO_LIMIAR_REAL
    topo_quat = np.where(mascara_quat, grid_z + OFFSET_QUATERNARIO_Z, np.nan)
    fundo_quat = np.where(mascara_quat, grid_z - QUATERNARIO_ESPESSURA_REAL, np.nan)

    gdf_intrusiva = gpd.read_file(POLIGONO_INTRUSIVA)
    gdf_sill = gdf_intrusiva[gdf_intrusiva["tipo"] == "Soleira"]
    gdf_dique = gdf_intrusiva[gdf_intrusiva["tipo"] == "Dique"]
    print(f"sill: {len(gdf_sill)} lobos, dique: {len(gdf_dique)} corpos (poligonos reais, ver poligon_intrusiva.shp)")
    elevacao_fn = montar_elevador(xyz)
    margem = 2000.0
    bbox_amplo = (xmin - margem, ymin - margem, xmax + margem, ymax + margem)

    gdf_formacoes = gpd.read_file(POLIGONOS_CPRM_GEOJSON)
    formacoes_geoms = {row.formacao: [row.geometry] for row in gdf_formacoes.itertuples()}
    print(f"Mapa geologico real: {len(gdf_formacoes)} formacoes ({', '.join(formacoes_geoms)})")
    zmin_hipso, zmax_hipso = float(grid_z.min()), float(grid_z.max())

    # satelite Esri (placeholder ate ter ortomosaico proprio, ver obter_satelite_utm) -- amostrado
    # na mesma grade da topografia. Pra simular textura fotografica numa Surface do Plotly (que so
    # aceita surfacecolor mapeada por colorscale, nao textura de imagem de verdade), cada vertice
    # vira um indice numa colorscale com um "stop" por cor -- MAS o renderizador WebGL (gl-surface3d)
    # tem um limite duro de 256 "shades" na colorscale (testado: uma cor por vertice, 3969 cores
    # numa grade 63x63, deu erro "map requires nshades to be at least size 3969" e a trace nao
    # renderizava nada). Solucao: reduzir a PALETA de cores pra no maximo 256 (quantizacao, estilo
    # GIF/paleta indexada) via Pillow, mantendo a resolucao espacial da grade cheia -- varios
    # vertices proximos passam a compartilhar a cor mais parecida da paleta, mas a malha continua
    # inteira (nao afeta a nitidez espacial, so a variedade de cores).
    from PIL import Image
    raster_satelite = obter_satelite_utm(xmin, ymin, xmax, ymax)
    r_sat, g_sat, b_sat = amostrar_satelite_rgb(raster_satelite, grid_x, grid_y, xmin, ymin, xmax, ymax)
    img_rgb = np.stack([r_sat, g_sat, b_sat], axis=-1).astype(np.uint8)
    img_quant = Image.fromarray(img_rgb, mode="RGB").quantize(colors=256, method=Image.MEDIANCUT)
    paleta = np.array(img_quant.getpalette()[:256 * 3]).reshape(-1, 3)
    n_cores_paleta = len(paleta)
    idx_satelite = np.array(img_quant, dtype=np.float64) / (n_cores_paleta - 1)
    colorscale_satelite = [
        [k / (n_cores_paleta - 1), f"rgb({r},{g},{b})"] for k, (r, g, b) in enumerate(paleta)
    ]

    def montar(eixo, j, invertido=False):
        return montar_estado(eixo, j, invertido, grid_x, grid_y, grid_z, grid_contatos, topo_quat, fundo_quat,
                              xs, ys, gdf_sill, gdf_dique, elevacao_fn, bbox_amplo,
                              formacoes_geoms, zmin_hipso, zmax_hipso, idx_satelite)

    j_vals = np.linspace(J_MIN_CORTE, RESOLUCAO_GRID_TOPO, N_CORTE).astype(int)
    estado_inicial = montar("x", j_vals[-1])  # sem corte (igual a versao original)

    fig = go.Figure()

    OPACIDADE_INICIAL_TOPO = 1.0
    OPACIDADE_MIN_OP = 3  # piso do slider = 0.3 (abaixo disso a superficie "some" contra o fundo escuro)
    fig.add_trace(go.Surface(
        **estado_inicial["topografia"],
        opacity=OPACIDADE_INICIAL_TOPO, showscale=True,
        colorbar=dict(title=dict(text="Elevação (m)", font=dict(color=MARCA_CINZA_CLARO)), x=1.0,
                       tickfont=dict(color=MARCA_CINZA_CLARO)),
        name="Topografia (curvas de nível)",
    ))

    # 5 formacoes drapeadas no relevo -- so paredes (perimetro) + tampa de
    # fundo, tampas de topo foram testadas e descartadas (ver historico:
    # tampa de topo duplicava o terreno, tampa de fundo vazava pela
    # transparencia e lavava a cor).
    for k in range(N_CAMADAS):
        grupo = f"camada_{k}"
        fig.add_trace(go.Mesh3d(
            **estado_inicial[f"camada_{k}_parede"],
            color=CORES_CAMADAS[k], opacity=0.95, name=NOMES_CAMADAS[k],
            flatshading=True, showlegend=True, legendgroup=grupo, legendrank=4 + k,
        ))
        fig.add_trace(go.Surface(
            **estado_inicial[f"camada_{k}_fundo"],
            colorscale=[[0, CORES_CAMADAS[k]], [1, CORES_CAMADAS[k]]], showscale=False,
            opacity=0.95, name=f"{NOMES_CAMADAS[k]} (fundo)", showlegend=False, legendgroup=grupo,
        ))

    # deposito quaternario: veneer fino, so onde o relevo real fica abaixo do
    # limiar (fundo de vale). NaN nas celulas fora da mascara -- o Plotly
    # simplesmente deixa essas celulas sem desenhar (vira um "buraco" na
    # superficie, exatamente o efeito de mascara que queremos).
    colorscale_quat = [[0, COR_QUATERNARIO], [1, COR_QUATERNARIO]]
    fig.add_trace(go.Surface(
        **estado_inicial["quaternario_topo"], colorscale=colorscale_quat, showscale=False,
        opacity=1.0, name="Depósito quaternário", showlegend=True, legendgroup="quaternario", legendrank=1,
    ))
    fig.add_trace(go.Surface(
        **estado_inicial["quaternario_fundo"], colorscale=colorscale_quat, showscale=False,
        legendgroup="quaternario",
        opacity=1.0, name="Depósito quaternário (fundo)", showlegend=False,
    ))

    for i, (chave, nome, cor) in enumerate((("sill", "Soleira", COR_SILL), ("dique", "Dique", COR_DIQUE))):
        fig.add_trace(go.Mesh3d(
            **estado_inicial[chave],
            color=cor, opacity=1.0, name=nome, showlegend=True, legendrank=2 + i,
            flatshading=True,
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.2),
        ))

    # decalques do mapa geologico real -- comecam invisiveis (modo padrao =
    # hipsometria), o botao "Cor: Geologia" so troca visible=True/False
    # (sem precisar de restyle de colorscale/frame hack: sao traces
    # separadas da topografia, nao um surfacecolor nela).
    for nome in ORDEM_FORMACOES:
        fig.add_trace(go.Mesh3d(
            **estado_inicial[f"geo_{nome}"],
            color=CORES_FORMACOES_MAPA[nome], opacity=1.0, name=nome, showlegend=False,
            visible=False, flatshading=False,
            lighting=dict(ambient=0.9, diffuse=0.3, specular=0.0),
        ))

    # satelite Esri -- colorscale/cmin/cmax fixos aqui (unica vez, NAO repetidos por frame, ver
    # nota em montar_estado). Comeca invisivel, terceiro modo do botao Hipsometria/Geologia/Satelite.
    fig.add_trace(go.Surface(
        **estado_inicial["topografia_satelite"],
        colorscale=colorscale_satelite, cmin=0, cmax=1, showscale=False,
        opacity=1.0, name="Satélite (Esri, provisório)", showlegend=False, visible=False,
    ))

    # seta do norte -- trace 3D fixa (nao entra na lista de indices dos frames
    # de corte, entao nao muda com a posicao/direcao do corte). Aponta +Y
    # (norte real em UTM), gira junto com a camera ao orbitar a cena (ao
    # contrario de um overlay 2D fixo na tela, que nao indicaria norte de
    # verdade numa cena 3D que o usuario pode rotacionar livremente).
    # Fica FORA da extensao real do modelo nos 3 eixos (X, Y E Z ganham
    # margem extra so pra caber ela) -- ha um lobo do sill bem no canto
    # nordeste real dos dados, entao so afastar em X (ou so elevar em Z) nao
    # bastava, ainda ficava "colada" nele em varios angulos de camera. Afasta
    # em X, afasta em Y (passa do proprio ymax, nao só encosta nele) E eleva
    # em Z ao mesmo tempo.
    comprimento_seta = (ymax - ymin) * 0.07
    margem_seta_x = (xmax - xmin) * 0.18
    seta_x = xmax + margem_seta_x * 0.75
    margem_seta_y = (ymax - ymin) * 0.05
    seta_y1 = ymax + margem_seta_y * 0.6
    seta_y0 = seta_y1 - comprimento_seta
    margem_seta_z = (grid_z.max() - grid_z.min()) * 0.25
    seta_z = grid_z.max() + margem_seta_z
    fig.add_trace(go.Scatter3d(
        x=[seta_x, seta_x], y=[seta_y0, seta_y1], z=[seta_z, seta_z],
        mode="lines", line=dict(color=MARCA_ROXO, width=7),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Cone(
        x=[seta_x], y=[seta_y1], z=[seta_z], u=[0], v=[comprimento_seta * 0.5], w=[0],
        anchor="tip", sizemode="absolute", sizeref=comprimento_seta * 0.4,
        colorscale=[[0, MARCA_ROXO], [1, MARCA_ROXO]], showscale=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[seta_x], y=[seta_y1 + comprimento_seta * 0.2], z=[seta_z],
        mode="text", text=["N"], textfont=dict(size=18, color=MARCA_ROXO, family=MARCA_FONTE),
        showlegend=False, hoverinfo="skip",
    ))

    # pontos de campo (catalogo unificado, 308 pontos reais medidos em campo) --
    # trace 3D fixa (nao clipada pela ferramenta de corte, igual seta/satelite),
    # colorida por litologia_padronizada, popup no hover com dados da tabela de
    # atributos. Comeca invisivel, toggle proprio.
    idx_pontos_campo = len(fig.data)
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
        fig.add_trace(go.Scatter3d(
            x=gdf_campo.geometry.x, y=gdf_campo.geometry.y, z=gdf_campo["Z_m"],
            mode="markers", marker=dict(size=4, color=cores_campo, line=dict(color=MARCA_CINZA_CLARO, width=0.5)),
            text=hover_campo, hoverinfo="text",
            name="Pontos de Campo", showlegend=False, visible=False,
        ))

    idx_geo_inicio = 1 + len(ORDEM_TRACES_RESTO) - len(CHAVES_GEO) - 1  # indice da 1a trace de decalque
    idx_satelite_trace = 1 + len(ORDEM_TRACES_RESTO) - 1  # ultimo item de ORDEM_TRACES_RESTO

    # 4 modos de corte: eixo x/y, cada um normal (mantem lado "menor") ou
    # invertido (mantem lado "maior") -- deixa escolher de qual lado o corte
    # "entra" (Leste-Oeste/Oeste-Leste, Norte-Sul/Sul-Norte).
    MODOS_CORTE = [("x", False, "x"), ("x", True, "xinv"), ("y", False, "y"), ("y", True, "yinv")]
    print(f"Pre-calculando ferramenta de corte: {len(MODOS_CORTE)} modos x {N_CORTE} posicoes...")
    n_traces_total = 1 + len(ORDEM_TRACES_RESTO)
    frames = []
    for eixo, invertido, modo in MODOS_CORTE:
        for p, j in enumerate(j_vals):
            estado = montar(eixo, j, invertido)
            dados_frame = [go.Surface(**estado["topografia"])] + [
                trace_de_tipo(chave, estado[chave]) for chave in ORDEM_TRACES_RESTO
            ]
            frames.append(go.Frame(data=dados_frame, name=f"{modo}_{p}", traces=list(range(n_traces_total))))
    fig.frames = frames

    # zaxis com folga extra no topo (margem_seta_z) so pra caber a seta do norte, elevada
    # acima do relevo de proposito (ver comentario acima).
    zmin, zmax = grid_z.min() - max(PROFUNDIDADE_CAMADAS), grid_z.max() + margem_seta_z
    eixo_3d = dict(
        gridcolor="#3D3560", zerolinecolor="#3D3560", showbackground=True,
        backgroundcolor=MARCA_NAVY, color=MARCA_CINZA_CLARO,
    )
    fig.update_layout(
        title=dict(
            text="<b>Modelo 3D Taió Plumbing System</b>",
            font=dict(family=MARCA_FONTE, size=26, color=MARCA_CINZA_CLARO),
            x=0.03, xanchor="left",
        ),
        paper_bgcolor=MARCA_NAVY,
        font=dict(family=MARCA_FONTE, color=MARCA_CINZA_CLARO),
        scene=dict(
            # xaxis/yaxis com folga extra a nordeste (margem_seta_x/y) so pra caber a seta
            # do norte, que fica fora da extensao real do modelo de proposito (ver comentario acima).
            xaxis=dict(title="X (UTM)", range=[xmin, xmax + margem_seta_x], **eixo_3d),
            yaxis=dict(title="Y (UTM)", range=[ymin, ymax + margem_seta_y], **eixo_3d),
            zaxis=dict(title="Z (m)", range=[zmin, zmax], **eixo_3d),
            aspectmode="manual",
            aspectratio=dict(
                x=1,
                y=(ymax - ymin) / (xmax - xmin),
                z=EXAGERO_Z * (grid_z.max() - grid_z.min()) / (xmax - xmin),
            ),
        ),
        legend=dict(x=0.02, y=0.98, bgcolor="rgba(45,10,74,0.75)", bordercolor=MARCA_ROXO, borderwidth=1,
                    font=dict(color=MARCA_CINZA_CLARO)),
        margin=dict(l=0, r=0, t=90, b=80),
        height=900,
        updatemenus=[
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.98, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[dict(label="Sólido: ON", method="skip"), dict(label="Sólido: OFF", method="skip")],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.88, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[dict(label="Leste-Oeste", method="skip"), dict(label="Oeste-Leste", method="skip")],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.78, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[dict(label="Norte-Sul", method="skip"), dict(label="Sul-Norte", method="skip")],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.68, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[
                    dict(label="Hipsometria", method="restyle",
                         args=[{"visible": [True] + [False] * len(CHAVES_GEO) + [False]},
                               [0] + list(range(idx_geo_inicio, idx_geo_inicio + len(CHAVES_GEO))) + [idx_satelite_trace]]),
                    dict(label="Geologia", method="restyle",
                         args=[{"visible": [False] + [True] * len(CHAVES_GEO) + [False]},
                               [0] + list(range(idx_geo_inicio, idx_geo_inicio + len(CHAVES_GEO))) + [idx_satelite_trace]]),
                    dict(label="Satélite", method="restyle",
                         args=[{"visible": [False] + [False] * len(CHAVES_GEO) + [True]},
                               [0] + list(range(idx_geo_inicio, idx_geo_inicio + len(CHAVES_GEO))) + [idx_satelite_trace]]),
                ],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.58, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[dict(label="Tema: Escuro", method="skip"), dict(label="Tema: Claro", method="skip")],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.48, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[
                    dict(label="Topografia: ON", method="restyle", args=[{"visible": True}, [0]]),
                    dict(label="Topografia: OFF", method="restyle", args=[{"visible": False}, [0]]),
                ],
            ),
            dict(
                type="buttons", direction="left", showactive=False,
                x=0.98, y=0.38, xanchor="right", yanchor="top",
                bgcolor=MARCA_ROXO_ESCURO, bordercolor=MARCA_ROXO, borderwidth=1.5,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                buttons=[
                    dict(label="Pontos de Campo: ON", method="restyle",
                         args=[{"visible": True}, [idx_pontos_campo]]),
                    dict(label="Pontos de Campo: OFF", method="restyle",
                         args=[{"visible": False}, [idx_pontos_campo]]),
                ],
            ),
        ],
        sliders=[
            dict(
                active=round(OPACIDADE_INICIAL_TOPO * 10) - OPACIDADE_MIN_OP,
                currentvalue=dict(prefix="Opacidade: ", xanchor="left", font=dict(color=MARCA_CINZA_CLARO)),
                pad=dict(t=30, b=10),
                x=0.02, y=0.0, len=0.4, xanchor="left",
                bgcolor=MARCA_ROXO_ESCURO, activebgcolor=MARCA_ROXO, bordercolor=MARCA_ROXO,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                steps=[
                    # opacidade aplica na topografia (trace 0) E nos decalques de
                    # geologia juntos -- so o que estiver visivel (hipsometria OU
                    # geologia) responde de verdade, mas assim funciona nos dois
                    # modos sem precisar rastrear qual ta ativo. Piso em
                    # OPACIDADE_MIN_OP (nao 0.1) -- superficie 3D translucida contra
                    # o fundo escuro "some" visualmente em opacidades muito baixas
                    # (blend quase invisivel), entao o slider nunca deixa passar
                    # disso.
                    dict(
                        method="restyle",
                        args=[{"opacity": op / 10},
                              [0] + list(range(idx_geo_inicio, idx_geo_inicio + len(CHAVES_GEO))) + [idx_satelite_trace]],
                        label=f"{op / 10:.1f}",
                    )
                    for op in range(OPACIDADE_MIN_OP, 11)
                ],
            ),
            dict(
                active=N_CORTE - 1,
                currentvalue=dict(prefix="Corte (Leste-Oeste) em X: ", xanchor="left", font=dict(color=MARCA_CINZA_CLARO)),
                pad=dict(t=30, b=10),
                x=0.55, y=0.0, len=0.4, xanchor="left",
                bgcolor=MARCA_ROXO_ESCURO, activebgcolor=MARCA_ROXO, bordercolor=MARCA_ROXO,
                font=dict(color=MARCA_CINZA_CLARO, family=MARCA_FONTE),
                steps=[
                    dict(
                        method="animate",
                        args=[[f"x_{p}"], dict(mode="immediate", frame=dict(duration=0, redraw=True), transition=dict(duration=0))],
                        label=f"{xs[j - 1]:.0f}",
                    )
                    for p, j in enumerate(j_vals)
                ],
            ),
        ],
    )

    eixos_js = ",\n        ".join(
        "{nome:'%s', prefixo:'%s', valores:[%s]}" % (
            modo, prefixo,
            ",".join(f"{v:.1f}" for v in valores),
        )
        for modo, prefixo, valores in [
            ("x", "Corte (Leste-Oeste) em X: ", [xs[j - 1] for j in j_vals]),
            ("xinv", "Corte (Oeste-Leste) em X: ", [xs[-j] for j in j_vals]),
            ("y", "Corte (Norte-Sul) em Y: ", [ys[j - 1] for j in j_vals]),
            ("yinv", "Corte (Sul-Norte) em Y: ", [ys[-j] for j in j_vals]),
        ]
    )
    indices_solido = [0] + list(range(1, 1 + 2 * N_CAMADAS))  # topografia + paredes/fundos das camadas
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
        var N_CORTE = {N_CORTE};
        var EIXOS = [
        {eixos_js}
        ];
        var INDICES_SOLIDO = {indices_solido};
        var eixoAtual = 0;
        var gd = document.getElementsByClassName('plotly-graph-div')[0];

        function stepsParaEixo(e) {{
            var info = EIXOS[e];
            var steps = [];
            for (var p = 0; p < N_CORTE; p++) {{
                steps.push({{
                    method: 'animate',
                    args: [[info.nome + '_' + p], {{mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}}}}],
                    label: info.valores[p].toFixed(0),
                }});
            }}
            return steps;
        }}

        function irParaEixo(e) {{
            eixoAtual = e;
            var posFinal = N_CORTE - 1;  // sem corte ao trocar de eixo
            Plotly.relayout(gd, {{
                'sliders[1].steps': stepsParaEixo(e),
                'sliders[1].active': posFinal,
                'sliders[1].currentvalue.prefix': EIXOS[e].prefixo,
            }});
            Plotly.animate(gd, [EIXOS[e].nome + '_' + posFinal], {{
                mode: 'immediate', frame: {{duration: 0, redraw: true}}, transition: {{duration: 0}},
            }});
        }}

        // "Solido": forca opacidade 1.0 na topografia + camadas (que normalmente
        // ficam <1 pra dar transparencia) -- ajuda a ver o contato entre
        // unidades no corte sem a transparencia atrapalhando. OFF restaura a
        // opacidade da topografia pro valor do slider de opacidade atual.
        function irParaSolido(ativado) {{
            if (ativado) {{
                Plotly.restyle(gd, {{opacity: 1.0}}, INDICES_SOLIDO);
            }} else {{
                var step = gd.layout.sliders[0].steps[gd.layout.sliders[0].active];
                Plotly.restyle(gd, {{opacity: step.args[0].opacity}}, [0]);
                Plotly.restyle(gd, {{opacity: 0.95}}, INDICES_SOLIDO.slice(1));
            }}
        }}

        // tema claro/escuro -- cores dos corpos/camadas/decalques sao
        // proprias (nao mudam), so a "moldura" (fundo, eixos 3d, legenda,
        // botoes, slider, colorbar) muda.
        var TEMA = {{
            escuro: {{
                paper: '{MARCA_NAVY}', sceneBg: '{MARCA_NAVY}', texto: '{MARCA_CINZA_CLARO}',
                grid: '#3D3560', legendBg: 'rgba(45,10,74,0.75)', botaoBg: '{MARCA_ROXO_ESCURO}',
            }},
            claro: {{
                paper: '{MARCA_CINZA_CLARO}', sceneBg: '#FFFFFF', texto: '{MARCA_NAVY}',
                grid: '#D0D0D8', legendBg: 'rgba(255,255,255,0.85)', botaoBg: '#EDE3FF',
            }},
        }};

        function aplicarTema(nome) {{
            var t = TEMA[nome];
            var patch = {{
                paper_bgcolor: t.paper,
                'font.color': t.texto,
                'title.font.color': t.texto,
                'legend.bgcolor': t.legendBg, 'legend.font.color': t.texto,
            }};
            ['xaxis', 'yaxis', 'zaxis'].forEach(function(eixo) {{
                patch['scene.' + eixo + '.backgroundcolor'] = t.sceneBg;
                patch['scene.' + eixo + '.gridcolor'] = t.grid;
                patch['scene.' + eixo + '.zerolinecolor'] = t.grid;
                patch['scene.' + eixo + '.color'] = t.texto;
            }});
            for (var m = 0; m < 7; m++) {{
                patch['updatemenus[' + m + '].bgcolor'] = t.botaoBg;
                patch['updatemenus[' + m + '].font.color'] = t.texto;
            }}
            for (var s = 0; s < 2; s++) {{
                patch['sliders[' + s + '].bgcolor'] = t.botaoBg;
                patch['sliders[' + s + '].font.color'] = t.texto;
                patch['sliders[' + s + '].currentvalue.font.color'] = t.texto;
            }}
            Plotly.relayout(gd, patch);
            Plotly.restyle(gd, {{'colorbar.tickfont.color': t.texto, 'colorbar.title.font.color': t.texto}}, [0]);
            document.body.style.background = t.paper;
        }}

        // 6 menus separados agora (Solido / Corte-X / Corte-Y / Cor / Tema /
        // Topografia), cada um so com o proprio par de botoes -- roteia pela
        // posicao do menu (y), ja que ev.active sempre vem 0 ou 1 dentro de
        // cada par. Cor (Hipsometria/Geologia) e Topografia (ON/OFF) usam
        // method='restyle' nativo, nao precisam de rota aqui.
        gd.on('plotly_buttonclicked', function(ev) {{
            if (typeof ev.active !== 'number' || !ev.menu) return;
            if (Math.abs(ev.menu.y - 0.98) < 0.001) {{
                irParaSolido(ev.active === 0);
            }} else if (Math.abs(ev.menu.y - 0.88) < 0.001) {{
                irParaEixo(ev.active);  // 0=Leste-Oeste, 1=Oeste-Leste
            }} else if (Math.abs(ev.menu.y - 0.78) < 0.001) {{
                irParaEixo(2 + ev.active);  // 2=Norte-Sul, 3=Sul-Norte
            }} else if (Math.abs(ev.menu.y - 0.58) < 0.001) {{
                aplicarTema(ev.active === 0 ? 'escuro' : 'claro');
            }}
        }});
    }})();
    """

    fig.write_html(str(OUT_HTML), include_plotlyjs="inline", full_html=True, post_script=post_script)
    favicon_tags = (
        '<link rel="icon" type="image/png" href="assets/favicon.png">'
        '<link rel="shortcut icon" href="assets/favicon.ico">'
        '<link rel="apple-touch-icon" href="assets/apple-touch-icon.png">'
    )
    html_txt = OUT_HTML.read_text(encoding="utf-8")
    html_txt = html_txt.replace('<head><meta charset="utf-8" /></head>', f'<head><meta charset="utf-8" />{favicon_tags}</head>', 1)
    OUT_HTML.write_text(html_txt, encoding="utf-8")
    print(f"\nSalvo em: {OUT_HTML}")


if __name__ == "__main__":
    main()
