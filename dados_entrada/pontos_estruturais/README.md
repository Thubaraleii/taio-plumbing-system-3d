# Pontos estruturais de campo

Aqui ficam os dados que alimentam o GemPy com a geologia real do corpo de Taió.

Ha dois arquivos de exemplo ja prontos (`surface_points_exemplo.csv` e
`orientations_exemplo.csv`), com um sill sintetico fictício so para
demonstrar o formato — foram usados para testar o pipeline. Quando for
usar dados reais, crie (ou renomeie os exemplos para) `surface_points.csv`
e `orientations.csv`, que sao os nomes que os scripts esperam.

## surface_points.csv

Pontos onde voce sabe que um contato geologico passa (topo/base do sill,
contato com a encaixante, etc.):

| coluna | significado |
|---|---|
| X, Y | coordenadas UTM (mesmo sistema dos seus shapefiles/raster) |
| Z | cota/altitude do ponto (metros) |
| formation | nome da unidade/superficie (ex.: `sill_principal`, `contato_encaixante`) |

## orientations.csv

Atitudes medidas em campo (bussola/clinometro), convertidas para vetor normal ao plano:

| coluna | significado |
|---|---|
| X, Y, Z | onde a medida foi tirada |
| G_x, G_y, G_z | vetor normal ao plano medido |
| formation | a qual superficie essa orientacao pertence |

Se em campo voce anotou **dip / dip direction** (mais comum), converta para
G_x, G_y, G_z antes — ha uma funcao pronta comentada no final do arquivo
`scripts/02_montar_modelo_gempy.py` (`dip_dipdir_para_normal`).

Quanto mais pontos de contato e orientacoes reais voce tiver (inclusive
tirados dos seus shapefiles de perfis/afonso_perfis e do laudo), mais fiel
o modelo implicito vai ficar ao corpo real do Taió.
