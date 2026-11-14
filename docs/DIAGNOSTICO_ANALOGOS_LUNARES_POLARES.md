# Diagnóstico — análogos terrestres para bases no polo sul lunar (Fase 1, 2026-11-14)

**Baseline:** backend `46f3a88` (Render). **Escopo:** diagnóstico, pesquisa e desenho. Nenhum código, limiar, ranking, infraestrutura ou Skip foi alterado; nada foi publicado nem commitado. As consultas a dados reais foram **só leituras** e estão registradas na seção 5.

---

## 1. Diagnóstico do pipeline lunar atual (verificado no código)

| Item | Situação | Onde |
|---|---|---|
| Produtos NASA/PDS usados | **LOLA RDR** (disparos do altímetro, via ODE GDS `lolardr`); **M³ L2 reflectance** (PDS Imaging, via ODE); camadas **Trek WMTS** (só imagem); **descoberta** de produtos LOLA e Diviner no PDS (só lista, não mede) | `providers/ode.py` (`GDS_QUERY`), `providers/m3.py`, `providers/trek.py`, `pipelines/lunar.py` (`pds_step(ctx, ["lola","diviner"])`) |
| Mineralogia M³ | IBD1000/IBD2000 e índices de banda; mineralogia indisponível com Sol ≥ 85° da vertical; observação suspeita se IBD1000 < −0,1; até 3 observações tentadas | `pipelines/lunar.py`, `science/spectral.py` |
| Topografia LOLA | Altitude (média, mediana, p05–p95), **relevo**, **declividade regional e aspecto**, **declividade local** (com distância de base declarada), **rugosidade RMS**, cobertura | `science/topography.py`, `pipelines/common.topography_step` |
| O que continua disponível nos polos | **Topografia: sim** (verificado: 57 mil a 123 mil disparos por região). **Mineralogia: não** (Sol rasante ou abaixo do horizonte; 0 pixels válidos). Camadas Trek polares: sim (só imagem). | seção 5 |
| Efeito da falta de luz | O M³ mede luz solar refletida: sem sol não há medição. Isso é correto e já tratado ("indisponível", sem invenção). | regra de 14/11 |
| Como o ranking escolhe análogos | **Só por família mineral** detectada (`analog_sites.match`). Sem família, o resultado é "indisponível" e 0 sítios. É o caso de **todos** os polos testados. | `science/analog_sites.py` |
| Dados que já existem mas não entram na comparação | **Toda a topografia** (declividade, rugosidade, relevo) dos dois corpos. A Terra também tem topografia (Copernicus GLO-30, declividade via Earth Engine). | `pipelines/earth.py` (linhas 59–74) |
| Estruturas reaproveitáveis | Leitor por trechos HTTP (`envi.RemoteCube`); projeção estereográfica polar (`crism.PolarStereographic`, para Marte); `SourceRecord`/`data_sources`; `SectionStatus`/`Reason`; o padrão de seções independentes (`guarded`) | `providers/envi.py`, `providers/crism.py`, `schemas/analysis.py` |

**Conclusão:** nos polos, a plataforma **mede** a topografia, mas **não a usa** para análogos. Não existe nenhuma dimensão de iluminação, temperatura ou gelo.

---

## 2. Matriz de fontes e produtos científicos

