"""
Exporta a topografia (nuvem de pontos XYZ gerada a partir das curvas de
nivel, ver 2_Banco_de_Dados/scripts_etl/extrair_topografia_curvas_nivel.py)
como uma malha .obj com UV, mais uma textura .png com tinta hipsometrica
(cor por elevacao), pronta para importar no Blender junto com as superficies
do GemPy (sill_diabasio.obj, encaixante_sedimentar.obj).

Diferente do 03_exportar_obj_para_blender.py (que exporta as superficies
calculadas pelo GemPy), este script nao depende do GemPy -- reconstroi a
superficie do terreno diretamente a partir dos pontos das curvas de nivel
via interpolacao (grade regular), so para fins de visualizacao/render no
Blender.

Uso:
    python scripts/04_exportar_topografia_para_blender.py
"""
from pathlib import Path

import numpy as np
from scipy.interpolate import griddata
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BASE = Path(__file__).parent.parent
TOPO_NPY = BASE / "dados_entrada" / "topografia_drone" / "topografia_xyz.npy"
EXPORTS_DIR = BASE / "exports" / "meshes"

# Resolucao da grade (pontos por eixo). So afeta o nivel de detalhe do
# render no Blender -- nao tem relacao com a grade de calculo do GemPy
# (RESOLUTION em 02_montar_modelo_gempy.py).
RESOLUCAO = 300

# paleta hipsometrica customizada (baixo -> alto), mesma usada no
# visualizador Plotly (blender/visualizacao_publico/scripts_bpy nao,
# esse le o PNG gerado aqui -- ver viewer_3d.py pro Plotly)
CORES_HIPSOMETRICAS = ["#A66A2C", "#C6924A", "#D8C88C", "#9FC1A3", "#4F9AA8"]
COLORMAP = LinearSegmentedColormap.from_list("hipsometrico_taio", CORES_HIPSOMETRICAS)

OBJ_PATH = EXPORTS_DIR / "topografia.obj"
MTL_PATH = EXPORTS_DIR / "topografia.mtl"
TEXTURA_PATH = EXPORTS_DIR / "topografia_textura.png"


def main():
    if not TOPO_NPY.exists():
        print(f"Topografia nao encontrada em: {TOPO_NPY}")
        print("Rode antes 2_Banco_de_Dados/scripts_etl/extrair_topografia_curvas_nivel.py")
        return

    xyz = np.load(TOPO_NPY)
    print(f"Topografia carregada: {xyz.shape[0]} pontos")

    xmin, xmax = xyz[:, 0].min(), xyz[:, 0].max()
    ymin, ymax = xyz[:, 1].min(), xyz[:, 1].max()

    print(f"Interpolando para uma grade regular {RESOLUCAO}x{RESOLUCAO}...")
    grid_x, grid_y = np.meshgrid(
        np.linspace(xmin, xmax, RESOLUCAO),
        np.linspace(ymin, ymax, RESOLUCAO),
    )
    grid_z = griddata(xyz[:, :2], xyz[:, 2], (grid_x, grid_y), method="linear")
    grid_z_nearest = griddata(xyz[:, :2], xyz[:, 2], (grid_x, grid_y), method="nearest")
    grid_z = np.where(np.isnan(grid_z), grid_z_nearest, grid_z)

    n = RESOLUCAO
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- textura: tinta hipsometrica (cor por elevacao) ---
    print("Gerando textura...")
    norm = plt.Normalize(vmin=grid_z.min(), vmax=grid_z.max())
    cores = COLORMAP(norm(grid_z))[:, :, :3]
    # imagem com linha 0 = norte (Y maximo) no topo, como um mapa normal
    plt.imsave(TEXTURA_PATH, np.flipud(cores))
    print(f"  {TEXTURA_PATH}")

    # --- material ---
    with open(MTL_PATH, "w") as f:
        f.write("newmtl topografia\n")
        f.write("Ka 1.0 1.0 1.0\n")
        f.write("Kd 1.0 1.0 1.0\n")
        f.write("Ks 0.0 0.0 0.0\n")
        f.write(f"map_Kd {TEXTURA_PATH.name}\n")
    print(f"  {MTL_PATH}")

    # --- malha .obj com UV ---
    # indice do vertice (i, j) -> i*n + j (0-indexado; OBJ usa 1-indexado)
    # v = i/(n-1) por causa do flip da imagem (linha 0 da imagem = i = n-1, Y maximo)
    with open(OBJ_PATH, "w") as f:
        f.write(f"# topografia - reconstruida das curvas de nivel ({n}x{n})\n")
        f.write(f"mtllib {MTL_PATH.name}\n")
        for i in range(n):
            for j in range(n):
                f.write(f"v {grid_x[i, j]} {grid_y[i, j]} {grid_z[i, j]}\n")
        for i in range(n):
            for j in range(n):
                u = j / (n - 1)
                v = i / (n - 1)
                f.write(f"vt {u} {v}\n")
        f.write("usemtl topografia\n")
        for i in range(n - 1):
            for j in range(n - 1):
                v00 = i * n + j + 1
                v01 = i * n + (j + 1) + 1
                v11 = (i + 1) * n + (j + 1) + 1
                v10 = (i + 1) * n + j + 1
                f.write(f"f {v00}/{v00} {v01}/{v01} {v11}/{v11}\n")
                f.write(f"f {v00}/{v00} {v11}/{v11} {v10}/{v10}\n")

    print(f"  {OBJ_PATH}")
    print(f"\nPronto. No Blender: File > Import > Wavefront (.obj), selecione {OBJ_PATH.name}")
    print("(mantenha topografia.obj, topografia.mtl e topografia_textura.png na mesma pasta)")


if __name__ == "__main__":
    main()
