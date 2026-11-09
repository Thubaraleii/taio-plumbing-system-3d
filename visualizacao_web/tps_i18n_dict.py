"""Dicionario PT -> EN das interfaces do projeto Taio Plumbing System.
DICT: texto inteiro (apos trim). RX: regex (padrao, flags, substituicao com $1..). FRAG: substrings (aplicadas por ultimo)."""

DICT = {
    # ---------------- comum ----------------
    "Criado por Afonso Henrique de Jesus": "Created by Afonso Henrique de Jesus",
    "Corte": "Cut", "Leste → Oeste": "East → West", "Oeste → Leste": "West → East", "Norte → Sul": "North → South", "Sul → Norte": "South → North",
    "Animar corte": "Animate cut", "Cor": "Color", "Hipsometria": "Hypsometry", "Geologia": "Geology", "Satélite": "Satellite",
    "Camadas": "Layers", "Topografia": "Topography", "Sólido": "Solid", "Campo": "Field", "Geoquímica": "Geochemistry",
    "Estruturas": "Structures", "Falha CPRM": "CPRM fault", "Fratura CPRM": "CPRM fracture", "Falha de campo": "Field fault",
    "Vista": "View", "Girar": "Rotate", "Exagero vertical": "Vertical exaggeration", "3× (padrão)": "3× (default)",
    "Tema": "Theme", "Escuro": "Dark", "Claro": "Light", "Mapa": "Map", "Textura": "Texture",
    "Depósito quaternário": "Quaternary deposit", "Soleira": "Sill", "Dique": "Dike", "Diques": "Dikes",
    "Elevação (m)": "Elevation (m)", "Poços": "Wells", "Poço": "Well", "Pontos de campo": "Field points",
    "Geoquímica (Alto/Baixo-Ti)": "Geochemistry (High/Low-Ti)", "Poços (ANP/SAG)": "Wells (ANP/SAG)",
    "Lineamento positivo": "Positive lineament", "Lineamento negativo": "Negative lineament",
    "Lineamento Positivo": "Positive lineament", "Lineamento Negativo": "Negative lineament",
    "Falha (CPRM)": "Fault (CPRM)", "Fratura (CPRM)": "Fracture (CPRM)", "Diques (CPRM)": "Dikes (CPRM)",
    "Área de estudo (Taió)": "Study area (Taió)", "Outras unidades": "Other units", "Sem dado": "No data",
    "Geologia SC (CPRM)": "SC geology (CPRM)", "Mapa geológico atualizado": "Updated geological map",
    "Satélite (Esri)": "Satellite (Esri)", "Relevo/Topográfico": "Relief/Topographic", "OSM Padrão": "OSM Standard",
    "Soleira (diabásio)": "Sill (diabase)", "Encaixante — Teresina": "Host rock — Teresina", "Encaixante — Serra Alta": "Host rock — Serra Alta",
    "Encaixante — Irati": "Host rock — Irati", "Encaixante — Palermo": "Host rock — Palermo", "Encaixante — Rio Bonito": "Host rock — Rio Bonito",
    "Encaixante — indefinida": "Host rock — undefined", "Outra/indefinida": "Other/undefined", "Outra estrutura": "Other structure",
    "Acamamento sedimentar": "Sedimentary bedding", "Fratura/falha": "Fracture/fault", "Dique provável (relevo +)": "Probable dike (positive relief)",
    "Dique confirmado": "Confirmed dike", "Falha/dique ambíguo (relevo −)": "Ambiguous fault/dike (negative relief)",
    "Contato sill/encaixante": "Sill/host-rock contact", "Fábrica interna da intrusão": "Intrusion internal fabric",
    "Lineamentos (satélite)": "Lineaments (satellite)", "Lineam. satélite": "Satellite lineam.",
    "Sim": "Yes", "Não": "No",
    # ---------------- hub ----------------
    "TAIÓ — Sistema Intrusivo · Plumbing System": "TAIÓ — Intrusive System · Plumbing System",
    "Modelagem do sistema intrusivo em profundidade": "Depth modelling of the intrusive system",
    "Modelagem 3D e seção transversal interativa do sistema intrusivo (sill/dique) de Taió — Mestrado em Geologia, UFSC.":
        "3D modelling and interactive cross-section of the Taió intrusive system (sill/dike) — MSc in Geology, UFSC.",
    "Mapa em tela cheia com zoom/pan contínuo (Leaflet): pontos de campo, mapa geológico atualizado, sill/dique, dados estruturais e camadas de referência (rios/estradas/localidades).":
        "Full-screen map with continuous zoom/pan (Leaflet): field points, updated geological map, sill/dike, structural data and reference layers (rivers/roads/localities).",
    "Painel com dados geoquímicos do sistema intrusivo de Taió, com visualizações para exploração dos elementos e relações geoquímicas.":
        "Dashboard with geochemical data of the Taió intrusive system, with visualizations to explore the elements and geochemical relationships.",
    "Seção 2D interativa": "Interactive 2D section",
    "Mapa em planta + seção transversal sincronizados, com linha de corte rotacionável, pontos de campo, dados estruturais e camadas de referência (rios/estradas/localidades).":
        "Plan-view map + synchronized cross-section, with a rotatable cut line, field points, structural data and reference layers (rivers/roads/localities).",
    "Modelo 3D interativo": "Interactive 3D model",
    "Cubão 3D com topografia real, corpos intrusivos, formações sedimentares e ferramenta de corte com 4 direções. Modos de cor: hipsometria, mapa geológico e satélite.":
        "3D block with real topography, intrusive bodies, sedimentary formations and a cutting tool with 4 directions. Color modes: hypsometry, geological map and satellite.",
    "Cinco blocos 3D de detalhe — Bela Vista, Pechincha, Domínio norte, Domínio sul e o Horst (basculamento esquemático com grabens subordinados) — com relevo real, empilhamento sedimentar, soleiras, diques, lineamentos, pontos de campo e poços.":
        "Five detailed 3D blocks — Bela Vista, Pechincha, North domain, South domain and the Horst (schematic tilting with subordinate grabens) — with real relief, sedimentary stack, sills, dikes, lineaments, field points and wells.",
    "3D regional": "Regional 3D",
    "Panorama 3D do norte de Santa Catarina (Alto Vale, Serra, Itajaí e plataforma), com relevo e batimetria, lineamentos, poços ANP/SAG e a área de Taió — base para a reconstrução cinemática do Gondwana.":
        "3D panorama of northern Santa Catarina (Alto Vale, Serra, Itajaí and shelf), with relief and bathymetry, lineaments, ANP/SAG wells and the Taió area — basis for the kinematic reconstruction of Gondwana.",
    "Identidade visual": "Visual identity",
    "Vermelho reservado para intrusões e condutos magmáticos; azuis para as unidades sedimentares e a interface. Tipografia: Montserrat (títulos), Inter (texto) e IBM Plex Mono (dados).":
        "Red is reserved for intrusions and magmatic conduits; blues for the sedimentary units and the interface. Typography: Montserrat (headings), Inter (text) and IBM Plex Mono (data).",
    # ---------------- hub (linha original) ----------------
    "Taió Plumbing System — Modelos 3D/2D": "Taió Plumbing System — 3D/2D Models",
    "Mapa em tela cheia com zoom/pan contínuo (Leaflet): pontos de campo, mapa geológico real (CPRM), sill/dique, dados estruturais e camadas de referência (rios/estradas/localidades).":
        "Full-screen map with continuous zoom/pan (Leaflet): field points, real geological map (CPRM), sill/dike, structural data and reference layers (rivers/roads/localities).",
    "Cubão 3D com topografia real, corpos intrusivos, formações sedimentares e ferramenta de corte com 4 direções. Modos de cor: hipsometria, geologia real (CPRM) e satélite.":
        "3D block with real topography, intrusive bodies, sedimentary formations and a cutting tool with 4 directions. Color modes: hypsometry, real geology (CPRM) and satellite.",
    # ---------------- titulos ----------------
    "Webmap Taió — Sistema Alimentador": "Taió Webmap — Feeder System", "Webmap Taió": "Taió Webmap",
    "Dashboard Geoquímico — Taió": "Geochemical Dashboard — Taió", "Dashboard Geoquímico": "Geochemical Dashboard",
    "Seção 2D interativa — Taió Plumbing System": "Interactive 2D section — Taió Plumbing System",
    "Modelo 3D — Taió Plumbing System": "3D Model — Taió Plumbing System", "Modelo 3D": "3D Model",
    "Recorte regional dos furos — Taió Plumbing System": "Regional borehole cutout — Taió Plumbing System",
    "— norte de SC": "— northern SC", "— furos de Taió": "— Taió boreholes", "Recorte regional": "Regional cutout",
    # ---------------- webmap ----------------
    "Mapa base": "Base map", "Geologia Taió": "Taió geology", "Área de Taió": "Taió area",
    "Ligar/desligar toda a camada": "Toggle the whole layer", "Ligar/desligar só este item": "Toggle this item only",
    "Estrutural": "Structural", "Geologia SC": "SC geology", "Estruturas CPRM": "CPRM structures", "Diques CPRM": "CPRM dikes",
    "Falhas (CPRM)": "Faults (CPRM)", "Fraturas (CPRM)": "Fractures (CPRM)", "Lineam. locais": "Local lineam.",
    # ---------------- webmap (2) ----------------
    "— Sistema Alimentador": "— Feeder System", "Sill/Dique": "Sill/Dike", "Panorama regional": "Regional panorama",
    "Legenda (clique p/ ligar/desligar)": "Legend (click to toggle)", "Geologia regional (CPRM SC)": "Regional geology (CPRM SC)",
    "Estruturas CPRM (falhas/fraturas)": "CPRM structures (faults/fractures)", "Falha": "Fault", "Fratura": "Fracture",
    "Dobra / outra": "Fold / other", "Dique CPRM": "CPRM dike", "Alto-Ti": "High-Ti", "Baixo-Ti": "Low-Ti",
    "Dados estruturais": "Structural data", "Positivo": "Positive", "Negativo": "Negative", "Rios": "Rivers", "Rio": "River",
    "Estradas": "Roads", "Estrada": "Road", "Localidades": "Localities", "Localidade": "Locality",
    # ---------------- dashboard ----------------
    "Lista de dados": "Data list", "Buscar por nome, litologia...": "Search by name, lithology...", "Amostra de referência": "Reference sample",
    "Corpos intrusivos — área, volume & classificação": "Intrusive bodies — area, volume & classification", "Área": "Area", "Polígonos": "Polygons",
    "Classificação Ti": "Ti classification", "Classificação de Ti": "Ti classification",
    "Coluna estratigráfica estimada (furo virtual)": "Estimated stratigraphic column (virtual borehole)",
    "Selecione um ponto na lista ou no mapa para ver o empilhamento esperado ali.": "Select a point in the list or on the map to see the expected stack there.",
    "TAS — Total Álcalis vs Sílica": "TAS — Total Alkali vs Silica", "basáltico": "basaltic", "Tefrítico": "Tephritic", "Fonolítico": "Phonolitic",
    "Sub-alcalino/Toleiítico": "Sub-alkaline/Tholeiitic", "AFM — Álcalis / FeOt / MgO": "AFM — Alkalis / FeOt / MgO",
    "Toleítico": "Tholeiitic", "Cálcio-alcalino": "Calc-alkaline",
    "Critérios de Peate et al. (1992) — 12 critérios": "Peate et al. (1992) criteria — 12 criteria",
    "faixas = janela de cada magma-tipo · pontos = amostras": "bands = window of each magma type · points = samples",
    "Matrizes de conformidade (Peate et al., 1992)": "Conformity matrices (Peate et al., 1992)",
    "pontos = nº de critérios (0–12) dentro da janela de cada magma-tipo do grupo · ordenado pela melhor pontuação":
        "points = number of criteria (0–12) within the window of each group magma type · sorted by best score",
    "ETR e discriminação tectônica": "REE and tectonic discrimination",
    "normalização: manto primitivo, McDonough & Sun (1995) · só amostras com os 14 ETR analisados":
        "normalization: primitive mantle, McDonough & Sun (1995) · only samples with all 14 REE analyzed",
    "Discriminação tectônica — Ti/V (Shervais, 1982)": "Tectonic discrimination — Ti/V (Shervais, 1982)",
    "linhas = razões Ti/V 10, 20, 50 e 100 · Ti = TiO₂ × 5990": "lines = Ti/V ratios 10, 20, 50 and 100 · Ti = TiO₂ × 5990",
    "Diagramas de Harker": "Harker diagrams", "Distribuição por litologia": "Distribution by lithology",
    "Óxidos maiores (% em peso)": "Major oxides (wt%)", "Elementos traço (ppm)": "Trace elements (ppm)",
    "Mín": "Min", "Máx": "Max", "Média": "Mean", "Média Alto-Ti": "Mean High-Ti", "Média Baixo-Ti": "Mean Low-Ti", "Distribuição": "Distribution",
    "Faixa vai do mínimo ao máximo observado ·": "Range goes from the observed minimum to the maximum ·", "média ·": "mean ·",
    "mediana · médias por classificação Ti calculadas só sobre as amostras de cada grupo": "median · means by Ti classification computed only over the samples of each group",
    "Campo (Taió)": "Field (Taió)", "Geoquímica (amostras brutas)": "Geochemistry (raw samples)",
    "Tema: Escuro": "Theme: Dark", "Tema: Claro": "Theme: Light",
    # ---------------- dashboard (2) ----------------
    "Nome": "Name", "Litologia": "Lithology", "Alto": "High", "Baixo": "Low", "dique": "dike",
    "Furo (Soleira Bela Vista)": "Borehole (Bela Vista sill)", "Corpo": "Body", "Soleira (sill)": "Sill",
    "Picrobasalto": "Picrobasalt", "Basalto": "Basalt", "Andesito": "Andesite", "Dacito": "Dacite", "Riolito": "Rhyolite",
    "Traqui-": "Trachy-", "basalto": "basalt", "Traquiandesito": "Trachyandesite", "andesito": "andesite", "Traquito": "Trachyte",
    "Traquidacito": "Trachydacite", "Basanito": "Basanite", "Fono-": "Phono-", "Tefrito": "Tephrite", "Fonolito": "Phonolite",
    "Foiditos": "Foidites", "Alcalino": "Alkaline", "Metaluminoso": "Metaluminous", "Peraluminoso": "Peraluminous", "Peralcalino": "Peralkaline",
    "Elementos terras raras": "Rare earth elements", "Amostra / manto primitivo": "Sample / primitive mantle", "Elemento": "Element",
    "Escuro (CartoDB Dark)": "Dark (CartoDB Dark)", "Rico (CartoDB Voyager)": "Rich (CartoDB Voyager)",
    # ---------------- secao 2D ----------------
    "Linha de corte": "Cut line", "Horizontal (O↔L)": "Horizontal (W↔E)", "Diagonal (SO↔NE)": "Diagonal (SW↔NE)", "Vertical (S↔N)": "Vertical (S↔N)",
    "Diagonal (SE↔NO)": "Diagonal (SE↔NW)", "Traçado A (SO↔NE)": "Trace A (SW↔NE)", "Traçado B (N↔S)": "Trace B (N↔S)",
    "Traçado C (L↔O)": "Trace C (E↔W)", "Traçado D (L↔O)": "Trace D (E↔W)", "Todos os traçados": "All traces",
    "Geologia (atualizado)": "Geology (updated)", "Auto (preencher)": "Auto (fill)", "1× (real)": "1× (true scale)",
    "Posição do corte": "Cut position", "ou clique no mapa": "or click on the map",
    "Distância ao longo da seção (km)": "Distance along the section (km)", "Mapa (clique p/ mover)": "Map (click to move)",
    "Seção transversal": "Cross-section", "Voltar à seção": "Back to the section",
    "Estrutura": "Structure", "Vista 3D": "3D view", "Exagero vertical (1x = escala real)": "Vertical exaggeration (1x = true scale)",
    # ---------------- zooms ----------------
    "Recorte": "Area", "(C) Domínio norte": "(C) North domain", "(D) Domínio sul": "(D) South domain",
    "Sem corte": "No cut", "Leste–Oeste (X)": "East–West (X)", "Norte–Sul (Y)": "North–South (Y)", "Inverter lado": "Flip side",
    "Subir / descer": "Raise / lower", "Planos de falha": "Fault planes", "Traços": "Traces", "Rótulos": "Labels",
    "Recorte regional (furos) ↗": "Regional cutout (boreholes) ↗", "Base (não modelada)": "Base (not modeled)",
    "Falhas do horst": "Horst faults", "Falhas subordinadas (grabens)": "Subordinate faults (grabens)",
    "Limite do horst (baixo)": "Horst boundary (low)", "Falha do horst (plano)": "Horst fault (plane)",
    "Falha subordinada do graben (plano)": "Graben subordinate fault (plane)",
    # ---------------- regional furos ----------------
    "Bloco (unidades)": "Block (units)", "Superfícies das unidades": "Unit surfaces", "Área / raio": "Area / radius", "Lineam. locais": "Local lineam.",
    "Superfícies indicativas: extrapolação do modelo regional de Taió (sem calibração nos poços — a tabela ANP não traz topos/litologia).":
        "Indicative surfaces: extrapolation of the Taió regional model (not calibrated on the wells — the ANP table has no tops/lithology).",
    "Poço (boca → fundo)": "Well (wellhead → bottom)", "Bocas dos poços": "Wellheads", "Fundo do poço (TD)": "Well bottom (TD)",
    "Poços no recorte": "Wells in the cutout", "Fundo (cota)": "Bottom (elevation)",
    "Cota do fundo = relevo (Terrain Tiles) na boca − profundidade total. A tabela ANP não informa topos de formação nem litologia, por isso o embasamento e as unidades não são amarrados aos poços aqui. Para calibrar, preencha":
        "Bottom elevation = relief (Terrain Tiles) at the wellhead − total depth. The ANP table gives no formation tops or lithology, so the basement and units are not tied to the wells here. To calibrate, fill in",
    "(poco, formacao, prof_topo_m) e regenere.": "(poco, formacao, prof_topo_m) and regenerate.",
    # ---------------- panorama ----------------
    "Satélite": "Satellite", "Hipsometria + batimetria": "Hypsometry + bathymetry", "Lineamentos": "Lineaments", "Corpos / Taió": "Bodies / Taió",
    "Oblíqua": "Oblique", "Planta": "Plan", "Perfil O→L": "Profile W→E", "Perfil S→N": "Profile S→N", "Direções": "Directions", "Rosetas": "Rosettes",
    "Buffer de 5 km (Taió)": "5 km buffer (Taió)", "Direções dos lineamentos — comparar": "Lineament directions — compare",
    "Roseta 1": "Rosette 1", "Roseta 2": "Rosette 2", "Panorama inteiro": "Whole panorama", "Taió + buffer de 5 km": "Taió + 5 km buffer",
    "Lineamentos locais (+)": "Local lineaments (+)", "Lineamentos locais (−)": "Local lineaments (−)",
    "SO": "SW", "NO": "NW", "L": "E", "O": "W",
    "Direção média:": "Mean direction:", "Classe dominante:": "Dominant class:", "Direção preferencial": "Preferred direction",
    "Direção subordinada": "Subordinate direction", "Limpar": "Clear", "mesma escala radial nas duas": "same radial scale on both",
    "Cada roseta tem seus próprios conjuntos (marque o que quer comparar) e sua própria seleção. Roseta por comprimento (km) em classes de 10°, simétrica (0–180°).":
        "Each rosette has its own sets (tick what you want to compare) and its own selection. Rosette by length (km) in 10° classes, symmetric (0–180°).",
    "Preferencial": "Preferred", "= classe de maior comprimento (±10°);": "= class with the greatest length (±10°);", "subordinada": "subordinate",
    "= a maior classe a pelo menos 30° da preferencial. A seleção da roseta 1 aparece em": "= the largest class at least 30° from the preferred one. Rosette 1's selection appears in",
    "branco": "white", "no 3D e a da roseta 2 em": "in the 3D view and rosette 2's in", "amarelo": "yellow",
    "; o restante dos conjuntos marcados fica em cinza.": "; the remaining selected sets stay grey.",
}