| Dimensão | Produto oficial | Tipo | Resolução | Cobertura do polo sul | Acesso | Propriedade realmente medida | Verificado aqui |
|---|---|---|---|---|---|---|---|
| A. Topografia | **LOLA RDR** (disparos) | **Observação direta** | disparos de ~5 m, espaçamento ao longo da órbita ~10–60 m | Excelente: o polo é onde as órbitas convergem | ODE GDS (já integrado) | Distância laser → altitude | ✅ 57 mil–123 mil disparos/região |
| A. Topografia | LOLA polar DEMs (LDEM 85S, 60 m e mais finos) | Derivado (interpolação de observações) | 60 m (e até 5 m em locais de interesse) | 85–90°S | PDS/PGDA (IMG/GeoTIFF) | Altitude interpolada | não lido |
| B. Térmica | **Diviner PRP** (`LRO-L-DLRE-5-PRP-V2.0`, DOI 10.17189/wj0s-w188): temperatura média e máxima anual, profundidade de estabilidade do gelo | **Derivado por modelo térmico ajustado às observações** (Paige et al. 2010) | malha de ~2,88 milhões de triângulos até 80° | 80–90°S | PDS Geosciences (tabela ASCII grande) | Radiância infravermelha → temperatura (o produto é o ajuste de modelo) | só documentação; arquivo **não** lido |
| B. Térmica | Diviner RDR (pontos) | Observação | pegada de ~200–300 m | sim | ODE (consulta assíncrona por e-mail) | Radiância/temperatura de brilho | inviável como API síncrona |
| C. Iluminação | **PGDA AVGVISIB / LPSR** (Mazarico et al. 2011, Icarus 211, 1066; doi:10.1016/j.icarus.2010.10.030) | **Modelo** de iluminação calculado sobre o DEM do LOLA (ciclo de nutação de 18,6 anos, passo de 1 h) | 60 m (85–90°S), 120 m, 240 m | 65–90°S | PDS IMG (int16) em imbrium.mit.edu; COG na PGDA; **aceita leitura por trechos (HTTP 206)** | Fração do tempo com o disco solar visível; sombra permanente sim/não; também visibilidade da Terra | ✅ leitura real (seção 5) |
| C. Iluminação | LROC WAC (mapas de iluminação polares, Speyerer et al. 2013) | Observação (imagens) | ~100 m | sim | LROC RDR | Iluminação observada em várias geometrias | não lido |
| D. Gelo | **M³** (Li et al. 2018, PNAS): gelo exposto na superfície | **Detecção direta** (três bandas de absorção juntas), esparsa | 280 m | só pixels em sombra com sinal | artigo + dados derivados | Absorções de H₂O | não lido |
| D. Gelo | LAMP (UV) e albedo LOLA | Indício consistente, **não diagnóstico** (Li 2018) | km | sim | PDS | Razão de UV; refletância em 1064 nm | não lido |
| D. Gelo | Lunar Prospector NS / LEND | **Hidrogênio** (forma não determinada) | ~dezenas de km | sim | PDS | Fluxo de nêutrons epitermais | não lido |
| D. Gelo | LCROSS (Cabeus) | **Detecção direta no subsolo**, num ponto | — | Cabeus | literatura | Água/OH na pluma de impacto | — |
| D. Gelo | Diviner PRP: profundidade de estabilidade | **Possibilidade** (modelo térmico) | malha | 80–90°S | PDS | Temperatura → estabilidade | — |

---

## 3. Comparação das quatro dimensões

| | A. Topografia/geomorfologia | B. Térmica | C. Iluminação | D. Água/gelo |
|---|---|---|---|---|
| Propriedade física | Altitude, declividade, rugosidade, relevo | Temperatura de superfície | Fração de tempo com sol; sombra permanente | Presença ou estabilidade de H₂O/H |
| Observação ou modelo | **Observação** (LOLA RDR) | Modelo ajustado às observações (PRP) | **Modelo** sobre DEM observado | Detecção esparsa, indícios e modelo, conforme o produto |
| Comparável com a Terra? | **Sim, quantitativamente**, se a declividade for medida na **mesma distância de base** (LOLA: base configurável; Terra: GLO-30, 30 m) | **Não, quantitativamente.** As sombras permanentes ficam em ~25–110 K; a Terra não chega perto (o mínimo natural fica na casa de 180 K). A analogia é só operacional: frio extremo para equipamentos. | **Só qualitativa/operacional.** Inclinação do eixo de ~1,5° (Lua) contra 23,4° (Terra), sem atmosfera. A Terra polar tem sol baixo e sombras longas, mas não sombra **permanente** | **Por processo:** aprisionamento a frio, permafrost, gelo de subsolo. Não há equivalência de condição |
| Integração ao backend | **Pronta no lado lunar** (já medido); no lado terrestre, o GLO-30 já existe; falta harmonizar a escala e comparar | Difícil: o PRP é uma tabela em malha de triângulos e exige pré-processamento para grade, com proveniência | **Simples:** IMG int16 polar, leitura por trechos, mesmo padrão do CRISM | Média: usar sombra permanente e temperatura como **condição**; a detecção (Li 2018) exige localizar os dados derivados |
| Principais incertezas | Escala e distância de base; LOLA esparso entre órbitas fora do polo | Modelo; resolução da malha; não é observação direta | Modelo; resolução de 60 m; terreno abaixo da resolução | Detecções esparsas; indícios ambíguos; "estável" não quer dizer "presente" |

---

## 4. Candidatos terrestres (com o estado de verificação)

