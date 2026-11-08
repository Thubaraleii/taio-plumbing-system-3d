"""Modelo 3D geral de Taio (HTML autonomo, Plotly) -- bloco SOLIDO e conectado, sem sobreposicao de superficies:
relevo real (drone) + mapa geologico em decalques exatos colados no relevo + empilhamento sedimentar nas paredes e
no chao do bloco + soleira/dique em volume (apagando o sedimentar) + faces de corte calculadas no navegador
(corte em X ou Y, 4 direcoes) + pontos de campo, geoquimica, falhas/fraturas (CPRM e de campo) e lineamentos.

Usa os dados/constantes de gerar_visualizador_3d.py (mesma pasta). Sem frames de corte -- o arquivo fica pequeno.

Uso:  python gerar_modelo_3d.py   ->  viewer_3d_taio.html
"""
import base64
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from rasterio import features
from rasterio.transform import from_bounds
from scipy.interpolate import RegularGridInterpolator, griddata
from shapely.geometry import box

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import gerar_visualizador_3d as v  # noqa: E402  (dados, paleta, construtores de solido)

BANCO = v.PONTOS_CAMPO_GPKG.parent.parent.parent
LINEAMENTOS_GPKG = BANCO / "Unificação" / "lineamentos_direcoes.gpkg"
GEOLOGIA_REGIONAL_GPKG = BANCO / "dados_base" / "geologia_regional_sc.gpkg"
ESTRUTURAL_GPKG = BANCO / "Unificação" / "GPKG_Novos" / "nuvem_pontos_direcoes.gpkg"
POCOS_GPKG = BANCO / "Unificação" / "pocos_regionais.gpkg"
OUT_HTML = AQUI / "viewer_3d_taio.html"

N_GRADE = 300          # vertices no eixo maior do relevo (~110 m)
RES_RASTER_M = 25.0    # raster geologico usado nas faces de corte
BASE_DIQUE_Z = -350.0
OFFSET_DEC = {"Depósito quaternário": 4.0, "Soleira": 5.0, "Dique": 6.0}  # decalques em camadas (corpos por cima)
OFFSET_BASE = 3.0
ELEV_LINHA, ELEV_PONTO = 14.0, 22.0
AZUL_FALHA, ROSA_FRATURA = "#2563EB", "#D81B73"
COR_LINEAMENTO = {"Positivo": "#2E7D5B", "Negativo": "#E8A33D"}
PRIORIDADE = ["Teresina", "Serra Alta", "Irati", "Palermo", "Rio Bonito", "Depósito quaternário", "Soleira", "Dique"]
COR_FORMACAO = dict(zip(v.ORDEM_FORMACOES, v.CORES_FORMACOES))
EXAGERO_PADRAO = 6


def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def triangulos_grade(ny, nx):
    idx = np.arange(ny * nx).reshape(ny, nx)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    return np.concatenate([a, b]), np.concatenate([b, d]), np.concatenate([c, c])


