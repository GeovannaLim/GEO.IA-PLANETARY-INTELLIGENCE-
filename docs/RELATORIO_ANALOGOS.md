# Relatório — sítios análogos terrestres e remedição da biblioteca (2026-11-06)

## Resultado
Quem seleciona uma região da Lua ou de Marte agora recebe `terrestrial_analogs`: locais reais da Terra com coordenadas, geologia, justificativa, semelhanças, diferenças, fontes com DOI e limitações. A correspondência é **geológica**: as famílias minerais detectadas na região são comparadas à geologia publicada de cada sítio. Dados espectrais entram só onde a definição é a mesma nos dois corpos. Método em `docs/CIENCIA.md#sítios-análogos-terrestres-terrestrial_analogs-2026-11-06`.

Nada foi alterado na fórmula de similaridade nem na biblioteca de produção.

## Frente 1 — Catálogo de análogos (`app/data/terrestrial_analog_sites.json`)
18 sítios, 16 verificados. Os 29 DOIs do catálogo, e o de Bandfield et al. 2000 usado no contexto global, foram conferidos no Crossref ou DataCite; 3 referências sem DOI (McKay 1994, ESA 2017, NASA NTRS) ficam com a URL. As coordenadas vêm da fonte registrada em cada sítio.

| Corpo | Família | Sítios (base documental) |
|---|---|---|
| Lua | basalto/piroxênio | Merriam Crater (fonte do JSC-1), Kaʻū (análogo regional), Timanfaya (só divulgação da ESA) |
| Lua | olivina/vidro | Craters of the Moon (FINESSE), Merriam |
| Lua | anortosito | Stillwater, Shawmere (fonte do OB-1), Sittampundi (fonte do LSS-ISAC-1) |
| Lua | norito | Stillwater, Sudbury |
| Marte | olivina, serpentina, carbonato | Samail BT1B, Twin Sisters |
| Marte | sulfato, óxido férrico | Río Tinto, Kaʻū, Cuprite (referência mineralógica) |
| Marte | sílica hidratada / Al-OH | El Tatio, Kaʻū, Cuprite, Dresser |
| Marte | basalto, solo alterado | Lonar, Kaʻū, Puʻu Nēnē (fonte do JSC Mars-1) |

**Não oferecidos:**
* Lake Salda: sem coordenada publicada sobre a unidade de hidromagnesita.
* Kunene: sem referência como análogo lunar.

**Descartados por falta de fonte verificável:** Duluth, San Gabriel, Lac-Saint-Jean, Bushveld (não pesquisado), Yungay, MDRS, cones do cume do Mauna Kea, picritos do Havaí.

**Teste com dados reais** (local antes do deploy e em produção depois):

| Região | Evidência da região | Sítios oferecidos |
|---|---|---|
| Lua 14.64/−24.07 e 25.8/−15.2 | piroxênio | Merriam, Sudbury, Stillwater, Kaʻū, Timanfaya |
| Marte Jezero | olivina, Fe/Mg-filossilicato, Al-OH/sílica, óxido férrico; gelo sem análogo | Samail, Dresser, Twin Sisters, Kaʻū, Puʻu Nēnē |
| Marte 5.81/−31.66 | olivina, sulfato, óxido férrico | Río Tinto, Kaʻū, … |
| Marte 0.99/−31.47, sem CRISM | contexto global (aviso explícito) | Puʻu Nēnē, Lonar, Kaʻū |
| Marte −85/150 | — | nenhum (polar, sem contexto global) |

**Medição EMIT dos 18 sítios:** 11 têm rocha exposta suficiente para comparar presença de banda. Ficaram fora por vegetação, água ou pouca exposição: Shawmere, Stillwater, Sudbury, Sittampundi, Lonar, Timanfaya e Lake Salda.
* Merriam: 1 µm coincide com a Lua; 2 µm não é detectado na Terra.
* Kaʻū: coincide nas duas bandas.

## Frente 2 — Remedição dos 90 sítios
* **Coordenadas** recuperadas de `deposits_master.json`: 90 de 90 encontradas.
  * Precisão pelas casas decimais escritas: 31 alta (≤ 0,1 km), 15 moderada, **44 baixa (≥ 1 km)**.
  * A fonte original de cada coordenada não estava registrada.
  * Arquivo: `data/remeasurement/library_sites_coordinates.json`.