> Ambiente frio **não** é, por si só, um análogo lunar. Cada candidato é qualificado pela **finalidade**.

| Candidato | Localização | Tipo de analogia | Propriedade lunar comparável | Evidência publicada (verificada nesta fase) | Diferenças fundamentais |
|---|---|---|---|---|---|
| **Cratera de impacto Haughton**, ilha Devon (Canadá) | Ártico canadense; coordenada **a verificar** em fonte primária (Earth Impact Database) | **Geomorfológica** (cratera de ~20 km, semelhante a Shackleton, de ~21 km) + **operacional** (testes de rovers K10 da NASA Ames para levantamento de postos avançados lunares, 2007) + ambiente polar | Cratera de impacto polar; mobilidade em terreno craterado; operações em sol baixo | NASA Ames 2007 (testes K10 em Haughton para postos lunares); Haughton Crater Lunar Analog Study (CMU, ~2009–2010, hipótese de gelo no subsolo); Haughton-Mars Project | Atmosfera; erosão glacial e fluvial; temperaturas muito mais altas; gravidade; ausência de sombra permanente |
| **Vales Secos de McMurdo**, Antártida | ~77–78°S (a verificar) | **Ambiental/processo** (deserto frio, permafrost, gelo no subsolo) + **operacional** (NASA testou um hábitat inflável por um ano em McMurdo) | Ciclo de gelo, sublimação, operações em frio extremo | Fato operacional verificado (NASA Facts, analogs 2008); a literatura de permafrost é sobretudo Marte, e o vínculo lunar **não** foi verificado | Atmosfera, ciclo sazonal de luz, temperaturas muito acima das sombras permanentes |
| **Sítios anortosíticos do catálogo** (Stillwater, Shawmere, Sittampundi) | já no catálogo, com coordenadas e DOIs | **Geológica** (crosta feldspática das terras altas) | Composição esperada das terras altas polares | DOIs no catálogo (fontes de simulantes NU-LHT, OB-1, LSS-ISAC-1) | Hoje **não** podem ser ligados ao polo **por medição**: falta mineralogia. Só como contexto de mapa geológico (seção 8) |
| Cavernas de gelo / lava tubes com gelo perene | a pesquisar | **Processo** (aprisionamento a frio de voláteis) | Aprisionamento de gelo em sombra permanente | **Não verificado** nesta fase | Escala, temperatura, origem do gelo |

Os dois primeiros têm vínculo lunar **publicado** (Haughton) ou **operacional** (McMurdo). Nenhum deve ser apresentado como "validado" para o polo sul lunar: são candidatos **por finalidade**, com diferenças explícitas.

---

## 5. Cobertura em regiões lunares reais (consultas só de leitura, 2026-11-14)

Regiões, com coordenadas do Gazetteer da IAU via USGS: **Mons Malapert** (−85,98°, −1,67°), da lista de 9 regiões Artemis III (NASA, out./2024); **Haworth** (86,8°S, 4°W), também da lista; **Shackleton**, interior (89,63°S, 132,32°E; fonte secundária, que espelha a IAU).

| Região | Topografia LOLA (pipeline real, local) | Mineralogia M³ | Iluminação média (PGDA, 60 m, janela 5×5) | Sombra permanente (PGDA) | Tempo |
|---|---|---|---|---|---|
| Mons Malapert | ✅ 90.530 disparos; mediana 4.751 m; relevo 487 m; declividade local mediana 12,7° (p95 19,3°); rugosidade 140 m | ❌ incidência 88,5°/88,0°; 3ª observação a 11 km | **0,42** (42% do tempo com sol) | não | 64 s |
| Haworth | ✅ 57.668 disparos; mediana −624 m; relevo 1.190 m; regional 16,0°; local 16,6° | ❌ 0 pixels válidos em 3 observações | **0,027** | não, no ponto central (o fundo tem sombras permanentes) | 29 s |
| Shackleton (interior) | ✅ 123.260 disparos; mediana −2.693 m; local 8,3° (p95 20,7°) | ❌ 0 pixels válidos / incidência 91,9° | **0,000** | **sim** | 33 s |

**Validação da leitura de iluminação:** testei as duas orientações possíveis da grade estereográfica. Só uma é coerente com os fatos conhecidos: interior de Shackleton em sombra permanente, Malapert iluminado. A outra daria 38% de sol dentro de Shackleton.

