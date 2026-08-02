"""
Le um raster de topografia (MDE/DEM gerado a partir das fotos de drone,
por exemplo via fotogrametria no WebODM/Agisoft/Pix4D/Metashape) e converte
para uma nuvem de pontos XYZ que o GemPy entende como topografia.

Coloque o seu raster (.tif) dentro de:
    dados_entrada/topografia_drone/

E ajuste RASTER_PATH abaixo.

Uso:
    python scripts/01_carregar_topografia_raster.py
"""
from pathlib import Path

import numpy as np
import rasterio

# --- AJUSTE AQUI ---
RASTER_PATH = Path(__file__).parent.parent / "dados_entrada" / "topografia_drone" / "mde_taio.tif"
# Reduz a resolucao do raster para nao gerar milhoes de pontos (o GemPy nao
# precisa da resolucao cheia do drone, so o suficiente para representar o
# relevo). 5 = usa 1 a cada 5 pixels em cada eixo.
DOWNSAMPLE_FACTOR = 5
# --------------------


def carregar_topografia(raster_path: Path, downsample: int = 5) -> np.ndarray:
    """Retorna um array (N, 3) de pontos X, Y, Z a partir de um raster de elevacao."""
    with rasterio.open(raster_path) as src:
        banda = src.read(1)
        banda = banda[::downsample, ::downsample]

        nodata = src.nodata
        rows, cols = np.meshgrid(
            np.arange(0, src.height, downsample),
            np.arange(0, src.width, downsample),
            indexing="ij",
        )
        # rasterio.transform.xy achata a entrada 2D em listas 1D (ordem 'ij',
        # a mesma do meshgrid acima), entao achatamos a banda do mesmo jeito
        # para os indices continuarem correspondendo ponto a ponto.
        xs, ys = rasterio.transform.xy(src.transform, rows, cols)
        xs = np.array(xs)
        ys = np.array(ys)
        zs = banda.ravel()

        if nodata is not None:
            mask = zs != nodata
        else:
            mask = np.isfinite(zs)

        xyz = np.column_stack([xs[mask], ys[mask], zs[mask]])
        return xyz


def main():
    if not RASTER_PATH.exists():
        print(f"Raster nao encontrado em: {RASTER_PATH}")
        print("Coloque o MDE (.tif) do drone nessa pasta e ajuste RASTER_PATH no script.")
        return

    xyz = carregar_topografia(RASTER_PATH, DOWNSAMPLE_FACTOR)
    z_min, z_max = xyz[:, 2].min(), xyz[:, 2].max()
    print(f"Topografia carregada: {xyz.shape[0]} pontos")
    print(f"Extensao X: {xyz[:, 0].min():.1f} a {xyz[:, 0].max():.1f}")
    print(f"Extensao Y: {xyz[:, 1].min():.1f} a {xyz[:, 1].max():.1f}")
    print(f"Extensao Z: {z_min:.4f} a {z_max:.4f}")

    # Checagem de sanidade: um raster de elevacao real da regiao de Taio deve
    # variar dezenas a centenas de metros (o campo mediu Z entre 365 e 879m).
    # Se o Z do raster estiver todo entre ~0 e ~1, o raster provavelmente foi
    # exportado com um "stretch"/normalizacao de simbologia (comum ao exportar
    # do ArcGIS sem preservar os valores brutos) em vez da elevacao real --
    # ja aconteceu com o raster que veio de 0_ORGANIZADO. Nesse caso NAO use
    # esse arquivo direto: ele vai gerar uma topografia errada (achatada).
    if -1 <= z_min and z_max <= 1.5:
        print("\nAVISO: os valores de Z desse raster estao entre 0 e 1.")
        print("Isso indica que o raster foi exportado normalizado/com stretch de")
        print("simbologia, NAO com a elevacao real em metros. Nao vou salvar o")
        print(".npy de topografia a partir desse arquivo -- ele deixaria o modelo")
        print("com o relevo achatado/errado. Reexporte o raster preservando os")
        print("valores brutos de elevacao (ou use outro DEM, ex.: TOPODATA/IBGE,")
        print("ALOS AW3D30, ou o MDE gerado direto da fotogrametria do drone).")
        return

    out_path = Path(__file__).parent.parent / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
    np.save(out_path, xyz)
    print(f"\nSalvo em: {out_path}")
    print("Use esse arquivo no script 02 (montar_modelo_gempy) para definir a topografia real do modelo.")


if __name__ == "__main__":
    main()