RX = [
    [r"1 wells", "", "1 well"],
    [r"^Opacidade: ", "", "Opacity: "],
    [r"^Corte \((.*?)\) em ([XY]): ", "", "Cut ($1) at $2: "],
    [r"^Média: ", "", "Mean: "],
    [r"^(\d+) de (\d+) registros$", "", "$1 of $2 records"],
    [r"^Conformidade com os 6 critérios de Peate — (.*?) \((\d+) amostras\)$", "", "Conformity with the 6 Peate criteria — $1 ($2 samples)"],
    [r"Padrões de ETR normalizados ao manto primitivo \((\d+) amostras\)", "", "REE patterns normalized to primitive mantle ($1 samples)"],
    [r"^Apanhado estatístico — elementos químicos \((\d+) amostras\)", "", "Statistical summary — chemical elements ($1 samples)"],
    [r"^(\d+) amostras \(QMC_TAIO_TODOS\) · campos de referência digitalizados aproximados", "", "$1 samples (QMC_TAIO_TODOS) · approximate digitized reference fields"],
    [r"^Raio dos (\d+) poços \((\d+) km\)$", "", "Radius of the $1 wells ($2 km)"],
    [r"^Litologia: ", "", "Lithology: "], [r"^Tipo: ", "", "Type: "], [r"^Qualidade: bom$", "", "Quality: good"],
    [r"^Qualidade: revisar$", "", "Quality: to review"], [r"^Qualidade: recuperado_medidas_TI$", "", "Quality: recovered TI measurements"],
    [r"^Qualidade: ", "", "Quality: "], [r"^Geoquímica: Sim \(Alto\)", "", "Geochemistry: Yes (High)"], [r"^Geoquímica: Sim \(Baixo\)", "", "Geochemistry: Yes (Low)"],
    [r"^Geoquímica: ", "", "Geochemistry: "], [r"^Classificação: ", "", "Classification: "], [r"^Formação: ", "", "Formation: "],
    [r"^Azimute/Strike: ", "", "Azimuth/Strike: "], [r"^Azimute: ", "", "Azimuth: "], [r"^Comprimento: ", "", "Length: "],
    [r"^Formação predominante: ", "", "Predominant formation: "], [r"^Profundidade: ", "", "Depth: "],
    [r"^Distância: ", "", "Distance: "], [r"^Elevação: ", "", "Elevation: "], [r"^Espessura: ", "", "Thickness: "],
]