**Diviner PRP:** o arquivo não foi baixado nem lido (tabela grande em malha de triângulos), então a cobertura real **não foi medida**.

---

## 6. Proposta metodológica

1. **Análogos por finalidade**, nunca um "melhor análogo absoluto". Cada finalidade fica numa seção própria:
   * **Geomorfologia e mobilidade:** declividade, rugosidade e relevo.
   * **Iluminação e operações:** fração de sol, sombra permanente, visibilidade da Terra.
   * **Ambiente térmico:** valores lunares e a declaração de que não há equivalente terrestre.
   * **Voláteis e gelo:** nível de evidência.
   * **Composição:** mineralogia, quando houver.
2. **Sem pontuação única.** Mineralogia e ambiente **não** se somam: medem coisas diferentes e não há base física para pesá-las juntas.
3. **Comparação só de propriedades mensuráveis na mesma definição.** Exemplo: declividade com a **mesma distância de base** e o mesmo método nos dois corpos. Cada métrica traz o valor lunar, o valor terrestre, a diferença e a incerteza. Faixa de tolerância **declarada e testada**, sem peso arbitrário.
4. **Observação, modelo e inferência separados:**
   * `observed` (LOLA RDR);
   * `model_derived` (iluminação PGDA, Diviner PRP);
   * `inferred` (estabilidade do gelo);
   * `detected` (por exemplo, M³ de Li 2018, quando a fonte for integrada).
5. **Ausência não é evidência.** "Sem dado" e "não detectado" nunca contam a favor de um análogo. Seção sem dado → `unavailable`; dados conflitantes → `inconclusive`.
6. **Proveniência completa** em `data_sources`: produto, DOI, versão (ex.: `AVGVISIB_85S_060M_201608`), resolução e janela lida.
7. **Ligação com a missão** por sítio: o que dá para testar ali (mobilidade em declive, navegação com sombras longas, operações em frio, prospecção de gelo) e o que **não** dá (vácuo, gravidade, radiação, temperatura das sombras permanentes).
8. **O ranking de Marte não é tocado.** As dimensões novas valem só para a Lua polar (|lat| ≥ 75°, por exemplo), em seção separada.

## 7. Limitações científicas
* Iluminação e temperatura polares são **modelos** derivados de dados (DEM do LOLA; ajuste do Diviner), não observações diretas pixel a pixel.
* Não há análogo terrestre **térmico** para sombras permanentes: o máximo honesto é uma analogia operacional de frio extremo.
* A iluminação terrestre polar não reproduz a sombra **permanente** nem a ausência de atmosfera.
* A comparação de declividade depende da escala: LOLA RDR é irregular entre órbitas; GLO-30 é uma grade de 30 m.
* Gelo: detecções esparsas (Li 2018); LAMP e albedo não são diagnósticos; nêutrons medem hidrogênio sem dizer a forma; "estável" não quer dizer "presente".
* Coordenadas: as regiões Artemis III foram divulgadas como áreas (~15×15 km na lista de 2022); o ponto central da IAU representa um acidente geográfico, não a área de pouso.
* Os candidatos terrestres desta fase **não estão validados**: alguns vínculos lunares foram verificados (Haughton, operacional em McMurdo) e outros estão marcados como "a verificar".

## 8. Plano de implementação em pequenas etapas (proposta; aguarda autorização)