* **Medição** feita pelo endpoint da Terra em produção, raio de 10 km, um sítio por vez.
  * 2.108 cenas EMIT registradas com id e data (2022-08-11 a 2026-08-30).
  * Resultado: 89 ok, 1 sem pixel de rocha (Bathurst).
  * Duas falhas transitórias (Cuajone, Barberton) foram repetidas e passaram.
  * Arquivo: `data/remeasurement/library_emit_remeasured.json`. Tabela por sítio: `data/remeasurement/COMPARACAO.md`.

| Achado | Valor |
|---|---|
| Correlação NDVI × bd2000 sem máscara | **0,75** (n=90) |
| Correlação NDVI × bd2000 só rocha | 0,46 (n=89): ainda há vegetação residual |
| Mediana de bd2000 bruto − rocha | 0,078 |
| Sítios com 2 µm detectado: bruto → rocha | **63 → 27** |
| Sítios com < 20% de rocha | 32 de 90 |
| Exemplos de basalto (bd2000 bruto → rocha) | Paraná 0,553 → −0,028 (1% rocha); Columbia 0,382 → 0,151; Deccan 0,170 → 0,044 |
| Máscara de qualidade do EMIT | mediana de 99,9% de pixels válidos; < 50% em 11 sítios tropicais ou úmidos (nuvem) |
| **Reprodutibilidade da biblioteca antiga** | mediana de \|Δ bd2000\| = **0,051** e \|Δ bd1000\| ≈ 0,02, sem relação com a precisão da coordenada. O código antigo rodado hoje reproduz a nova medição bruta (0,008). Os valores de produção não são reproduzíveis a partir das coordenadas e do código disponíveis. |

**Efeito no ranking atual (simulação; a produção não foi alterada).**
* A biblioteca candidata tem 58 sítios com ≥ 20% de rocha e valores de rocha.
* Nos 4 casos reais, o top-5 muda quase inteiro, e a discriminação continua "baixa" (a Lua 25.8/−15.2 cai de "moderada" para "baixa").
* Conclusão: com dados corrigidos, a distância sobre duas profundidades de banda continua sem separar os sítios. O ranking deve seguir rotulado como ilustrativo, e a correspondência geológica é o caminho informativo.

## Testes
* Backend local: **94 aprovados**, 3 pulados (ao vivo), `pyflakes` limpo. Inclui 8 testes novos de correspondência, contexto global, ausência sem preenchimento, pt-BR e o pipeline da Terra com Earth Engine simulado.
* Real local (antes do deploy): 5 regiões da Lua e de Marte pelos pipelines completos.
* Produção (`cc19126`): **33/33**, incluindo os testes novos H (análogos na Lua, em Marte, polar e contexto global) e D (registro EMIT mascarado).

## Limitações
* A comparação espectral é só de presença de banda. Centros de banda, que resolveriam piroxênio × olivina e mare × norito, não estão implementados.
* A máscara de NDVI não remove vegetação seca, que absorve perto de 2,1 µm.
* Várias coordenadas são pontos de referência, e não pontos sobre a unidade. A precisão declarada vai de 0,2 a 15 km.
* "Feldspático × solo maduro" na Lua é ambíguo.
* Gelo em Marte não tem análogo no catálogo.
* O Skip ainda não exibe a seção: o prompt está em `docs/PROMPT_SKIP_ANALOGOS.md`.

## Próximos passos (exigem aprovação)
1. Aplicar `docs/PROMPT_SKIP_ANALOGOS.md` no Skip e testar pela interface.
2. Decidir sobre a biblioteca de produção: substituí-la pela candidata não resolve a discriminação. Sugestão: manter o ranking como ilustrativo e destacar os sítios análogos.
3. Centro de banda em 1 e 2 µm nos três corpos, com controles positivo e negativo.
4. Pontos sobre a unidade para Lake Salda, Stillwater e Sudbury, e um sítio de anortosito árido com referência lunar.
