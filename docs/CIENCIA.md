# Métodos científicos, critérios e limitações

## Convenções
* Latitude **planetocêntrica**; longitude **leste-positiva**. A API aceita `[-180, 180)` (padrão, `east_180`) ou `[0, 360)` com `"longitude_convention": "east_360"`, e converte para cada provedor (`science/coordinates.py`): ODE/GDS/PDS/CRISM em 0–360; Trek/STAC em −180..180.
* Regiões são círculos de `radius_km` (limites: Lua 25 km, Marte 50 km, Terra 25 km). O bbox que envolve o círculo é aberto em todas as longitudes quando atinge um polo, e dividido em dois quando cruza 0° (o antimeridiano ±180° não cruza nada em 0–360).

## Topografia (Lua: LOLA RDR; Marte: MOLA PEDR)
Dados numéricos medidos: tiros individuais do altímetro laser via ODE GDS (somente tiros válidos, flag 0). Nunca são usados tiles WMTS.
* Datum: LOLA = raio − esfera de 1737,4 km; MOLA PEDR = raio − areoide.
* Pontos recortados ao círculo numa projeção azimutal equidistante local.
* `regional_slope_degrees`/`regional_aspect_degrees`: plano de mínimos quadrados.
* `local_slope_degrees`: grade com célula = `slope_baseline_m` (adaptada à densidade), mediana por célula, diferenças centrais.
* `roughness_m`: RMS dos resíduos em relação ao plano. `coverage_fraction`: fração de células com dados.
* Se o GDS recusar a área ou o arquivo exceder o limite, o raio amostrado é reduzido à metade (até 3 vezes) e isso aparece em `sampled_radius_km` e nas limitações.

## Mineralogia — Lua (M3 L2)
1. ODE: footprints `REFIMG` que intersectam o ponto; prioridade aos que o contêm e com centro mais próximo.
2. Backplane LOC do L1B localiza o pixel mais próximo (busca grosso-fino com leituras Range de ~5 KB). Rejeita se o pixel estiver a mais de max(1 km, 3 pixels).
3. Janela de até 41×41 px lida numa única requisição; máscara: fora do raio, −999, ≤ 0, ≥ 1,5, bandas < 540 nm e > 2600 nm.
4. Indicadores: `IBD1000`, `IBD2000` (após Mustard et al. 2011), `legacy_bd1000/2000` (definição da biblioteca terrestre), `R750`, `slope_750_1550`.
5. Se não houver pixels válidos, tenta-se a observação seguinte; senão `insufficient_data`.

## Mineralogia — Marte (CRISM MTRDR)
Parâmetros-sumário calculados pela equipe CRISM (Viviano-Beck et al. 2014) lidos do cubo `SU` mapeado (pixel calculado analiticamente pela projeção equiretangular do cabeçalho). Bandas I/F do cubo `IF` alimentam as `legacy_bd` para comparação. Índices lunares não são aplicados a Marte.
Sem MTRDR no ponto: se existirem TRDR não projetados → `no_compatible_observations`; senão `no_coverage`.

## Critério de “detecção” (triagem)
Um indicador de profundidade de banda é marcado positivo quando: média da janela > 3 × erro-padrão (n efetivo = pixels/25, para correlação espacial ~5×5 px), mediana > 0 e ≥ 60 % dos pixels positivos. Isso detecta **uma absorção positiva**; não é abundância nem identificação mineral. Valores muito pequenos mas espacialmente consistentes podem passar — por isso o texto sempre diz “screening”.

## Análogos terrestres

### Como funciona hoje
* **Atributos pontuados:** só `legacy_bd1000` e `legacy_bd2000`, as únicas profundidades de banda com **a mesma fórmula** nos três corpos: `BD = (C − R_centro)/C`, `C = (R_esq + R_dir)/2`, bandas mais próximas de (1000; 800, 1300) nm e (2000; 1700, 2300) nm.
* **Origem lunar:** M3 L2 (reflectância, correção fotométrica e térmica da equipe M3), janela de pixels ao redor do ponto.
* **Origem marciana:** CRISM MTRDR I/F (correções fotométrica e atmosférica *volcano-scan*), mesmas 6 bandas.
* **Origem terrestre:** biblioteca de 90 sítios (`app/data/earth_emit_reference_library.json`), média de 10 km do composto mediano EMIT L2A (Earth Engine), herdada do backend anterior, com proveniência (sha256 do arquivo de origem).
* **Normalização:** nenhuma além da própria profundidade de banda (razão ao contínuo, insensível a offsets de calibração absoluta). Corte em zero aplicado **uma vez, à média da janela** (ver correção abaixo).
* **Similaridade:** distância euclidiana `d`; `similarity = 1 − d/(0,4·√n)`, pesos iguais. Serve **só para ordenar**; não é probabilidade.
* **Dados ausentes:** se um dos dois atributos falta, a seção fica `unavailable / insufficient_data` (nada é imputado). Sítios da biblioteca sem o atributo são excluídos.
* **Elegibilidade:** todos os 90 sítios entram; não há filtro por contexto geológico.
* **Proxies e não comparáveis** (listados, nunca pontuados): IBD lunares, BDI1000IR/LCPINDEX2/HCPINDEX2 do CRISM; maturidade lunar, hidratação/filossilicatos/carbonatos/sulfatos/gelo, ASTER TIR, NDVI.

