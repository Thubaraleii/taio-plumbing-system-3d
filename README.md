# Modelo 3D interativo — Taió

**Versão 1.0** · Projeto *Taió Plumbing System* (Mestrado em Geologia, UFSC)

🔗 **Acesso:** <https://thubaraleii.github.io/taio-plumbing-system-3d/visualizacao_web/viewer_3d_taio.html>

Modelo 3D interativo (Plotly, HTML autônomo) do “cubão” estilizado da área de Taió: relevo real, formações sedimentares,
depósito quaternário e os corpos intrusivos (soleiras e diques) em volume, com ferramenta de corte.

## Funcionalidades

**Barra superior**
- **Corte** em quatro direções (Leste → Oeste, Oeste → Leste, Norte → Sul, Sul → Norte), com controle deslizante da posição do corte; botão **Animar corte**.
- **Cor:** hipsometria, geologia (mapa geológico drapeado) ou satélite.
- **Camadas:** Topografia, Sólido (exibe o bloco inteiro, sem recorte), Campo (pontos de campo) e Geoquímica (Alto/Baixo-Ti).
- **Estruturas** (cada uma liga/desliga sozinha): falha CPRM, fratura CPRM, falha de campo (traço de rumo sobre a superfície) e lineamentos positivo/negativo.
- **Vista:** giro automático (Girar) e exagero vertical (1×, 2×, 3×, 5× ou 8×; padrão 3×).
- **Tema** escuro/claro. O modelo abre inteiro, com corte e giro desligados.
- Controle deslizante de **opacidade** da topografia e legenda de unidades.

## Dados e métodos

- **Relevo:** MDE de drone reamostrado em malha regular; **satélite** Esri reprojetado para UTM.
- **Unidades:** empilhamento por plano de mergulho regional + espessuras por unidade, com erosão pelo relevo real; paredes do bloco mostram a sequência estratigráfica nas faces de corte.
- **Soleiras e diques:** polígonos da litologia atualizada extrudados em sólido (base da soleira = topo da Serra Alta, espessura mínima de 27 m).
- **Geologia:** decalques vetoriais dos polígonos (6 unidades + quaternário + soleira + dique) drapeados no relevo.
- **Corte:** cada posição é um estado pré-calculado (4 modos × 9 posições) que mantém a caixa e a escala fixas.

## Uso

Abra `viewer_3d_taio.html` no navegador (o arquivo é grande, ~90 MB) ou acesse a versão publicada. Arraste para orbitar, role para ampliar; use o controle deslizante inferior para o corte.

## Regenerar os produtos

O repositório contém o HTML publicado e o script gerador. Para regenerar é necessário o conjunto de dados do projeto
(modelo digital de elevação, litologia, pontos de campo, lineamentos, poços), que **não é distribuído** neste repositório.

```bash
python visualizacao_web/gerar_visualizador_3d.py
```

Dependências Python: `numpy`, `pandas`, `geopandas`, `shapely`, `pyproj`, `rasterio`, `scipy`, `plotly`, `contextily` (imagem de satélite).

`gerar_visualizador_3d.py` também funciona como biblioteca de dados e construtores de sólidos.

## Pipeline de modelagem (GemPy → Blender)

Além do visualizador web, o repositório contém o pipeline de modelagem geológica implícita e de renderização.

```
MDE do drone + contatos e atitudes de campo ──► GemPy ──► malhas .obj ──► Blender ──► renders / animações
```

| Script (`scripts/`) | Função |
|---|---|
| `00_verificar_ambiente.py` | Testa a instalação do GemPy com um modelo sintético mínimo |
| `01_carregar_topografia_raster.py` | Converte o MDE (GeoTIFF) em nuvem de pontos XYZ (`topografia_xyz.npy`) |
| `02_montar_modelo_gempy.py` | Monta o modelo implícito (extensão, topografia, pontos de superfície, orientações, pilha estratigráfica) e o calcula |
| `03_exportar_obj_para_blender.py` | Recalcula o modelo e exporta cada superfície como `.obj` |
| `04_exportar_topografia_para_blender.py` | Exporta a topografia como malha `.obj` com UV e textura hipsométrica |
| `05_gerar_solidos_visualizacao.py` | Gera sólidos (com espessura) dos corpos intrusivos para visualização |
| `06_gerar_solidos_estilizados_cubao.py` | Gera os sólidos estilizados do “cubão” (visualização pública) |
| `07_gerar_secao_transversal.py` | Gera uma seção transversal 2D estilizada ao longo de uma linha reta |

