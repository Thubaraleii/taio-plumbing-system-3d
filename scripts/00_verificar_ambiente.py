"""
Verifica se o ambiente Python esta pronto para o pipeline GemPy -> Blender.
Roda um modelo GemPy minusculo, 100% sintetico, so para confirmar que a
instalacao e a API estao funcionando nesta maquina.

Uso:
    python scripts/00_verificar_ambiente.py
"""
import sys


def main():
    print("Verificando dependencias...")

    try:
        import numpy as np
    except ImportError:
        sys.exit("ERRO: numpy nao instalado. Rode: pip install -r ambiente/requirements.txt")

    try:
        import pandas as pd
    except ImportError:
        sys.exit("ERRO: pandas nao instalado. Rode: pip install -r ambiente/requirements.txt")

    try:
        import rasterio  # noqa: F401
    except ImportError:
        sys.exit("ERRO: rasterio nao instalado. Rode: pip install -r ambiente/requirements.txt")

    try:
        import gempy as gp
    except ImportError:
        sys.exit("ERRO: gempy nao instalado. Rode: pip install -r ambiente/requirements.txt")

    print(f"GemPy versao: {gp.__version__}")
    print("Rodando modelo sintetico de teste (2 pontos de contato + 1 orientacao)...")

    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp:
        sp_path = os.path.join(tmp, "surface_points.csv")
        ori_path = os.path.join(tmp, "orientations.csv")

        pd.DataFrame({
            "X": [0, 10, 20, 0, 10, 20],
            "Y": [0, 0, 0, 0, 0, 0],
            "Z": [10, 8, 5, -5, -8, -10],
            "formation": ["contato_1"] * 3 + ["contato_2"] * 3,
        }).to_csv(sp_path, index=False)

        pd.DataFrame({
            "X": [10], "Y": [0], "Z": [8],
            "G_x": [0], "G_y": [0], "G_z": [1],
            "formation": ["contato_1"],
        }).to_csv(ori_path, index=False)

        geo_model = gp.create_geomodel(
            project_name="teste_ambiente",
            extent=[0, 20, 0, 10, -20, 20],
            resolution=[20, 10, 20],
            refinement=1,
            importer_helper=gp.data.ImporterHelper(
                path_to_surface_points=sp_path,
                path_to_orientations=ori_path,
            ),
        )
        gp.map_stack_to_surfaces(geo_model, {"Series1": ["contato_1", "contato_2"]})
        gp.compute_model(geo_model)

        n_meshes = len(geo_model.solutions.dc_meshes)
        assert n_meshes > 0, "Nenhuma malha foi gerada — algo esta errado."

    print(f"Modelo calculado com sucesso ({n_meshes} superficie(s) gerada(s)).")
    print("\nAmbiente OK")


if __name__ == "__main__":
    main()