### Correção aplicada (2026-11-06): ordem do corte em zero
A biblioteca guarda `max(0, média(BD))` (o valor bruto da média é negativo em 64 dos 90 sítios para 1 µm e em 8 para 2 µm). O código lunar e marciano fazia `média(max(0, BD))`, cortando **cada pixel** antes da média. Em janelas ruidosas isso empurra o valor para cima (a média de valores cortados é sempre ≥ ao corte da média) e torna a consulta incomparável com a biblioteca. Agora:
* o indicador mostra a profundidade **sem corte** (negativo = contínuo convexo = sem absorção, explicado em `interpretation`);
* o valor usado nos análogos é `max(0, média)`, exatamente como na biblioteca (`spectral.legacy_analog_input`);
* na Terra, o valor médio negativo é mostrado com o sinal e a mesma explicação; os análogos usam 0.
O teste estatístico de detecção passou a usar os valores sem corte.

### Explicabilidade acrescentada (sem mudar a pontuação)
`query_values`, `query_uncertainty` (erro-padrão com correção de correlação espacial), `differences` por análogo e atributo, `top5_distance_spread`, `indistinguishable_sites` (sítios cuja distância fica a até 2σ da do melhor) e `discrimination`:
* `low`: dispersão dos 5 primeiros < 0,05 **ou** ≥ 5 sítios indistinguíveis;
* `moderate`: dispersão < 0,10 **ou** ≥ 3 indistinguíveis;
* `adequate`: caso contrário.

### Achados da auditoria (não corrigidos — exigem decisão)
1. **A biblioteca mede mais vegetação/umidade que Fe²⁺.** 6 dos 7 basaltos de derrame (Deccan, Paraná, Karoo…) têm profundidade em 1 µm negativa e em 2 µm entre 0,19 e 0,50 — o contrário do esperado para piroxênio (bandas em 1 e 2 µm, 2 µm mais fraca). Esse padrão é típico de folhas e solo úmido (platô do infravermelho próximo; água líquida perto de 1,9–2,0 µm). Mediana de `legacy_bd2000` na biblioteca: 0,24; na Lua e em Marte: ~0–0,05.
2. **Consequência:** Lua e Marte caem sempre no canto de baixa profundidade, onde só há ~19 sítios (áridos). Numa grade de consultas típicas (bd1000 0–0,10; bd2000 0–0,05), apenas 21 sítios aparecem no top-5, e Etendeka, Hamersley e Escondida aparecem na maioria. O ranking diz mais sobre "superfície árida e pouco vegetada" do que sobre litologia.
3. **Instrumentos e correções diferentes:** EMIT (reflectância de superfície, 60 m), M3 (reflectância com correção térmica empírica que afeta 2 µm, 140–280 m) e CRISM (I/F com correção *volcano-scan*, 18–36 m). A comparação é de **forma**, não de composição, e não há validação cruzada entre instrumentos.
4. **Ambientes:** intemperismo espacial (Lua) e poeira (Marte) reduzem profundidades de banda; a Terra tem vegetação, água e atmosfera residual. Não há correção para isso.
5. **Proveniência incompleta da biblioteca:** datas e cenas EMIT não foram arquivadas; centroides dos sítios não foram guardados, então não dá para remedir.
6. **Repetibilidade da biblioteca ≈ separação do ranking.** Teste de autoconsistência em produção (2026-11-06): a própria Escondida, remedida hoje com o mesmo buffer de 10 km, sai em 1º lugar, mas só 0,004 unidades de profundidade de banda à frente da Candelaria (similaridade 0,989 vs 0,982); `legacy_bd1000` remedido = 0,044 contra 0,038 na biblioteca. Com buffer de 5 km ela cai para 2º. A incerteza do lado terrestre (~0,006) é maior que a da consulta (erro-padrão ~0,001) e do mesmo tamanho da dispersão dos 5 primeiros (0,008–0,053 nos casos reais). `indistinguishable_sites` considera só a incerteza da consulta e, por isso, é otimista.
7. **Escala da similaridade:** com `d_max = 0,4·√2`, diferenças de 0,03 viram 0,95 — números altos que parecem fortes. Mantido para não alterar o comportamento validado; o selo de discriminação e o aviso compensam.