| Etapa | Tarefas (máx. 3) | Arquivos | Schema | Testes | Aceitação |
|---|---|---|---|---|---|
| **1. Iluminação polar (recomendada primeiro)** | (1) leitor do PGDA AVGVISIB/LPSR (+ visibilidade da Terra) com leitura por trechos e projeção polar esférica; (2) nova seção `environment.illumination` para a Lua com \|lat\| ≥ 65°; (3) proveniência e motivos de indisponível | `providers/lola_illumination.py` (novo), `pipelines/lunar.py` (passo novo protegido), `schemas/analysis.py`, `services/datasets.py`, allow-list de hosts (`imbrium.mit.edu` / `pgda.gsfc.nasa.gov`) | **Opcional:** `environment` com `sunlit_fraction` (mediana, p05, p95), `psr_fraction`, `earth_visibility`, `product`, `resolution_m`, `kind: "model_derived"` | **Positivos:** Shackleton interior → sombra permanente ≈ 1, sol ≈ 0; Malapert → sol ≈ 0,42. **Negativos:** latitude −40° → `not_applicable`; servidor fora → `failed` sem número; pixel fora da grade → `unavailable` | Valores reproduzem a seção 5; sem regressão em Marte e na Lua não polar; o Skip ignora o campo novo |
| 2. Geomorfologia comparável | (1) calcular a declividade terrestre na **mesma base** da lunar; (2) medir uma vez, com dados reais, os candidatos terrestres (Haughton + catálogo) e guardar com proveniência; (3) seção `geomorphology_analogs` (por métrica: valor lunar, terrestre, diferença) | `pipelines/earth.py`/`providers/earth_engine.py` (parâmetro de base), `science/` (novo módulo), dados com proveniência | Seção opcional nova | Positivo: Haughton × uma cratera polar com estatística conhecida; negativo: planície × massif → "não comparável" | Diferenças por métrica com incerteza; nenhum "melhor" absoluto |
| 3. Voláteis (níveis de evidência) | (1) condição de aprisionamento a frio pela sombra permanente (etapa 1); (2) avaliar o pré-processamento do Diviner PRP em grade (temperatura máxima anual) com proveniência; (3) localizar os dados derivados de Li 2018 antes de qualquer "detected" | `science/` (novo), `data/` (só se derivado de produto oficial, com DOI) | `volatiles: {level: detected/inferred/possible/no_data, sources}` | Positivo: Shackleton → "possible" (sombra permanente); negativo: Malapert iluminado → nunca "detected" | Nenhum "detected" sem fonte de detecção direta |

**Risco de regressão:** baixo nas etapas 1 e 3 (seções novas e opcionais, protegidas; Marte intacto); médio na etapa 2 (mexe no pipeline da Terra; precisa de reteste da bateria). **Esforço estimado:** etapa 1 ≈ 1 dia; etapa 2 ≈ 1–2 dias; etapa 3 ≈ 1–2 dias, mais pesquisa.

## 9. Recomendação: primeira melhoria

**Etapa 1: iluminação e sombra permanente (PGDA, Mazarico et al. 2011).**
* **Ganho científico:** iluminação e proximidade de sombra permanente são os critérios centrais na escolha das regiões de base no polo sul. Hoje a plataforma não diz **nada** sobre isso, e o polo devolve 0 análogos.
* **Menor risco:** o produto é oficial e versionado, o acesso foi **verificado** (HTTP 206), o formato é trivial (int16) e a orientação foi validada com fatos conhecidos. Reaproveita o padrão de leitura por trechos e de projeção polar já existente, e não toca Marte nem a mineralogia.
* **Honestidade:** o valor sai como `model_derived` (não "observado"), com DOI, e **não** gera análogo por si só. A ligação com análogos terrestres (operacional: sol baixo e sombras longas, como na Haughton polar) vem como **finalidade** declarada, com diferenças explícitas.

---

### Fontes
* NASA, 9 regiões candidatas Artemis III (out./2024): https://www.upi.com/Science_News/2024/10/28/nasa-artemis-moon-landing-regions/5971730152372/
* Gazetteer (USGS/IAU): Haworth https://planetarynames.wr.usgs.gov/News?page=36 · Mons Malapert https://planetarynames.wr.usgs.gov/Feature/16338 · Shackleton (secundária) https://the-moon.us/wiki/Shackleton
* Iluminação: https://pgda.gsfc.nasa.gov/products/69 (Mazarico et al. 2011, doi:10.1016/j.icarus.2010.10.030)
* Diviner PRP: https://ode.rsl.wustl.edu/moon/pagehelp/Content/Missions_Instruments/LRO/DIVINER/PRP.htm (Paige et al. 2010, doi:10.1126/science.1187726)
* Diviner RDR (consulta pontual): https://ode.rsl.wustl.edu/moon/pagehelp/Content/Web_Interface/Tools_Tab/DIVINER_RDR_Query_Page.htm
* Gelo: Li et al. 2018, PNAS — https://pmc.ncbi.nlm.nih.gov/articles/6130389 · Fisher et al. 2017 (NASA) — https://www.nasa.gov/missions/nasa-orbiter-finds-new-evidence-of-frost-on-moons-surface/ · Lunar Prospector/LCROSS — https://nssdc.gsfc.nasa.gov/planetary/ice/ice_moon.html
* Haughton: https://phys.org/news104156323.html · https://ri.cmu.edu/?p=10550 · NASA Facts (analogs 2008) — https://www.nasa.gov/wp-content/uploads/2016/04/nasa_facts_analogs_2008.pdf
