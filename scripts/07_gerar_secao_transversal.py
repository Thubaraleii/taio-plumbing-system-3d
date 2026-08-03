"""
Gera uma secao transversal 2D (perfil geologico, estilo "SECAO A-A'") ao
longo de uma linha reta -- terreno, 4 camadas sedimentares, deposito
quaternario, sill e dique, tudo em corte. Usa os mesmos dados/paleta
estilizados do "cubao" (blender/visualizacao_publico/), nao e o modelo
cientifico fino do GemPy.

Uso:
    python scripts/07_gerar_secao_transversal.py
    (edite PONTO_A / PONTO_B no topo pra mudar a linha de corte -- UTM,
    EPSG:31982, mesmas coordenadas do resto do projeto)
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
from shapely.geometry import Point

BASE = Path(__file__).parent.parent
TOPO_NPY = BASE / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
POLIGONO_REFERENCIA = BASE.parent / "2_Banco_de_Dados" / "dados_base" / "poligon_intrusiva.shp"
OUT_PATH = BASE / "exports" / "renders" / "secao_transversal.png"

# Linha de corte A-A' (UTM, EPSG:31982) -- ajuste aqui pra outra secao.
# Padrao: passa pelo centro do modelo, orientada W-E.
PONTO_A = (582500.0, 7012062.0)
PONTO_B = (604500.0, 7012062.0)
N_AMOSTRAS = 500

# 5 formacoes sedimentares REAIS (Bacia do Parana, Grupo Guata/Passa Dois),
# mais nova (topo) -> mais antiga (base). Espessuras da literatura (busca em
# 01/08/2026): Rio Bonito ate 269m (poco 1-BN-1-SC), Palermo ~100m
# (ESTIMATIVA -- nao confirmada, checar Loureiro 2024 ou tese de Alfredo
# Wagner/SC), Irati 40-70m (uso 55m), Serra Alta 52-100m na borda leste
# (uso 80m), Teresina 300-400m na borda leste (uso 350m). Mesmos valores de
# ../visualizacao_web/gerar_visualizador_3d.py / gerar_secao_interativa.py.
NOMES_CAMADAS = ["Teresina", "Serra Alta", "Irati", "Palermo", "Rio Bonito"]
CORES_CAMADAS = ["#D6C79A", "#8C8C86", "#3E362C", "#B5AE93", "#C9A66B"]
PROFUNDIDADE_CAMADAS = [0.0, 350.0, 430.0, 485.0, 585.0, 854.0]

# trend regional (mergulho ~0.85 graus, azimute ~106 graus/ESE) extraido dos
# contatos CPRM reais -- ver ../../2_Banco_de_Dados/scripts_etl/
# calcular_trend_regional_camadas.py. Mesmos valores dos visualizadores web.
TREND_A, TREND_B = 0.01034, -0.00025
TREND_X0, TREND_Y0 = 592300.0, 7015058.8
Z_REF_TILT = 1053.5  # ancora o plano em boundary(prof=350) = 703.5 (media real do contato Teresina/Serra Alta)
COR_SILL = "#A63D2F"
COR_DIQUE = "#1B4332"  # verde escuro
COR_QUATERNARIO = "#D9CB82"
ESPESSURA_SILL = 400.0
QUATERNARIO_LIMIAR = 450.0
QUATERNARIO_ESPESSURA = 30.0
BASE_Z_ABSOLUTA = -600.0  # piso rebaixado pra caber a espessura real das 5 formacoes


def main():
    xyz = np.load(TOPO_NPY)
    linear = LinearNDInterpolator(xyz[:, :2], xyz[:, 2])
    nearest = NearestNDInterpolator(xyz[:, :2], xyz[:, 2])

    def elevacao(x, y):
        z = linear(x, y)
        if np.isnan(z):
            z = nearest(x, y)
        return float(z)

    gdf = gpd.read_file(POLIGONO_REFERENCIA)
    sill_geom = gdf[gdf["tipo"] == "Soleira"].geometry.union_all()
    dique_geom = gdf[gdf["tipo"] == "Dique"].geometry.union_all()

    ax_, ay_ = PONTO_A
    bx_, by_ = PONTO_B
    dist_total = np.hypot(bx_ - ax_, by_ - ay_)
    ts = np.linspace(0, 1, N_AMOSTRAS)
    xs = ax_ + ts * (bx_ - ax_)
    ys = ay_ + ts * (by_ - ay_)
    dists = ts * dist_total

    print(f"Amostrando {N_AMOSTRAS} pontos ao longo de {dist_total:.0f}m...")
    terreno = np.array([elevacao(x, y) for x, y in zip(xs, ys)])
    dentro_sill = np.array([sill_geom.contains(Point(x, y)) for x, y in zip(xs, ys)])
    dentro_dique = np.array([dique_geom.contains(Point(x, y)) for x, y in zip(xs, ys)])

    fig, plot_ax = plt.subplots(figsize=(14, 6))

    # contato 0 = sempre o relevo real (Teresina afloraria sempre no seu
    # lugar); contatos > 0 sao planos inclinados, erodidos pelo relevo real
    # onde ficam acima dele (ver comentario equivalente em ../visualizacao_web/gerar_visualizador_3d.py).
    tilt = Z_REF_TILT + TREND_A * (xs - TREND_X0) + TREND_B * (ys - TREND_Y0)
    contatos = [terreno if m == 0 else np.minimum(tilt - PROFUNDIDADE_CAMADAS[m], terreno)
                for m in range(len(PROFUNDIDADE_CAMADAS))]
    for k in range(len(PROFUNDIDADE_CAMADAS) - 1):
        topo = contatos[k]
        base = contatos[k + 1]
        plot_ax.fill_between(dists / 1000, base, topo, color=CORES_CAMADAS[k], linewidth=0, zorder=1)

    mascara_quat = terreno <= QUATERNARIO_LIMIAR
    if mascara_quat.any():
        quat_topo = np.where(mascara_quat, terreno, np.nan)
        quat_base = np.where(mascara_quat, terreno - QUATERNARIO_ESPESSURA, np.nan)
        plot_ax.fill_between(dists / 1000, quat_base, quat_topo, color=COR_QUATERNARIO, linewidth=0, zorder=2, label="Depósito quaternário")

    if dentro_sill.any():
        sill_topo = np.where(dentro_sill, terreno, np.nan)
        sill_base = np.where(dentro_sill, terreno - ESPESSURA_SILL, np.nan)
        plot_ax.fill_between(dists / 1000, sill_base, sill_topo, color=COR_SILL, linewidth=0, zorder=3, label="Sill de diabásio")

    if dentro_dique.any():
        dique_topo = np.where(dentro_dique, terreno, np.nan)
        dique_base = np.where(dentro_dique, BASE_Z_ABSOLUTA, np.nan)
        plot_ax.fill_between(dists / 1000, dique_base, dique_topo, color=COR_DIQUE, linewidth=0, zorder=4, label="Dique de diabásio")

    plot_ax.plot(dists / 1000, terreno, color="black", linewidth=1.2, zorder=5)

    for i, nome in enumerate(NOMES_CAMADAS):
        plot_ax.fill_between([], [], color=CORES_CAMADAS[i], label=nome)  # so pra entrar na legenda

    plot_ax.set_xlabel("Distância ao longo da seção (km)")
    plot_ax.set_ylabel("Elevação (m)")
    plot_ax.set_title(f"Seção transversal A-A'  ({PONTO_A} → {PONTO_B})")
    plot_ax.set_xlim(0, dist_total / 1000)
    plot_ax.legend(loc="upper right", fontsize=8, ncol=2)
    plot_ax.grid(alpha=0.3)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUT_PATH, dpi=150)
    print(f"Salvo em: {OUT_PATH}")


if __name__ == "__main__":
    main()
