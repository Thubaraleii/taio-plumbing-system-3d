# 1_Modelo_3D_Taio — pasta principal do projeto

Esta é a pasta **main** do mestrado: o modelo 3D do plumbing system intrusivo de Taió. Todas as outras pastas numeradas que virão a seguir (2_, 3_, 4_...) são subsídios para chegar até aqui — geoprocessamento, dados de campo, geoquímica, etc. As pastas antigas (`0_ORGANIZADO\01_...` a `04_...`) continuam existindo como base/arquivo de referência, fora dessa nova numeração.

## Objetivo

Construir o modelo 3D do sistema intrusivo de Taió usando **GemPy** (modelagem geológica implícita) para gerar as superfícies (contatos, sills, corpo intrusivo) a partir de dados de campo e GIS, apoiado na topografia real obtida por fotogrametria de drone (raster/MDE + ortomosaico), e depois refinar/renderizar o resultado no **Blender**.

## Fluxo de trabalho (visão geral)

1. **Dados de entrada** (`dados_entrada/`): raster de topografia do drone (MDE/DEM), rasters geológicos (magnetometria etc. se houver), e os pontos estruturais de campo (contatos e atitudes/orientações) digitalizados em CSV.
2. **GemPy** (`scripts/`): carrega a topografia real, monta o modelo geológico (superfícies + orientações), calcula o modelo implícito e exporta cada superfície como malha (.obj).
3. **Blender** (`blender/`): importa os .obj exportados, ajusta materiais/texturas (ex.: ortomosaico de drone como textura do terreno), organiza cenas e cria os renders/animações do plumbing system.
4. **Exports** (`exports/`): resultado final — malhas, imagens, vídeos.

Veja `docs/fluxo_de_trabalho.md` para o detalhe passo a passo, e `ambiente/SETUP.md` para instalar o ambiente Python com GemPy.

O visualizador 2D interativo (mapa em planta + seção transversal) também tem
repositório próprio: [taio-plumbing-system-2d](https://github.com/Thubaraleii/taio-plumbing-system-2d).

## Status (atualizado em 30/07/2026)

- **Dados estruturais reais já ligados**: `2_Banco_de_Dados` extraiu 158 pontos de contato e 104 orientações de campo dos shapefiles que já existiam em `0_ORGANIZADO` (ver `2_Banco_de_Dados/README.md`), e eles já estão em `dados_entrada/pontos_estruturais/`. `EXTENT` e `PILHA_ESTRATIGRAFICA` em `scripts/02_montar_modelo_gempy.py` já foram ajustados para a área e as formações reais (`sill_diabasio`, `encaixante_sedimentar`).
- **Primeiro resultado já gerado**: `exports/meshes/sill_diabasio.obj` e `exports/meshes/encaixante_sedimentar.obj` — já dá pra abrir no Blender agora, mesmo sem topografia (ver pendência abaixo).
- **Pendente**: topografia real. O MDE que já existia em `0_ORGANIZADO` não tem elevação em metros de verdade (é um raster normalizado 0-1) — ver `dados_entrada/topografia_drone/README.md` para o que fazer. Sem isso, o modelo roda só em subsuperfície (sem o relevo real por cima).
- Todo o pipeline (scripts 00 a 03) foi testado de ponta a ponta nesta sessão, tanto com dados sintéticos quanto com os dados reais de campo, usando GemPy 2026.0.3 (API v3).
