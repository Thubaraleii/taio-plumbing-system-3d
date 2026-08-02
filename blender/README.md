# Blender

Guarde aqui os arquivos `.blend` do projeto (cena do modelo 3D do plumbing
system, materiais, camera/iluminacao, animacoes).

## Fluxo basico de importacao

1. Rode `scripts/03_exportar_obj_para_blender.py` — isso gera um `.obj` por
   superficie em `exports/meshes/`.
2. No Blender: `File > Import > Wavefront (.obj)`, selecione todos os
   `.obj` gerados (pode selecionar varios de uma vez).
3. Cada superficie entra como um objeto separado — nomeie/organize por
   camadas (collections) se quiser (ex.: "sill_principal",
   "contato_encaixante").
4. Se quiser usar o ortomosaico de drone como textura do terreno: importe
   o raster de topografia como imagem e aplique como textura sobre a malha
   de topografia (voce pode gerar essa malha de topografia separadamente a
   partir do MDE, ou usar um plugin de importacao de DEM do proprio
   Blender).
5. Salve o `.blend` aqui.

## Sobre escala/coordenadas

Os `.obj` exportados pelo script 03 ja estao nas coordenadas reais (UTM,
mesmo sistema do raster e dos shapefiles) — nao na escala normalizada
interna do GemPy. Isso significa que os numeros podem ser grandes (coordenadas
UTM tem 6-7 digitos). Se o Blender reclamar de escala/precisao, considere
recentralizar o modelo antes de exportar (subtrair um ponto de referencia
fixo de todas as coordenadas X, Y, Z) — posso ajustar o script 03 para
fazer isso automaticamente se voce preferir.