### Evolução proposta (requer aprovação)
* **Remedir a biblioteca** com centroides e datas arquivados, máscara de vegetação (NDVI < 0,2 no composto EMIT) e de água; guardar o espectro médio completo de cada sítio, não só duas profundidades.
* **Escolher análogos pela geologia, não só por mineração:** basaltos áridos (Etendeka, Columbia em áreas secas), anortositos (Stillwater, Bushveld), vidros vulcânicos, regolitos de deserto, sítios de análogos marcianos consagrados (Atacama, Rio Tinto, Pilbara, Svalbard, Mojave).
* **Atributos com justificativa:** centro de banda em 1 µm e em 2 µm (posição, não só profundidade — distingue olivina/piroxênio de baixo e alto Ca), razão de áreas de banda (BAR), inclinação do contínuo; em Marte, só parâmetros CRISM que tenham equivalente EMIT com a mesma definição.
* **Comparação por espectro reamostrado** (ex.: ângulo espectral após remoção do contínuo) sobre a mesma grade de comprimentos de onda, com propagação de incerteza.
* **Validação:** (a) consistência — o mesmo sítio terrestre medido por EMIT em datas diferentes deve ficar indistinguível de si mesmo; (b) controle positivo — áreas lunares de composição conhecida (mare vs. terra alta; sítios Apollo/Luna com amostras) devem se separar; (c) controle negativo — consultas com ruído puro devem resultar em `discrimination = low`.
* **Critério de desempenho:** só exibir ranking como informativo quando a dispersão dos 5 primeiros superar 2σ da medida e o controle positivo separar mare de terra alta.
* **Riscos:** ruído instrumental tratado como sinal; vieses de seleção da biblioteca; leitura do ranking como indício de jazida.
* **Não fazer:** aprendizado de máquina sem rótulos de verdade de campo; converter similaridade em probabilidade.

## Sítios análogos terrestres (`terrestrial_analogs`, 2026-11-06)
Seção nova, separada do ranking por similaridade (que continua igual). Responde à pergunta "que lugares reais da Terra têm as famílias minerais que a região mostra?", com justificativa documentada.

**1. Evidência da região.** Usa só as detecções triadas que os pipelines já calculam (`detected` em cada indicador; critério da seção "Detecção"):
* Lua (M3): IBD1000 e IBD2000 detectados → piroxênio (basalto de mare ou norito); só IBD1000 → olivina ou vidro (ambíguo); nenhum → feldspático *ou* solo maduro (ambíguo, evidência "ampla").
* Marte (CRISM): cada parâmetro detectado indica sua família (OLINDEX3 olivina; LCP/HCPINDEX2 piroxênio; D2300 filossilicato Fe/Mg; BD2210_2 Al-OH/sílica hidratada; MIN2295_2480/MIN2345_2537 carbonato; BD2100_2/SINDEX2 sulfato; BD530_2 óxido férrico; BD1900_2 hidratação genérica; BDI1000IR máfico genérico; BD1435/BD1500_2 gelo). Famílias genéricas são descartadas quando uma específica explica a mesma absorção. A triagem não é identificação mineral (Viviano-Beck et al. 2014).
* Marte sem cobertura CRISM (e só por falta de cobertura, nunca por falha de provedor), entre ±60° de latitude: "contexto global" — a crosta marciana é basáltica (Bandfield et al. 2000); os sítios mostrados **não** são específicos da região e o aviso aparece em `notes`.

**2. Catálogo curado** (`app/data/terrestrial_analog_sites.json`, gerado por `scripts/build_analog_catalog.py`): 18 sítios, 16 verificados.
* Coordenadas tiradas da fonte citada em `coordinate_source`, com precisão declarada.
* Referências: cada DOI conferido no Crossref ou DataCite em 2026-11-06.
* `analog_basis` registra a força da afirmação:
  * artigo que usa o sítio como análogo daquele corpo;
  * fonte de simulante oficial;
  * análogo citado só de forma regional;
  * referência mineralógica;
  * divulgação.
* Entradas não verificadas (Lake Salda: coordenada sobre a unidade não publicada; Kunene: sem referência como análogo lunar) ficam no arquivo por transparência, mas o algoritmo nunca as oferece.
* Descartados na pesquisa por falta de fonte verificável:
  * Duluth;
  * San Gabriel;
  * Lac-Saint-Jean;
  * Bushveld (não pesquisado);
  * Yungay e MDRS (sem família mineral documentada em fonte aberta);
  * cones do cume do Mauna Kea;
  * picritos do Havaí.

