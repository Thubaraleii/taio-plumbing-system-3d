# Fluxo de trabalho — Modelo 3D do Plumbing System de Taió

## Visao geral

```
dados de campo (contatos, atitudes)  ---\
                                          >--  GemPy  --> malhas .obj --> Blender --> render/animacao
raster de topografia (MDE do drone)  ---/
```

O GemPy faz a parte de **modelagem geologica implicita**: a partir de
pontos onde voce sabe que um contato passa e de orientacoes (atitudes)
medidas em campo, ele interpola matematicamente as superficies em 3D
(usando um metodo de interpolacao co-kriging). O resultado sao malhas
(vertices + faces triangulares) de cada superficie/formacao.

O Blender entra depois, para dar acabamento visual: materiais, texturas
(ex.: ortomosaico de drone sobre o terreno), iluminacao, camera e
renders/animacoes para apresentacao (banca, artigo, etc.).

## Passo a passo

### 1. Preparar o ambiente

```
cd 1_Modelo_3D_Taio
python -m venv venv
venv\Scripts\activate
pip install -r ambiente\requirements.txt
python scripts\00_verificar_ambiente.py
```

### 2. Preparar os dados de entrada

- Coloque o MDE (raster de elevacao) gerado da fotogrametria do drone em
  `dados_entrada/topografia_drone/` (veja o README dessa pasta).
- Digite/exporte os pontos de contato e as orientacoes medidas em campo
  para `dados_entrada/pontos_estruturais/surface_points.csv` e
  `orientations.csv` (veja o README dessa pasta — ha exemplos prontos
  para copiar o formato).
  - Dica: se voce ja tem esses pontos digitalizados como shapefile (ex.:
    em `02_Dados_GIS_Base/Shapefiles_Campo/afonso_perfis`), pode exportar
    os atributos X/Y/Z + formacao para CSV a partir do QGIS/ArcGIS em vez
    de digitar tudo de novo.

### 3. Rodar o pipeline

```
python scripts\01_carregar_topografia_raster.py
python scripts\02_montar_modelo_gempy.py
python scripts\03_exportar_obj_para_blender.py
```

O script 2 e onde voce ajusta o essencial do modelo geologico:
- `EXTENT`: a caixa 3D que delimita o modelo (coordenadas UTM min/max de
  X, Y, Z) — defina com base na area real do corpo de Taió.
- `RESOLUTION`: a resolucao da grade de calculo (quanto maior, mais
  detalhado e mais lento).
- `PILHA_ESTRATIGRAFICA`: os nomes das suas formacoes/superficies reais e
  a ordem de intrusao/deposicao (da mais nova para a mais antiga).

### 4. Trabalhar no Blender

- Importe os `.obj` de `exports/meshes/` (`File > Import > Wavefront`).
- Ajuste materiais, texturas, iluminacao, camera.
- Salve o `.blend` em `blender/`.
- Exporte os renders finais para `exports/renders/`.

## Iterando o modelo

Modelagem implicita e um processo iterativo: voce roda, ve se a geometria
faz sentido geologico (comparando com o que sabe de campo, perfis,
literatura sobre o sistema), adiciona mais pontos de controle ou ajusta
orientacoes onde o modelo "errou", e recalcula. Nao espere acertar o
modelo final na primeira rodada.

## Proximas pastas (subsidios)

As pastas `2_`, `3_`, etc. que virao depois desta serao os subsidios para
alimentar esse modelo — por exemplo, geoprocessamento dedicado
(preparar shapefiles/rasters), extracao/organizacao dos dados de campo,
geoquimica, etc. A ideia e que tudo convirja para esta pasta `1_`.
