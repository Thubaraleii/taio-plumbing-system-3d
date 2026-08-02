# Topografia (MDE/DEM do drone)

Coloque aqui o raster de elevacao (Modelo Digital de Elevacao / DEM/MDE)
gerado a partir das fotos de drone processadas em fotogrametria (WebODM,
Agisoft Metashape, Pix4D, etc.) — geralmente um arquivo `.tif`.

Esse e o raster de **elevacao** (superficie do terreno), diferente do
ortomosaico (a "foto" colorida do terreno) — os dois normalmente saem
juntos do processamento fotogrametrico, mas para o GemPy so precisamos do
MDE. O ortomosaico pode ser usado depois no Blender como textura.

Depois de colocar o arquivo aqui, rode:

```
python scripts/01_carregar_topografia_raster.py
```

(ajuste o nome do arquivo em `RASTER_PATH` dentro do script se nao for
`mde_taio.tif`). Isso gera `topografia_xyz.npy`, que o script 02 usa
automaticamente para colocar a topografia real no modelo GemPy.

## Pendencia (30/07/2026): o MDE que ja existia em 0_ORGANIZADO nao serve

Testei o MDE que ja estava pronto em `0_ORGANIZADO/02_Dados_GIS_Base/
Rasters_e_Projetos_Taio/relevo/` (`Modelo Dig Terreno.tif`, e tambem as
variantes `_1.tif`, `_1_bgis.tif` e o grid ESRI original `w001001.adf`) —
**nenhuma delas tem elevacao real em metros**. Os valores de pixel em
todas elas vao de 0 a 1 (um raster "esticado"/normalizado, provavelmente
exportado a partir da simbologia do ArcGIS em vez dos valores brutos).
Os pontos de campo (`2_Banco_de_Dados`) mostram que a elevacao real da
area varia entre 365m e 879m — bem diferente de uma escala 0-1.

Por isso nao coloquei nenhum raster aqui ainda. O script
`01_carregar_topografia_raster.py` ja tem uma checagem automatica que
detecta esse problema (raster com Z entre 0 e 1) e avisa em vez de
silenciosamente gerar uma topografia errada/achatada.

Opcoes pra resolver:
1. **Reexportar o raster no ArcGIS/QGIS preservando os valores brutos**
   (sem "stretch"/normalizacao de simbologia) a partir do projeto
   `Projeto_ArcGIS_Sill/sillCRI.aprx` ou de onde o MDE original foi gerado.
2. **Baixar um DEM publico da regiao** (TOPODATA/IBGE, ALOS AW3D30, SRTM)
   caso nao tenha o dado bruto salvo em lugar nenhum.
3. **Usar o MDE gerado direto da fotogrametria do drone** (WebODM/Metashape/
   Pix4D), que e o mais preciso e o que da o titulo a esta pasta — se ainda
   nao processou as fotos de `0_ORGANIZADO/04_Fotos_Drone_Por_Agrupamento`
   em fotogrametria, esse e o caminho ideal.

Enquanto isso, o modelo GemPy (scripts 02 e 03) ja roda normalmente **sem**
topografia — ele so fica sem o relevo real por cima, com as superficies
calculadas apenas em subsuperficie. Isso ja foi testado e funciona (veja
`exports/meshes/` — ja tem um primeiro resultado gerado so com os dados
estruturais de campo).