**3. Correspondência.**
* Um sítio entra quando sua geologia documentada explica pelo menos uma família da região.
* A ordem segue, nesta prioridade:
  1. famílias específicas explicadas;
  2. total de famílias explicadas;
  3. força documental (`analog_basis`);
  4. concordância EMIT (abaixo);
  5. precisão da coordenada.
* No máximo 5 sítios, sem pontuação nem porcentagem.
* Famílias sem sítio no catálogo (ex.: gelo) aparecem em `unexplained_evidence`; não são preenchidas.

**4. Espectro, só onde é comparável.**
* O único atributo espectral com a mesma definição nos três corpos é a presença da banda de 3 pontos em 1 µm e 2 µm (`legacy_bd*` na região; `rock_bd*` no composto EMIT mascarado do sítio).
* Ela só é comparada quando o sítio tem medição EMIT com status `ok`, pelo menos 200 pixels de rocha e pelo menos 20% da área.
* Na Terra, a banda de 2 µm divide a janela com CO₂ atmosférico residual (~2,0 µm): por isso só se compara presença, nunca profundidade.
* NDVI, ASTER e Sentinel-2 nunca são usados como evidência de equivalência.

**5. Limitações.**
* A analogia é de família mineral, não de origem, abundância ou condição de formação.
* Superfícies terrestres têm intemperismo químico e não têm intemperismo espacial.
* Vários sítios são pequenos em relação ao pixel de 60 m, ou parcialmente vegetados.
* A ambiguidade lunar "feldspático × solo maduro" só se resolve com centro de banda, ainda não implementado.

## Remedição EMIT com máscaras (Terra)
O endpoint da Terra passou a devolver, em `earth_observation.emit_masked`, três variantes calculadas sobre a mesma região e escala (60 m, `bestEffort=False`):
* `raw`: mediana de todas as cenas, sem máscara (o mesmo composto da biblioteca antiga);
* `quality`: máscara por cena de reflectância fora de [0; 1,5] e de `aggregate_flag ≠ 0` do próprio EMIT L2A (nuvem, cirro, água, estrutura da estação, nuvem dilatada);
* `rock`: a máscara `quality` mais vegetação (NDVI ≥ 0,2), neve (NDSI > 0,4; Hall et al. 1995) e água (NDWI > 0; McFeeters 1996), todos calculados com bandas do próprio EMIT na mesma cena.

Em cada variante, a profundidade de banda é calculada por pixel e sem corte. Depois vêm média, desvio-padrão, mediana, contagem de pixels e fração positiva.

Proveniência registrada:
* id, data e zênite solar de cada cena;
* comprimento de onda real de cada banda usada (propriedade `reflectance_wavelengths`);
* pixels da região: válidos, de qualidade e de rocha;
* frações vegetada, de neve e de água (no composto de qualidade).

A fração de rocha é a parte da região com pelo menos uma cena que passa em todas as máscaras. Por isso, vegetação sazonal é removida pela cena seca, e vegetação esparsa com NDVI < 0,2 continua presente.

Os limiares são valores de triagem convencionais e vêm em `mask_rules`. Valores ausentes ficam ausentes: um sítio sem pixel de rocha devolve `no_rock_pixels`, nunca zero.

`scripts/remeasure_library.py` remede os 90 sítios da biblioteca e os sítios análogos por esse endpoint, um de cada vez. A biblioteca de produção **não** é substituída. O resultado fica em `data/remeasurement/` como candidato, e a comparação antigo × corrigido está em `data/remeasurement/COMPARACAO.md`.

## Confiança
`confidence.level` é calculado a partir dos critérios aplicáveis (lista em `confidence.criteria`):
* altimetria: ≥ 30 tiros; cobertura de células ≥ 0,3; raio pedido integralmente amostrado;
* espectroscopia: pixel dentro da tolerância; ≥ 25 pixels válidos; incidência solar ≤ 70° (quando conhecida).

Todos atendidos → `high`; ≥ 2/3 → `moderate`; abaixo → `low`; nenhum critério aplicável → `not_assessed`. Sem mineralogia disponível o nível máximo é `moderate`.

## Limitações conhecidas
* M3: correção térmica empírica (região de 2 µm em terreno quente); ~140/280 m/px; correlação espacial.
* CRISM: footprints de ~10 km; parâmetros-sumário sensíveis a ruído e CO2 residual; I/F ≠ reflectância de superfície EMIT.
* Biblioteca terrestre: datas de extração EMIT não foram arquivadas pelo pipeline antigo.
* Diviner (Lua) e DTMs USGS são **descobertos e listados**, não lidos.
* Terra depende de credencial Earth Engine; não foi testada com dados reais neste ambiente.
