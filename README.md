# _Modelo_3D_Taio 


## Objetivo

Construir o modelo 3D do sistema intrusivo de Taió usando **GemPy** (modelagem geológica implícita) para gerar as superfícies (contatos, sills, corpo intrusivo) a partir de dados de campo e GIS, apoiado na topografia real obtida por fotogrametria de drone (raster/MDE + ortomosaico), e depois refinar/renderizar o resultado no **Blender**.

## Fluxo de trabalho (visão geral)

1. **Dados de entrada** (`dados_entrada/`): raster de topografia do drone (MDE/DEM), rasters geológicos (magnetometria etc. se houver), e os pontos estruturais de campo (contatos e atitudes/orientações) digitalizados em CSV.
2. **GemPy** (`scripts/`): carrega a topografia real, monta o modelo geológico (superfícies + orientações), calcula o modelo implícito e exporta cada superfície como malha (.obj).
3. **Blender** (`blender/`): importa os .obj exportados, ajusta materiais/texturas (ex.: ortomosaico de drone como textura do terreno), organiza cenas e cria os renders/animações do plumbing system.
4. **Exports** (`exports/`): resultado final — malhas, imagens, vídeos.

Veja `docs/fluxo_de_trabalho.md` para o detalhe passo a passo, e `ambiente/SETUP.md` para instalar o ambiente Python com GemPy.

Cada visualizador web é uma aplicação separada, com repositório próprio
(mais leve, focado só naquele produto):
- [taio-plumbing-system-2d](https://github.com/Thubaraleii/taio-plumbing-system-2d) — seção transversal interativa
- [TAIO-DASH](https://github.com/Thubaraleii/TAIO-DASH) — dashboard geoquímico
- [TAIO-WEBMAP](https://github.com/Thubaraleii/TAIO-WEBMAP) — webmap em tela cheia

`visualizacao_web/index.html` (este repositório) é o hub que linka pros 4.