def main():
    print("Carregando dados...")
    xyz = np.load(v.TOPO_NPY)
    sat_bbox = (xyz[:, 0].min(), xyz[:, 1].min(), xyz[:, 0].max(), xyz[:, 1].max())
    sat = v.obter_satelite_utm(*sat_bbox)
    lito = gpd.read_file(v.LITOLOGIA_ATUALIZADA).to_crs(31982)
    lineas = gpd.read_file(LINEAMENTOS_GPKG).to_crs(31982)
    pontos = gpd.read_file(v.PONTOS_CAMPO_GPKG).to_crs(31982)
    est_cprm = gpd.read_file(GEOLOGIA_REGIONAL_GPKG, layer="estrutura") if GEOLOGIA_REGIONAL_GPKG.exists() else None
    est_campo = None
    if ESTRUTURAL_GPKG.exists():
        est_campo = gpd.read_file(ESTRUTURAL_GPKG).to_crs(31982)
        est_campo = est_campo[est_campo["classificacao"].isin(["falha_ou_dique_ambiguo_relevo_negativo", "fratura_falha"])]
    pocos = gpd.read_file(POCOS_GPKG).to_crs(31982) if POCOS_GPKG.exists() else None

    x0, y0, x1, y1 = sat_bbox
    bbox = sat_bbox
    dx, dy = x1 - x0, y1 - y0
    nx, ny = (N_GRADE, max(int(N_GRADE * dy / dx), 20)) if dx >= dy else (max(int(N_GRADE * dx / dy), 20), N_GRADE)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    gx, gy = np.meshgrid(xs, ys)
    gz = griddata(xyz[:, :2], xyz[:, 2], (gx, gy), method="linear")
    gz = np.where(np.isnan(gz), griddata(xyz[:, :2], xyz[:, 2], (gx, gy), method="nearest"), gz)
    interp = RegularGridInterpolator((ys, xs), gz, bounds_error=False, fill_value=None)

    def elev(x, y):
        """Elevacao coerente com a malha renderizada -- tudo (decalques, corpos, linhas) assenta na mesma superficie."""
        return float(interp((y, x)))

    def elev_v(px, py):
        return interp(np.column_stack([np.asarray(py, float), np.asarray(px, float)]))

    ti, tj, tk = triangulos_grade(ny, nx)
    base_xy = dict(x=np.round(gx.ravel(), 1), y=np.round(gy.ravel(), 1), z=np.round(gz.ravel(), 1), i=ti, j=tj, k=tk)
    nos = np.column_stack([gx.ravel(), gy.ravel()])
    janela = box(*bbox)
    fig = go.Figure()

    # ---- relevo (uma malha; cor por vertice trocada em JS: hipsometria / satelite) ----
    sr, sg, sb = v.amostrar_satelite_rgb(sat, gx, gy, *sat_bbox)
    cor_sat = np.column_stack([sr.ravel(), sg.ravel(), sb.ravel()]).astype(np.uint8)
    zn = (gz.ravel() - gz.min()) / max(np.ptp(gz), 1.0)
    paleta_h = np.array([hex_rgb(c) for c in v.CORES_HIPSOMETRICAS])
    pos = zn * (len(paleta_h) - 1)
    lo = np.floor(pos).astype(int).clip(0, len(paleta_h) - 2)
    fr = (pos - lo)[:, None]
    cor_hip = (paleta_h[lo] * (1 - fr) + paleta_h[lo + 1] * fr).astype(np.uint8)
    fig.add_trace(go.Mesh3d(**base_xy, vertexcolor=cor_hip, name="terreno", showlegend=False, hoverinfo="skip",
                            lighting=dict(ambient=0.7, diffuse=0.6, specular=0.05), flatshading=False, meta="terreno"))

    # ---- mapa geologico: decalques exatos (contatos finos) colados no relevo ----
    print("Decalques geologicos...")
    for nome_f in PRIORIDADE:
        vs, fs, off_v = [], [], 0
        for g in lito.loc[lito["formacao"] == nome_f, "geometry"]:
            inter = g.intersection(janela)
            for parte in ([inter] if inter.geom_type == "Polygon" else list(getattr(inter, "geoms", []))):
                if parte.geom_type != "Polygon" or parte.area < 150:
                    continue
                pxy, tri = v.triangular_interior(parte, 20.0, None, nos)
                if len(tri) == 0:
                    continue
                zz = elev_v(pxy[:, 0], pxy[:, 1]) + OFFSET_DEC.get(nome_f, OFFSET_BASE)
                vs.append(np.column_stack([pxy, zz])); fs.append(tri + off_v); off_v += len(pxy)
        if vs:
            vv, ff = np.vstack(vs), np.vstack(fs)
            fig.add_trace(go.Mesh3d(x=np.round(vv[:, 0], 1), y=np.round(vv[:, 1], 1), z=np.round(vv[:, 2], 1), i=ff[:, 0], j=ff[:, 1], k=ff[:, 2],
                                    color=COR_FORMACAO[nome_f], flatshading=False, showlegend=False, hoverinfo="skip", name=nome_f, meta="geo",
                                    lighting=dict(ambient=0.9, diffuse=0.3, specular=0.0)))

    # ---- raster geologico (indices em PRIORIDADE) -> mascara de soleira/dique e faces de corte ----
    w_r, h_r = int(dx / RES_RASTER_M), int(dy / RES_RASTER_M)
    shapes = [(g, k + 1) for k, nome in enumerate(PRIORIDADE) for g in lito.loc[lito["formacao"] == nome, "geometry"] if not g.is_empty]
    r_fine = features.rasterize(shapes, out_shape=(h_r, w_r), transform=from_bounds(x0, y0, x1, y1, w_r, h_r), fill=0, dtype="uint8")
    col = np.clip(((gx - x0) / dx * (w_r - 1)).astype(int), 0, w_r - 1)
    row = np.clip(((y1 - gy) / dy * (h_r - 1)).astype(int), 0, h_r - 1)
    form = r_fine[row, col]

    # ---- bloco: paredes (empilhamento), chao e placeholders das faces de corte ----
    tilt = v.Z_REF_TILT + v.TREND_A * (gx - v.TREND_X0) + v.TREND_B * (gy - v.TREND_Y0)
    contatos = [gz if m == 0 else np.minimum(tilt - v.PROFUNDIDADE_CAMADAS[m], gz) for m in range(len(v.PROFUNDIDADE_CAMADAS))]
    contatos_orig = [c.copy() for c in contatos]
    m_sill = form == PRIORIDADE.index("Soleira") + 1
    m_dique = form == PRIORIDADE.index("Dique") + 1
    base_sill_g = np.minimum(contatos[1], gz - v.ESPESSURA_MINIMA_SILL)
    contatos = [np.where(m_dique, gz, np.where(m_sill, np.minimum(c, base_sill_g), c)) for c in contatos]
    ri = np.unique(np.append(np.arange(0, ny, 3), ny - 1)); ci = np.unique(np.append(np.arange(0, nx, 3), nx - 1))
    sub = np.ix_(ri, ci)
    for k, nome in enumerate(v.NOMES_CAMADAS):
        px, py, pz, pi, pj, pk = v.paredes_caixa(gx[sub], gy[sub], contatos[k][sub], contatos[k + 1][sub])
        fig.add_trace(go.Mesh3d(x=np.round(px, 1), y=np.round(py, 1), z=np.round(pz, 1), i=pi, j=pj, k=pk, color=v.CORES_CAMADAS[k],
                                flatshading=False, name=nome, legendgroup=nome, showlegend=True, hoverinfo="name",
                                lighting=dict(ambient=0.95, diffuse=0.1, specular=0.0, roughness=1.0)))
    zmin_bloco = float(np.nanmin(contatos_orig[-1]))
    fig.add_trace(go.Mesh3d(x=np.round(gx.ravel(), 1), y=np.round(gy.ravel(), 1), z=np.round(contatos_orig[-1].ravel(), 1), i=ti, j=tj, k=tk,
                            color=v.CORES_CAMADAS[-1], flatshading=False, showlegend=False, hoverinfo="skip", meta="chao",
                            lighting=dict(ambient=0.95, diffuse=0.1, specular=0.0)))
    for k_cap, (n_cap, c_cap) in enumerate(zip(list(v.NOMES_CAMADAS) + ["Soleira", "Dique"], list(v.CORES_CAMADAS) + [v.COR_SILL, v.COR_DIQUE])):
        fig.add_trace(go.Mesh3d(x=[0, 0, 0], y=[0, 0, 0], z=[0, 0, 0], i=[0], j=[1], k=[2], color=c_cap, flatshading=False, showlegend=False,
                                hoverinfo="name", name=n_cap, visible=False, meta=f"cap_{k_cap}",
                                lighting=dict(ambient=0.95, diffuse=0.1, specular=0.0)))

    # ---- soleiras e diques em volume ----
    print("Soleiras e diques...")
    for nome, cor, kw in (("Soleira", v.COR_SILL, dict(base_fn=lambda x, y: v.elevacao_serra_alta(x, y, elev), espessura_minima=v.ESPESSURA_MINIMA_SILL, nos=nos)),
                          ("Dique", v.COR_DIQUE, dict(base_absoluta=BASE_DIQUE_Z))):
        vs, fs, off_v = [], [], 0
        for g in lito.loc[lito["formacao"] == nome, "geometry"]:
            inter = g.intersection(janela)
            for p in ([inter] if inter.geom_type == "Polygon" else list(getattr(inter, "geoms", []))):
                if p.geom_type != "Polygon" or p.area < 400:
                    continue
                vert, faces = v.construir_solido(p, elev, **kw)
                if len(faces) == 0:
                    continue
                vs.append(vert); fs.append(faces + off_v); off_v += len(vert)
        if vs:
            vv, ff = np.vstack(vs), np.vstack(fs)
            fig.add_trace(go.Mesh3d(x=np.round(vv[:, 0], 1), y=np.round(vv[:, 1], 1), z=np.round(vv[:, 2], 1), i=ff[:, 0], j=ff[:, 1], k=ff[:, 2],
                                    color=cor, flatshading=True, name=nome, legendgroup=nome, showlegend=True, hoverinfo="name",
                                    lighting=dict(ambient=0.7, diffuse=0.55)))

    # ---- camadas de pontos e linhas ----
    def linhas_draped(geoms, passo, extra, min_len=20):
        ex, ey, ez = [], [], []
        for g in geoms:
            inter = g.intersection(janela)
            for seg in ([inter] if inter.geom_type == "LineString" else list(getattr(inter, "geoms", []))):
                if seg.geom_type != "LineString" or seg.length < min_len:
                    continue
                pts = [seg.interpolate(d) for d in np.linspace(0, seg.length, max(int(seg.length // passo), 2))]
                px, py = [q.x for q in pts], [q.y for q in pts]
                ex += px + [None]; ey += py + [None]; ez += list(elev_v(px, py) + extra) + [None]
        return ex, ey, ez

    for tipo, cor in COR_LINEAMENTO.items():
        ex, ey, ez = linhas_draped(lineas.loc[lineas["tipo"] == tipo, "geometry"], 100, ELEV_LINHA, 30)
        if ex:
            fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="lines", line=dict(color=cor, width=5), name=f"Lineamento {tipo.lower()}",
                                       legendgroup="lin", meta="lin_pos" if tipo == "Positivo" else "lin_neg", hoverinfo="name"))
    if est_cprm is not None:
        for categoria, cor, larg in (("Falha", AZUL_FALHA, 6), ("Fratura", ROSA_FRATURA, 4)):
            ex, ey, ez = linhas_draped(est_cprm.loc[est_cprm["categoria"] == categoria, "geometry"], 100, ELEV_LINHA, 30)
            if ex:
                fig.add_trace(go.Scatter3d(x=ex, y=ey, z=ez, mode="lines", line=dict(color=cor, width=larg), name=f"{categoria} (CPRM)",
                                           legendgroup="estr", meta=f"est_{categoria.lower()}", hoverinfo="name"))
    if est_campo is not None and len(est_campo):
        ec = est_campo[est_campo.geometry.within(janela)]
        fig.add_trace(go.Scatter3d(
            x=ec.geometry.x, y=ec.geometry.y, z=elev_v(ec.geometry.x, ec.geometry.y) + ELEV_PONTO, mode="markers",
            marker=dict(size=4, symbol="x", color="#000000", line=dict(color="#FFFFFF", width=1)),
            text=[f"<b>{r.ponto_id}</b><br>{r.classificacao}<br>Azimute: {r.azimute_ou_strike_deg:.0f}°" for r in ec.itertuples()],
            hoverinfo="text", name="Falha de campo", legendgroup="estr", meta="est_campo"))
        lx, ly, lz = [], [], []
        for r in ec.itertuples():
            if r.azimute_ou_strike_deg != r.azimute_ou_strike_deg:
                continue
            ux, uy = np.sin(np.radians(r.azimute_ou_strike_deg)), np.cos(np.radians(r.azimute_ou_strike_deg))
            fs_ = np.linspace(-250, 250, 8)
            px, py = r.geometry.x + fs_ * ux, r.geometry.y + fs_ * uy
            lx += list(px) + [None]; ly += list(py) + [None]; lz += list(elev_v(px, py) + ELEV_LINHA) + [None]
        fig.add_trace(go.Scatter3d(x=lx, y=ly, z=lz, mode="lines", line=dict(color="#000000", width=3), name="Falha de campo (rumo)",
                                   legendgroup="estr", meta="est_campo", hoverinfo="name"))

    dentro = pontos[pontos.geometry.within(janela)]
    n_campo = len(dentro)
    fig.add_trace(go.Scatter3d(
        x=dentro.geometry.x, y=dentro.geometry.y, z=elev_v(dentro.geometry.x, dentro.geometry.y) + ELEV_PONTO, mode="markers",
        marker=dict(size=4, color=[v.CORES_LITOLOGIA_CAMPO.get(l, v.COR_LITOLOGIA_PADRAO) for l in dentro["litologia_padronizada"]],
                    line=dict(width=1, color="#F1F5F9")),
        text=[f"<b>{r.nome_itc}</b> ({r.ponto_id})<br>Litologia: {r.litologia_padronizada}<br>Tipo: {r.tipo_ponto}<br>Z: {r.Z_m:.0f} m"
              for r in dentro.itertuples()], hoverinfo="text", name="Pontos de campo", meta="campo"))

    if v.GEOQUIMICA_CSV.exists():
        dg = pd.read_csv(v.GEOQUIMICA_CSV)
        coord = {r.ponto_id: (r.geometry.x, r.geometry.y) for r in pontos.itertuples()}
        for i, r in dg.iterrows():
            if pd.isna(r["utm_e"]) and pd.notna(r["ponto_id"]) and r["ponto_id"] in coord:
                dg.loc[i, "utm_e"], dg.loc[i, "utm_n"] = coord[r["ponto_id"]]
        dg = dg.dropna(subset=["utm_e", "utm_n"])
        fig.add_trace(go.Scatter3d(
            x=dg["utm_e"], y=dg["utm_n"], z=elev_v(dg["utm_e"], dg["utm_n"]) + ELEV_PONTO + 6, mode="markers",
            marker=dict(size=6, symbol="diamond", color=[v.COR_TI_ALTO if t == "Alto-Ti" else v.COR_TI_BAIXO for t in dg["classificacao_ti"]],
                        line=dict(width=1, color="#F1F5F9")),
            text=[f"<b>{r.amostra}</b> ({r.classificacao_ti})<br>{r.origem}<br>TiO₂ {r.TiO2:.2f}% · SiO₂ {r.SiO2:.1f}%" for r in dg.itertuples()],
            hoverinfo="text", name="Geoquímica (Alto/Baixo-Ti)", meta="geoq"))

    if pocos is not None:
        pd_ = pocos[pocos.geometry.within(janela)]
        if len(pd_):
            fig.add_trace(go.Scatter3d(x=pd_.geometry.x, y=pd_.geometry.y, z=elev_v(pd_.geometry.x, pd_.geometry.y) + 5, mode="markers+text",
                                       marker=dict(size=6, symbol="diamond", color="#FFFFFF"), text=pd_["nome"], hoverinfo="text", name="Poços", meta="pocos"))

    # seta do norte (fora do bloco)
    ax_, ay0, ay1 = x1 + 0.03 * dx, y1 - 0.12 * dy, y1 - 0.03 * dy
    zmax = float(np.nanmax(gz)) + 60
    zmin = max(zmin_bloco, -450.0)
    fig.add_trace(go.Scatter3d(x=[ax_, ax_], y=[ay0, ay1], z=[zmax - 20, zmax - 20], mode="lines+text", text=["", "N"], textposition="top center",
                               textfont=dict(size=16, color=v.MARCA_ROXO), line=dict(color=v.MARCA_ROXO, width=6), showlegend=False,
                               hoverinfo="skip", meta="norte"))

    fig.update_layout(
        paper_bgcolor=v.MARCA_NAVY, font=dict(family=v.MARCA_FONTE, color=v.MARCA_CINZA_CLARO), margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(bgcolor="rgba(12,41,69,0.8)", bordercolor=v.MARCA_ROXO, borderwidth=1, x=0.01, y=0.99),
        scene=dict(
            xaxis=dict(title="X (UTM)", range=[x0 - 0.03 * dx, x1 + 0.06 * dx], backgroundcolor="#0C2945", gridcolor="#2A4663", color=v.MARCA_CINZA_CLARO),
            yaxis=dict(title="Y (UTM)", range=[y0 - 0.03 * dy, y1 + 0.03 * dy], backgroundcolor="#0C2945", gridcolor="#2A4663", color=v.MARCA_CINZA_CLARO),
            zaxis=dict(title="Z (m)", range=[zmin - 40, zmax + 60], backgroundcolor="#0C2945", gridcolor="#2A4663", color=v.MARCA_CINZA_CLARO),
            aspectmode="manual", aspectratio=dict(x=1.09, y=1.06 * dy / dx, z=(zmax - zmin + 100) * 3.0 / dx),
            camera=dict(eye=dict(x=-1.25, y=-1.45, z=0.95)),
        ),
    )
    cap = dict(
        x0=x0, y0=y0, x1=x1, y1=y1, nx=int(nx), ny=int(ny), terr=np.round(gz.ravel(), 1).tolist(),
        con=[np.round(c.ravel(), 1).tolist() for c in contatos_orig],
        rw=int(r_fine.shape[1]), rh=int(r_fine.shape[0]), raster=base64.b64encode(r_fine.astype(np.uint8).tobytes()).decode(),
        idx_sill=PRIORIDADE.index("Soleira") + 1, idx_dique=PRIORIDADE.index("Dique") + 1,
        esp_sill=v.ESPESSURA_MINIMA_SILL, base_dique=BASE_DIQUE_Z,
        hip=base64.b64encode(cor_hip.tobytes()).decode(), sat=base64.b64encode(cor_sat.tobytes()).decode(),
    )
    info = f"{dx * dy / 1e6:.0f} km² · {n_campo} pontos de campo · relevo {gz.min():.0f}–{gz.max():.0f} m"

    logo_path = Path(v.LOGO_PATH)
    mime = "jpeg" if logo_path.suffix.lower() in (".jpg", ".jpeg") else "png"
    logo = base64.b64encode(logo_path.read_bytes()).decode() if logo_path.exists() else ""
    html = f"""<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Modelo 3D — Taió Plumbing System</title>
<link rel="icon" type="image/png" href="assets/favicon.png?v=2"><link rel="shortcut icon" href="assets/favicon.ico?v=2">
<link rel="apple-touch-icon" href="assets/apple-touch-icon.png?v=2">
<style>
 :root {{ --bg:{v.MARCA_NAVY}; --painel:{v.MARCA_ROXO_ESCURO}; --txt:{v.MARCA_CINZA_CLARO}; --ac:{v.MARCA_ROXO}; --btn:{v.MARCA_NAVY}; }}
 * {{ box-sizing:border-box; }}
 body {{ margin:0; background:var(--bg); color:var(--txt); font-family:{v.MARCA_FONTE}; overflow:hidden; }}
 #barra {{ display:flex; flex-wrap:wrap; gap:6px 14px; align-items:center; padding:8px 70px 8px 14px; background:var(--painel); border-bottom:2px solid var(--ac); }}
 #barra h1 {{ font-size:15px; margin:0 8px 0 0; }} #barra h1 b {{ color:var(--ac); }}
 .grupo {{ display:flex; gap:5px; align-items:center; font-size:12px; }}
 .grupo label {{ opacity:.7; text-transform:uppercase; font-size:10px; letter-spacing:.06em; }}
 button, select {{ background:var(--btn); color:var(--txt); border:1px solid var(--ac); border-radius:5px; padding:4px 9px; font:inherit; font-size:12px; cursor:pointer; }}
 button.ativo {{ background:var(--ac); color:var(--bg); }}
 input[type=range] {{ accent-color:var(--ac); }}
 #info {{ margin-left:auto; font-size:11px; opacity:.75; }}
 #logo {{ position:fixed; top:8px; right:12px; width:46px; height:46px; border-radius:50%; border:2px solid var(--ac); z-index:5; }}
 #plot {{ width:100%; }}
</style></head><body>
<img id="logo" src="data:image/{mime};base64,{logo}">
<div id="barra"><h1><b>Modelo 3D</b> — Taió Plumbing System</h1>
 <div class="grupo"><label>Corte</label><button class="cz" data-e="x" data-i="0">Leste → Oeste</button><button class="cz" data-e="x" data-i="1">Oeste → Leste</button><button class="cz" data-e="y" data-i="0">Norte → Sul</button><button class="cz" data-e="y" data-i="1">Sul → Norte</button><button class="cz" data-e="">Sem corte</button><button id="anim">Animar corte</button>
  <input type="range" id="cpos" min="4" max="100" value="100" style="width:110px"></div>
 <div class="grupo"><label>Cor</label><button class="tex ativo" data-t="tex_hipsometria">Hipsometria</button><button class="tex" data-t="tex_geologia">Geologia</button><button class="tex" data-t="tex_satelite">Satélite</button>
  <label>Opacidade</label><input type="range" id="op" min="30" max="100" value="100" style="width:80px"></div>
 <div class="grupo"><label>Camadas</label><button class="cam ativo" data-m="terreno">Topografia</button><button class="cam" data-m="campo">Campo</button><button class="cam" data-m="geoq">Geoquímica</button><button class="cam" data-m="pocos">Poços</button></div>
 <div class="grupo"><label>Estruturas</label><button class="cam" data-m="est_falha">Falha CPRM</button><button class="cam" data-m="est_fratura">Fratura CPRM</button><button class="cam" data-m="est_campo">Falha de campo</button><button class="cam" data-m="lin_pos">Lineam. (+)</button><button class="cam" data-m="lin_neg">Lineam. (−)</button></div>
 <div class="grupo"><label>Vista</label><button id="giro">Girar</button><select id="exag"><option value="1">1×</option><option value="3">3×</option><option value="6" selected>6× (padrão)</option><option value="10">10×</option></select></div>
 <div class="grupo"><label>Tema</label><button class="tema ativo" data-t="escuro">Escuro</button><button class="tema" data-t="claro">Claro</button></div>
 <div id="info">{info}</div></div>
<div id="plot"></div>
<script>{get_plotlyjs()}</script>
<script>
var FIG = {fig.to_json()}, CAP = {json.dumps(cap)};
var gd = document.getElementById('plot');
var textura = 'tex_hipsometria', EXAG = {EXAGERO_PADRAO}, OP = 1, camadasOn = {{terreno: true, campo: false, geoq: false, pocos: false,
  est_falha: false, est_fratura: false, est_campo: false, lin_pos: false, lin_neg: false}};
var CORTE = {{eixo: 'x', inv: false, frac: 1}}, CORES = {{}}, anim = null, giroT = null, ang = Math.atan2(-1.45, -1.25), RAIO = Math.sqrt(1.25 * 1.25 + 1.45 * 1.45);
function altura() {{ return window.innerHeight - document.getElementById('barra').offsetHeight; }}
function b64u8(s) {{ var b = atob(s), a = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) a[i] = b.charCodeAt(i); return a; }}
CAP.rast = b64u8(CAP.raster);
function coresTerreno(tipo) {{
  if (!CORES[tipo]) {{ var u = b64u8(CAP[tipo]), a = []; for (var i = 0; i < u.length; i += 3) a.push([u[i], u[i + 1], u[i + 2]]); CORES[tipo] = a; }}
  return CORES[tipo];
}}
function bil(arr, x, y) {{
  var d = CAP, fx = (x - d.x0) / (d.x1 - d.x0) * (d.nx - 1), fy = (y - d.y0) / (d.y1 - d.y0) * (d.ny - 1);
  fx = Math.min(Math.max(fx, 0), d.nx - 1.001); fy = Math.min(Math.max(fy, 0), d.ny - 1.001);
  var i = Math.floor(fx), j = Math.floor(fy), tx = fx - i, ty = fy - j;
  function g(a, b) {{ return arr[b * d.nx + a]; }}
  return (g(i, j) * (1 - tx) + g(i + 1, j) * tx) * (1 - ty) + (g(i, j + 1) * (1 - tx) + g(i + 1, j + 1) * tx) * ty;
}}
function formAt(x, y) {{
  var d = CAP, col = Math.min(Math.max(Math.round((x - d.x0) / (d.x1 - d.x0) * (d.rw - 1)), 0), d.rw - 1);
  var row = Math.min(Math.max(Math.round((d.y1 - y) / (d.y1 - d.y0) * (d.rh - 1)), 0), d.rh - 1);
  return d.rast[row * d.rw + col];
}}
// face do corte: empilhamento (soleira/dique "apagam" o sedimentar) ao longo do plano de corte
function montarCaps(eixo, pos) {{
  var d = CAP, ns = 480, tops = [], bots = [], X = [], Y = [], u, k, i;
  for (u = 0; u < 7; u++) {{ tops.push([]); bots.push([]); }}
  for (i = 0; i < ns; i++) {{
    var t = i / (ns - 1), x = eixo === 'x' ? pos : d.x0 + t * (d.x1 - d.x0), y = eixo === 'x' ? d.y0 + t * (d.y1 - d.y0) : pos;
    X.push(x); Y.push(y);
    var z0 = bil(d.terr, x, y), cs = d.con.map(function(a) {{ return bil(a, x, y); }}), f = formAt(x, y), base = Math.min(cs[1], z0 - d.esp_sill);
    for (k = 0; k < 5; k++) {{
      var tp = cs[k], bt = cs[k + 1];
      if (f === d.idx_dique) {{ tp = NaN; bt = NaN; }} else if (f === d.idx_sill) {{ tp = Math.min(tp, base); bt = Math.min(bt, base); }}
      tops[k].push(tp); bots[k].push(bt);
    }}
    tops[5].push(f === d.idx_sill ? z0 : NaN); bots[5].push(f === d.idx_sill ? base : NaN);
    tops[6].push(f === d.idx_dique ? z0 : NaN); bots[6].push(f === d.idx_dique ? d.base_dique : NaN);
  }}
  var out = [];
  for (u = 0; u < 7; u++) {{
    var ok = [], ii = [], jj = [], kk = [], z = [];
    for (i = 0; i < ns; i++) ok.push(isFinite(tops[u][i]) && isFinite(bots[u][i]) && tops[u][i] - bots[u][i] > 0.3);
    for (i = 0; i < ns; i++) z.push(ok[i] ? tops[u][i] : 0);
    for (i = 0; i < ns; i++) z.push(ok[i] ? bots[u][i] : 0);
    for (i = 0; i < ns - 1; i++) if (ok[i] && ok[i + 1]) {{ ii.push(i, i + 1); jj.push(i + 1, ns + i + 1); kk.push(ns + i, ns + i); }}
    if (!ii.length) {{ ii = [0]; jj = [0]; kk = [0]; }}
    out.push({{x: X.concat(X), y: Y.concat(Y), z: z, i: ii, j: jj, k: kk}});
  }}
  return out;
}}
var capIdx = []; FIG.data.forEach(function(t, n) {{ if (t.meta && t.meta.indexOf('cap_') === 0) capIdx[parseInt(t.meta.slice(4), 10)] = n; }});
var idxTerreno = FIG.data.findIndex(function(t) {{ return t.meta === 'terreno'; }});
function aplicarCorte() {{
  var s = FIG.layout.scene, patch = {{'scene.xaxis.range': s.xaxis.range, 'scene.yaxis.range': s.yaxis.range}};
  if (!CORTE.eixo || CORTE.frac >= 0.99) {{ Plotly.restyle(gd, {{visible: false}}, capIdx); Plotly.relayout(gd, patch); return; }}
  var eixo = CORTE.eixo, a0 = eixo === 'x' ? CAP.x0 : CAP.y0, a1 = eixo === 'x' ? CAP.x1 : CAP.y1;
  var pos = CORTE.inv ? a1 - CORTE.frac * (a1 - a0) : a0 + CORTE.frac * (a1 - a0), base = eixo === 'x' ? s.xaxis.range : s.yaxis.range;
  patch['scene.' + eixo + 'axis.range'] = CORTE.inv ? [pos - 0.5, base[1]] : [base[0], pos + 0.5];
  Plotly.relayout(gd, patch);
  montarCaps(eixo, pos).forEach(function(m, u) {{
    Plotly.restyle(gd, {{x: [m.x], y: [m.y], z: [m.z], i: [m.i], j: [m.j], k: [m.k], visible: true}}, [capIdx[u]]);
  }});
}}
function aplicar() {{
  var vis = FIG.data.map(function(t) {{
    var m = t.meta;
    if (m === 'geo') return camadasOn.terreno && textura === 'tex_geologia';
    if (m === 'terreno') return camadasOn.terreno;
    if (m && m.indexOf('cap_') === 0) return false;
    if (m && camadasOn.hasOwnProperty(m)) return camadasOn[m];
    return true;
  }});
  Plotly.restyle(gd, {{visible: vis}});
  Plotly.restyle(gd, {{vertexcolor: [coresTerreno(textura === 'tex_satelite' ? 'sat' : 'hip')]}}, [idxTerreno]);
  var ids = []; FIG.data.forEach(function(t, n) {{ if (t.meta === 'terreno' || t.meta === 'geo') ids.push(n); }});
  Plotly.restyle(gd, {{opacity: OP}}, ids);
  var ar = FIG.layout.scene.aspectratio;
  Plotly.relayout(gd, {{'scene.aspectratio': {{x: ar.x, y: ar.y, z: ar.z * EXAG / 3}}}});
  aplicarCorte();
}}
gd.style.height = altura() + 'px';
Plotly.newPlot(gd, FIG.data, FIG.layout, {{responsive: true, displaylogo: false}}).then(function() {{ aplicar(); iniciarAnimacoes(); }});
function marcarCorte() {{
  document.querySelectorAll('.cz').forEach(function(b) {{
    b.classList.toggle('ativo', b.dataset.e === CORTE.eixo && (b.dataset.e === '' || (b.dataset.i === '1') === CORTE.inv));
  }});
}}
function pararAnim() {{ if (anim) {{ clearInterval(anim); anim = null; }} document.getElementById('anim').classList.remove('ativo'); }}
function tocarAnim() {{
  pararAnim(); document.getElementById('anim').classList.add('ativo');
  var dir = -1; if (!CORTE.eixo) {{ CORTE.eixo = 'x'; CORTE.inv = false; }}
  anim = setInterval(function() {{
    CORTE.frac += dir * 0.04; if (CORTE.frac <= 0.1) {{ CORTE.frac = 0.1; dir = 1; }} if (CORTE.frac >= 1) {{ CORTE.frac = 1; dir = -1; }}
    document.getElementById('cpos').value = Math.round(CORTE.frac * 100); marcarCorte(); aplicarCorte();
  }}, 220);
}}
function pararGiro() {{ if (giroT) {{ clearInterval(giroT); giroT = null; }} document.getElementById('giro').classList.remove('ativo'); }}
function tocarGiro() {{
  pararGiro(); document.getElementById('giro').classList.add('ativo');
  giroT = setInterval(function() {{
    ang = (ang + 2 * Math.PI / 90) % (2 * Math.PI);
    Plotly.relayout(gd, {{'scene.camera.eye': {{x: RAIO * Math.cos(ang), y: RAIO * Math.sin(ang), z: 0.95}}}});
  }}, 80);
}}
function iniciarAnimacoes() {{ marcarCorte(); setTimeout(tocarAnim, 500); setTimeout(tocarGiro, 300); }}
document.querySelectorAll('.cz').forEach(function(b) {{ b.onclick = function() {{
  pararAnim(); CORTE.eixo = b.dataset.e; CORTE.inv = b.dataset.i === '1';
  if (CORTE.eixo && CORTE.frac >= 0.99) {{ CORTE.frac = 0.5; document.getElementById('cpos').value = 50; }}
  marcarCorte(); aplicarCorte(); }}; }});
document.getElementById('cpos').oninput = function() {{ pararAnim(); CORTE.frac = parseFloat(this.value) / 100; if (!CORTE.eixo) CORTE.eixo = 'x'; marcarCorte(); aplicarCorte(); }};
document.getElementById('anim').onclick = function() {{ if (anim) {{ pararAnim(); CORTE.frac = 1; document.getElementById('cpos').value = 100; aplicarCorte(); }} else tocarAnim(); }};
document.getElementById('giro').onclick = function() {{ if (giroT) pararGiro(); else tocarGiro(); }};
['mousedown', 'touchstart', 'wheel'].forEach(function(ev) {{ gd.addEventListener(ev, pararGiro); }});
document.querySelectorAll('.tex').forEach(function(b) {{ b.onclick = function() {{ textura = b.dataset.t;
  document.querySelectorAll('.tex').forEach(function(x) {{ x.classList.toggle('ativo', x === b); }}); aplicar(); }}; }});
document.querySelectorAll('.cam').forEach(function(b) {{ b.onclick = function() {{ camadasOn[b.dataset.m] = !camadasOn[b.dataset.m];
  b.classList.toggle('ativo', camadasOn[b.dataset.m]); aplicar(); }}; }});
document.querySelectorAll('.cam').forEach(function(b) {{ b.classList.toggle('ativo', !!camadasOn[b.dataset.m]); }});
document.getElementById('op').oninput = function() {{ OP = parseFloat(this.value) / 100; aplicar(); }};
document.getElementById('exag').onchange = function() {{ EXAG = parseFloat(this.value); aplicar(); }};
var TEMA = {{
  escuro: {{paper: '{v.MARCA_NAVY}', cena: '#0C2945', grid: '#2A4663', txt: '{v.MARCA_CINZA_CLARO}', painel: '{v.MARCA_ROXO_ESCURO}', btn: '{v.MARCA_NAVY}', leg: 'rgba(12,41,69,0.8)'}},
  claro: {{paper: '#F1F5F9', cena: '#FFFFFF', grid: '#CBD5E1', txt: '{v.MARCA_NAVY}', painel: '#E2E8F0', btn: '#FFFFFF', leg: 'rgba(255,255,255,0.85)'}},
}};
document.querySelectorAll('.tema').forEach(function(b) {{ b.onclick = function() {{
  var t = TEMA[b.dataset.t], r = document.documentElement.style;
  r.setProperty('--bg', t.paper); r.setProperty('--txt', t.txt); r.setProperty('--painel', t.painel); r.setProperty('--btn', t.btn);
  document.querySelectorAll('.tema').forEach(function(x) {{ x.classList.toggle('ativo', x === b); }});
  var p = {{paper_bgcolor: t.paper, 'font.color': t.txt, 'legend.bgcolor': t.leg}};
  ['xaxis', 'yaxis', 'zaxis'].forEach(function(e) {{ p['scene.' + e + '.backgroundcolor'] = t.cena; p['scene.' + e + '.gridcolor'] = t.grid; p['scene.' + e + '.color'] = t.txt; }});
  Plotly.relayout(gd, p);
}}; }});
window.addEventListener('resize', function() {{ gd.style.height = altura() + 'px'; Plotly.Plots.resize(gd); }});
</script></body></html>"""
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Salvo em: {OUT_HTML} ({OUT_HTML.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