FRAG = [
    ["sill_diabasio_cprm", "diabase sill (CPRM)"], ["sill_diabasio", "diabase sill"], ["dique_cprm", "dike (CPRM)"],
    ["encaixante_sedimentar", "host rock (sedimentary)"], ["encaixante_rio_bonito", "host rock — Rio Bonito"],
    ["encaixante_serra_alta", "host rock — Serra Alta"], ["encaixante_teresina", "host rock — Teresina"],
    ["encaixante_palermo", "host rock — Palermo"], ["encaixante_irati", "host rock — Irati"], ["Alto-Ti", "High-Ti"], ["Baixo-Ti", "Low-Ti"],
    ["afloramento_descritivo", "descriptive outcrop"], ["atitude_acamamento", "bedding attitude"], ["atitude_de_contato", "contact attitude"],
    ["bloco_rolado_ou_transportado", "rolled/transported block"], ["contato_litologico", "lithological contact"],
    ["estrutura_interna_intrusao", "intrusion internal structure"], ["feicao_estrutural_secundaria", "secondary structural feature"],
    ["ponto_catalogo_sem_descricao", "catalog point without description"],
    ["Leste-Oeste", "East-West"], ["Oeste-Leste", "West-East"], ["Norte-Sul", "North-South"], ["Sul-Norte", "South-North"],
    ["(esquemático)", "(schematic)"], ["Domínio norte", "North domain"], ["Domínio sul", "South domain"],
    ["pontos de campo", "field points"], ["amostras de geoquímica", "geochemistry samples"], [" poços", " wells"], [" poço", " well"],
    ["Relevo/batimetria", "Relief/bathymetry"], ["satélite:", "satellite:"], ["área ≈", "area ≈"], [" lineamentos", " lineaments"],
    ["Conjuntos marcados", "Selected sets"], ["% em peso", "wt%"], ["% peso", "wt%"], ["amostras", "samples"], ["amostra", "sample"],
    ["critérios", "criteria"], ["s/ período", "no period"], ["s/ dado", "n/a"],
    ["Depósitos colúvio-aluvionares", "Colluvial-alluvial deposits"], ["Depósitos aluvionares", "Alluvial deposits"],
    ["Depósitos de planície de maré arenosos", "Sandy tidal-flat deposits"], ["Gnaisses Granulíticos", "Granulitic Gneisses"],
    ["Granito ", "Granite "], ["rítmica", "rhythmic"], ["pelítica", "pelitic"],
]