Dados de entrada em `dados_entrada/` (`topografia_drone/`, `pontos_estruturais/` com `surface_points.csv` e `orientations.csv`, `rasters_geologicos/`);
ambiente em `ambiente/` (`requirements.txt`, `SETUP.md`); detalhes do fluxo em `docs/fluxo_de_trabalho.md`; cena Blender em `blender/`; saídas em `exports/`.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r ambiente/requirements.txt
python scripts/00_verificar_ambiente.py
python scripts/01_carregar_topografia_raster.py
python scripts/02_montar_modelo_gempy.py
python scripts/03_exportar_obj_para_blender.py
```

O visualizador web (`visualizacao_web/gerar_visualizador_3d.py`) é independente do GemPy: usa o MDE, a litologia e as estruturas diretamente.

## Estrutura

```
visualizacao_web/viewer_3d_taio.html         visualizador publicado
visualizacao_web/gerar_visualizador_3d.py    gerador e biblioteca
scripts/                                    pipeline GemPy → Blender
dados_entrada/  ambiente/  docs/  blender/  exports/
```

## Referências

1. Milani, E. J.; Melo, J. H. G.; Souza, P. A.; Fernandes, L. A.; França, A. B. (2007). Bacia do Paraná. *Boletim de Geociências da Petrobras*, 15(2), 265–287.
2. Schneider, R. L.; Mühlmann, H.; Tommasi, E.; Medeiros, R. A.; Daemon, R. F.; Nogueira, A. A. (1974). Revisão estratigráfica da Bacia do Paraná. In: *Anais do 28º Congresso Brasileiro de Geologia*, Porto Alegre, SBG, 1, 41–65.
3. Frank, H. T.; Gomes, M. E. B.; Formoso, M. L. L. (2009). Review of the areal extent and the volume of the Serra Geral Formation, Paraná Basin, South America. *Pesquisas em Geociências*, 36(1), 49–57.
4. Peate, D. W. (1997). The Paraná–Etendeka Province. In: Mahoney, J. J.; Coffin, M. F. (eds.), *Large Igneous Provinces*. AGU Geophysical Monograph 100, 217–245.
5. de la Varga, M.; Schaaf, A.; Wellmann, F. (2019). GemPy 1.0: open-source stochastic geological modeling and inversion. *Geoscientific Model Development*, 12, 1–32.
6. Blender Foundation. **Blender** — free and open-source 3D creation suite. <https://www.blender.org>
7. Agafonkin, V. **Leaflet** — an open-source JavaScript library for interactive maps. <https://leafletjs.com>
8. Plotly Technologies Inc. (2015). **Collaborative data science** (Plotly.js). Montréal. <https://plot.ly>
9. Mapzen / Amazon Web Services. **Terrain Tiles** (formato Terrarium). <https://registry.opendata.aws/terrain-tiles/>
10. OpenStreetMap contributors. **OpenStreetMap**. <https://www.openstreetmap.org/copyright>
11. CPRM/SGB — Serviço Geológico do Brasil. **Geologia e Recursos Minerais do Estado de Santa Catarina — Mapa Geológico 1:500.000 (SIG SC)**. <https://geosgb.sgb.gov.br>
12. ANP — Agência Nacional do Petróleo, Gás Natural e Biocombustíveis. **Dados abertos — poços**. <https://www.gov.br/anp>
13. Harris, C. R. et al. (2020). Array programming with NumPy. *Nature*, 585, 357–362.
14. Virtanen, P. et al. (2020). SciPy 1.0: fundamental algorithms for scientific computing in Python. *Nature Methods*, 17, 261–272.
15. Jordahl, K. et al. **GeoPandas**. Zenodo. <https://geopandas.org>; Gillies, S. et al. **Shapely** e **Rasterio**. <https://github.com/shapely/shapely>, <https://github.com/rasterio/rasterio>.

## Licença e uso

- **Código** (scripts de geração e JavaScript das páginas): licença **MIT** — ver [`LICENSE`](LICENSE).
- **Produtos gerados** (HTML, figuras, tabelas derivadas): **CC BY 4.0** — uso, adaptação e redistribuição permitidos com atribuição ao autor.
- **Dados de terceiros** incorporados mantêm as licenças e os termos das fontes originais (tabela em *Créditos e fontes de dados*).
- Os modelos são **interpretativos** e dependem da qualidade e da densidade dos dados de entrada; **não substituem** estudo geológico, hidrogeológico ou geotécnico de detalhe, nem devem ser usados como base única para decisões de engenharia, perfuração ou licenciamento.
- Fornecido “como está”, sem garantias de qualquer tipo.

## Créditos e fontes de dados

| Fonte | Uso | Termos |
|---|---|---|
| Levantamento de campo do autor (pontos, estruturas, geoquímica, MDE de drone) | Dados primários da área de Taió | CC BY 4.0 (autor) |
| CPRM/SGB — Mapa Geológico do Estado de Santa Catarina 1:500.000 (SIG SC) | Geologia regional, falhas, fraturas e diques regionais | Dados abertos CPRM/SGB — citar a fonte |
| ANP — Tabela de poços (dados abertos) | Poços de petróleo/gás (posição e profundidade total) | Dados abertos ANP — citar a fonte |
| Cadastro de poços do Sistema Aquífero Guarani (SAG) | Poços do SAG (posição e profundidade), arquivo KML do projeto | Citar a fonte original do cadastro |
| OpenStreetMap contributors | Rios, estradas e localidades | ODbL 1.0 — © OpenStreetMap contributors |
| Esri World Imagery | Imagem de satélite (tiles e textura) | Termos da Esri — uso com atribuição |
| CARTO / OpenTopoMap | Mapas base do webmap | Atribuição nos próprios mapas (OSM, SRTM, OpenTopoMap CC-BY-SA) |
| AWS Terrain Tiles (formato Terrarium) | Relevo e batimetria regionais (derivados de SRTM, GEBCO e outras fontes) | Atribuição conforme o provedor dos tiles |
| Plotly.js (MIT), Leaflet (BSD-2-Clause) | Bibliotecas de visualização embutidas/carregadas nas páginas | Licenças originais |

## Como citar

> JESUS, A. H. de. **Modelo 3D interativo — Taió**, versão 1.0. 2026. Projeto *Taió Plumbing System* — Mestrado em Geologia, UFSC. Disponível em: <https://thubaraleii.github.io/taio-plumbing-system-3d/visualizacao_web/viewer_3d_taio.html>.

## Autoria

**Afonso Henrique de Jesus** — Mestrado em Geologia, Universidade Federal de Santa Catarina (UFSC).
Projeto: *Architecture and Geochemical Evolution of the Taió Intrusive Plumbing System* (Taió, SC — Bacia do Paraná).
