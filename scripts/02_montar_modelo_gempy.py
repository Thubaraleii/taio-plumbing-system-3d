"""
Monta o modelo geologico do plumbing system de Taio no GemPy:
  1. Cria o geo_model com a extensao real da area
  2. Define a topografia real (a partir do .npy gerado pelo script 01)
  3. Carrega os pontos de superficie (contatos) e orientacoes (atitudes) de campo
  4. Define as series/pilha estratigrafica (ordem de intrusao/deposicao)
  5. Calcula o modelo implicito

Antes de rodar, preencha os CSVs de exemplo em
dados_entrada/pontos_estruturais/ com os dados reais de campo:

  surface_points.csv   -> colunas: X, Y, Z, formation
  orientations.csv     -> colunas: X, Y, Z, G_x, G_y, G_z, formation
    (G_x, G_y, G_z = vetor normal ao plano medido em campo; se voce mediu
    dip/dip direction, converta antes — ha uma funcao auxiliar comentada
    no final deste arquivo)

Uso:
    python scripts/02_montar_modelo_gempy.py
"""
from pathlib import Path

import numpy as np
import gempy as gp

BASE = Path(__file__).parent.parent
DADOS = BASE / "dados_entrada"

SURFACE_POINTS_CSV = DADOS / "pontos_estruturais" / "surface_points.csv"
ORIENTATIONS_CSV = DADOS / "pontos_estruturais" / "orientations.csv"
TOPOGRAFIA_NPY = DADOS / "topografia_drone" / "topografia_xyz.npy"

# --- Extensao real, calculada a partir dos dados extraidos em
# 2_Banco_de_Dados (158 pontos de contato + 104 orientacoes de TI.shp e
# pontos2507.shp) com uma folga de 1000m em X/Y e 200m em Z. Ajuste se
# adicionar mais dados de campo com extensao maior/menor.
# [min_x, max_x, min_y, max_y, min_z, max_z] -- SIRGAS 2000 / UTM 22S (EPSG:31982)
EXTENT = [581834, 605093, 6992965, 7031159, 165, 1079]
RESOLUTION = [50, 50, 50]

# Formacoes reais (31/07/2026: encaixante_sedimentar generica foi
# reclassificada nas 5 formacoes permianas reais mapeadas pela CPRM/GeoSGB
# que cruzam a extensao do modelo -- ver
# 2_Banco_de_Dados/scripts_etl/gerar_gempy_de_unificados.py e
# extrair_cprm_formacoes.py). Da mais nova para a mais antiga: o dique corta
# tudo (serie propria, orientacao bem mais intgreme que o resto -- por isso
# fica fora da Serie_Intrusiva, senao a mistura de mergulhos rasos
# (sill/encaixante) com intgremes (dique) num so campo potencial tende a
# desestabilizar a interpolacao); depois o sill diabasico intrude a
# sequencia sedimentar (Bacia do Parana, Grupo Guata/Passa Dois, mais nova
# -> mais antiga: Teresina, Serra Alta, Irati, Palermo, Rio Bonito).
#
# Atencao: encaixante_rio_bonito, encaixante_palermo e encaixante_irati
# ainda NAO tem nenhuma orientacao propria (todo o dado de orientacao de
# campo caiu perto de Serra Alta/Teresina) -- essas 3 superficies vao ficar
# fracamente restringidas ate ter medidas de atitude reais nelas.
PILHA_ESTRATIGRAFICA = {
    "Serie_Dique": ["dique"],
    "Serie_Intrusiva": [
        "sill_diabasio",
        "encaixante_teresina",
        "encaixante_serra_alta",
        "encaixante_irati",
        "encaixante_palermo",
        "encaixante_rio_bonito",
    ],
}
# ---------------------------------------------------------------------


def main():
    if not SURFACE_POINTS_CSV.exists() or not ORIENTATIONS_CSV.exists():
        print("Faltam os CSVs de pontos estruturais. Copie/edite os exemplos em:")
        print(f"  {SURFACE_POINTS_CSV}")
        print(f"  {ORIENTATIONS_CSV}")
        return

    print("Criando geo_model...")
    geo_model = gp.create_geomodel(
        project_name="taio_plumbing_system",
        extent=EXTENT,
        resolution=RESOLUTION,
        refinement=1,
        importer_helper=gp.data.ImporterHelper(
            path_to_surface_points=str(SURFACE_POINTS_CSV),
            path_to_orientations=str(ORIENTATIONS_CSV),
        ),
    )

    if TOPOGRAFIA_NPY.exists():
        print("Aplicando topografia real do drone...")
        xyz = np.load(TOPOGRAFIA_NPY)
        gp.set_topography_from_arrays(grid=geo_model.grid, xyz_vertices=xyz)
    else:
        print("Aviso: topografia do drone nao encontrada — rode antes o script 01.")
        print("Seguindo sem topografia real (modelo so em subsuperficie).")

    print("Definindo pilha estratigrafica...")
    gp.map_stack_to_surfaces(geo_model, PILHA_ESTRATIGRAFICA)

    print("Calculando o modelo (pode demorar dependendo da resolucao)...")
    gp.compute_model(geo_model)

    n_meshes = len(geo_model.solutions.dc_meshes)
    print(f"\nModelo calculado: {n_meshes} superficie(s).")

    out_path = BASE / "exports" / "geo_model_taio.gempy"
    gp.save_model(geo_model, path=str(out_path))
    print(f"Modelo salvo em: {out_path}")
    print("\nProximo passo: rode scripts/03_exportar_obj_para_blender.py")

    return geo_model


# --- Auxiliar: se voce mediu dip / dip direction em campo (mais comum em
# caderneta de campo do que vetor normal direto), converta assim antes de
# montar o orientations.csv:
#
# import numpy as np
# def dip_dipdir_para_normal(dip_deg, dip_direction_deg):
#     dip = np.radians(dip_deg)
#     dipdir = np.radians(dip_direction_deg)
#     gx = np.sin(dip) * np.sin(dipdir)
#     gy = np.sin(dip) * np.cos(dipdir)
#     gz = np.cos(dip)
#     return gx, gy, gz

if __name__ == "__main__":
    main()
