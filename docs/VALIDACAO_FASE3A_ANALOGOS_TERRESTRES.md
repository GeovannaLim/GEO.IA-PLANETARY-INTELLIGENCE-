# Validação da fase 3A — discriminação geomorfológica e análogos terrestres

Data: 2026-11-14. Base de produção: `ed1ee18` (inalterada). Estado: local, sem commit, push ou deploy.
Fase anterior: [VALIDACAO_GEOMORFOLOGIA_LUA_TERRA.md](VALIDACAO_GEOMORFOLOGIA_LUA_TERRA.md).

Objetivo: melhorar a qualidade da evidência, não o número de recomendações. Todos os números deste documento vêm
de dados reais: LOLA RDR (Lua) e Copernicus GLO-30 (Terra). Dados sintéticos aparecem só nos testes automatizados.

## Resumo

| Pergunta | Resposta curta |
|---|---|
| A. A discriminação melhorou de forma demonstrável? | **Não.** A distribuição completa de declividades não discrimina melhor que o método atual. O método atual (V1) foi mantido sem mudança. |
| B. Quantos análogos documentados ganharam coordenadas verificáveis? | **1 de 5:** Craters of the Moon (Highway Flow e North Crater, amostras com GPS em Tolometti 2021). Já corrigido no JSON geomorfológico (Seção 2.1.1). Os outros 4 seguem com `represents_site=false`. |
| C. Rio Tinto serve como referência de relevo natural? | **Não.** O relevo é misto: o ponto fica na mina de Peña de Hierro. Rio Tinto passa a ser referência de relevo modificado. |
| D. Haughton ou outro candidato corresponde de forma defensável a Haworth? | **Não.** Haughton é rejeitado (declividade mediana de 3° contra 16°). Puʻu Hiwahine (Mauna Kea) tem só uma correspondência exploratória, frágil, para mobilidade. |
| E. Quais candidatos estão prontos para revisão? | Craters of the Moon/Highway Flow (correção de coordenada), Puʻu Hiwahine e Haughton (como referência de baixa declividade). Nenhum está pronto para inclusão automática. |
| F. O que impede publicar recomendações? | Discriminação modesta, taxa de coincidência alta, controle positivo lunar sem área independente, catálogo pequeno e um único análogo documentado com correspondência completa. |

## 1. Tarefa 1 — distribuição completa de declividades contra o método atual

### 1.1 Desenho do estudo

Scripts: `scripts/geomorph_dist_lib.py`, `scripts/geomorph_dist_build.py` e `scripts/geomorph_dist_study.py`.
Saídas: `var/geomorph_dist_study.txt` e `var/geomorph_dist_*.pkl`.

**Mesmos dados e mesma grade.** O estudo reutiliza as janelas de produção: 9 janelas de 1 km, a mesma projeção e a
mesma grade com a mediana por célula. Verifiquei que a reimplementação reproduz `terrain_profile` exatamente no
Haworth real (6/6 métricas iguais até a 4ª casa). Cada janela guarda a distribuição empírica completa de θ. A
unidade de terreno usa a mistura das 9 distribuições, com peso igual por janela.

**Alternativas avaliadas** (interpretáveis, sem pontuação universal):

- **W1:** distância de Wasserstein-1 entre as distribuições de declividade, em graus. É o deslocamento médio de
  declividade necessário para transformar uma distribuição na outra.
- **KS:** distância máxima entre as funções de distribuição acumulada.
- **Critério de correspondência:** usa um nulo por permutação de janelas. As 18 janelas (9 + 9) são reetiquetadas
  ao acaso 999 vezes, com semente fixa. A distância observada não pode passar do percentil 95 desse nulo. Esse
  percentil foi **fixado antes do estudo** e nunca foi ajustado.
- **Combinações com o método atual (V1):**
  - `V1&W1` e `V1&KS`: V1 **e** distribuição. Só podem remover correspondências.
  - `V1/W1`: V1 com o portão de declividade mediana trocado por W1.
- **Referências apenas de declividade:**
  - `GATE`: só a declividade mediana do V1.
  - `W1` e `KS` isolados.

**Controles com dados reais.** Usei as 16 localizações medidas, incluindo as 6 de coordenada grosseira: elas são
terreno real em algum lugar e servem como controle do método, mas não representam o sítio documentado.

| Controle | O que é | Pares |
|---|---|---|
| Positivo **com sobreposição** | mesmo terreno, família deslocada 1–3 km | 192 |
| Positivo **sem sobreposição** | mesmo terreno, família deslocada 4–6 km, em 8 azimutes | 384 |
| Pares distintos | todos os pares das 16 localizações; **não** foram tratados como falsos positivos comprovados | 120 |
| Contrastes a priori | maciço alpino ou ofiolítico (Twin Sisters, Samail, Stillwater) × planície, escudo ou planalto (Shawmere, Sudbury, Kaʻū, Craters of the Moon, El Tatio) | 15 |

- A sobreposição termina em 4 km porque cada família cobre um raio de 2 km.
- Os rótulos de contraste vêm das descrições geológicas do catálogo. Ressalva: o autor já conhecia as métricas
  V0/V1 desses sítios.

> **Correção da fase 2.** O relatório anterior chamou o deslocamento de 3 km de "sem sobreposição". Isso estava
> errado: com raio de família de 2 km, as janelas externas ainda se sobrepõem até 4 km de deslocamento. A taxa
> realmente independente é a de 4–6 km.

**Vazamento.** Nenhum limiar foi calibrado: z ≤ 2 e o percentil 95 são fixos. A escolha do método foi feita numa
metade dos terrenos e avaliada na outra metade.
- Partição: semente 2026, 8 + 8 terrenos.
- Critério fixado antes: maximizar (positivo sem sobreposição − pares distintos), com zero contrastes aceitos.
- Repeti nas duas direções.
- A Lua não foi usada em nenhuma escolha.

### 1.2 Resultados (L = 60 m)

Para os métodos por finalidade, cada par tem 3 decisões (rover, traverse, rugged). Para os métodos só de
declividade, há 1 decisão por par.

| Método | Positivo com sobreposição | Positivo **sem** sobreposição | Pares distintos | Contrastes a priori | Separação (sem sobreposição − distintos) |
|---|---|---|---|---|---|
| **V1 (produção)** | 350/576 (61%) | **477/1152 (41%)** | **83/360 (23%)** | **0/45** | **+18 p.p.** |
| V1&W1 | 228/576 (40%) | 113/1152 (10%) | 25/360 (7%) | 0/45 | +3 p.p. |
| V1&KS | 216/576 (38%) | 112/1152 (10%) | 12/360 (3%) | 0/45 | +6 p.p. |
| V1/W1 | 228/576 (40%) | 113/1152 (10%) | 25/360 (7%) | 0/45 | +3 p.p. |
| GATE (só a mediana) | 161/192 (84%) | 265/384 (69%) | 56/120 (47%) | 0/15 | +22 p.p. |
| W1 isolado | 107/192 (56%) | 72/384 (19%) | 24/120 (20%) | **2/15** | −1 p.p. |
| KS isolado | 98/192 (51%) | 56/384 (15%) | 13/120 (11%) | **2/15** | +4 p.p. |

**Ordenação sem limiar.** Mede a fração de combinações em que o par do mesmo terreno sem sobreposição tem
distância menor que um par distinto:

| Escala | W1 | Diferença de declividade mediana |
|---|---|---|
| 60 m | 0,666 | 0,649 |
| 120 m | 0,658 | 0,660 |
| 240 m | 0,664 | 0,660 |

A distribuição completa praticamente não acrescenta informação discriminante além da declividade mediana nessas
escalas.

**Autocorrespondência por distância de deslocamento (V1, L60):**

| Deslocamento | V1 | V1&W1 |
|---|---|---|
| 1 km | 72% | 69% |
| 2 km | 62% | 34% |
| 3 km | 48% | 19% |
| 4 km | 45% | 10% |
| 5 km | 41% | 8% |
| 6 km | 38% | 10% |

**Partição em metades:** V1 foi escolhido nas duas direções.

| Avaliação na metade | V1 | V1&KS | V1&W1 |
|---|---|---|---|
| B | +30 p.p. | +9 p.p. | −1 p.p. |
| A | +13 p.p. | +3 p.p. | −1 p.p. |

**Estabilidade entre escalas** (mesma decisão em 60 m e na outra escala):

| Comparação | V1 | V1&W1 |
|---|---|---|
| 60 m × 120 m | 91% | 93% |
| 60 m × 240 m | 82% | 84% |

V1&W1 só parece um pouco mais estável porque quase sempre decide "não". Em 240 m, o V1 aceita 2/45 contrastes; em
60 m e 120 m, aceita 0. Esse é mais um motivo para continuar preferindo a escala mais fina válida, como a produção
já faz.

### 1.3 Interpretação

- **O nulo por permutação herda o mesmo problema do z.** As janelas de uma família se sobrepõem muito: são
  janelas de 1 km a 1 km de distância. Por isso a variabilidade dentro da família é pequena e o teste rejeita
  quase todo terreno vizinho sem sobreposição, mesmo sendo o mesmo terreno: a autocorrespondência cai para cerca
  de 10%, o mesmo nível dos pares distintos.
- **Uma família heterogênea alarga o nulo e passa a aceitar contrastes.** O W1 isolado aceita Samail ×
  El Tatio e Samail × Craters of the Moon.
- **Decisão:** nenhuma alternativa melhora os controles independentes. **O algoritmo de produção não foi
  alterado.** O W1 fica apenas como diagnóstico descritivo nos scripts de validação. Nunca foi convertido em
  porcentagem.
- **Uso coerente com a fase 2.** Aplicado à Lua, `V1&W1` elimina exatamente as correspondências que a fase 2 já
  classificava como fracas: El Tatio e Cuprite com Shackleton e Malapert. Mantém Rio Tinto (traverse/rugged) e
  Merriam (rover) com Shackleton. Isso confirma a leitura qualitativa anterior, mas não justifica trocar o método.

## 2. Tarefa 2 — auditoria de coordenadas dos sítios existentes

### 2.1 Sítios com coordenada grosseira

Fontes: pesquisa documental em 2026-11-14. Só foram aceitas coordenadas citadas literalmente de fontes abertas e
lidas; nada foi digitalizado de figuras.

| Sítio | Unidade estudada de fato | Melhor coordenada encontrada (literal) | Fonte | Precisão justificável | Terreno e alteração humana | Vegetação ou construções | Elegível |
|---|---|---|---|---|---|---|---|
| Kaʻū Desert | derrame pāhoehoe de dez/1974 e área AVIRIS de 6×6 km | "centered at 19°30′N and 155°22′23″W" | Seelos et al. 2010, JGR 115, E00D15 | **nenhuma**: a coordenada contradiz o próprio texto ("5 km a SW da caldeira"; 19°30′N fica ao norte) | basaltos jovens; trilhas | quase sem vegetação; colapso da caldeira em 2018 é posterior ao DSM | **Não** (`represents_site=false`) |
| Dresser | localidades DFc1 de geiserito numa área de 7 km centrada na mina de barita | nenhuma publicada (o GPS foi coletado, mas não divulgado) | Djokic et al. 2017, Nat. Commun. 8:15263 | ±3,5 km no melhor caso | cristas de chert; cavas de barita | spinifex | **Não** |
| Craters of the Moon | seis derrames (Highway, North Crater, Big Craters, Blue Dragon, Devils Orchard, Serrate) | ex.: HF16001 "43°27'48.01" N, 113°34'16.90 "W"; COTM16010 "43°28'0.91" N, 113°32'54.46 "W" | Tolometti 2021, tese (Western Univ., grupo Neish/FINESSE), Tabela 2.2 | métrica (GPS); datum não declarado | lavas holocênicas; rodovia US-20/26/93 e estrada do parque | artemísia esparsa; poucas construções | **Sim, por derrame** (Seção 4) |
| Timanfaya | trincheiras em tefra de 1730–36; áreas do curso PANGAEA | nenhuma | Muller & Longpré 2024; ESA; Zenodo 3603760 | — | campo de lava; estrada LZ-67 | quase sem vegetação | **Não** |
| Stillwater | matéria-prima do NU-LHT "hand picked from the mine's waste dump" | nenhuma | Stoeser et al. NASA/TM-2010-216438; Rickman et al. NASA/TM-2011-216454 | — | mina subterrânea, pilhas de rejeito, usina | floresta de coníferas | **Não**: mesmo com coordenada, seria um sítio de mina, não uma unidade geomórfica |
| Sittampundi | anortosito coletado (>100 kg), pedreira não identificada | nenhuma para o local de coleta | EPSC2021-535 | ±15 km | pedreiras, vilas, agricultura | lavouras e árvores | **Não** |

**Resultado: 1 dos 5 análogos lunares documentados** (Craters of the Moon) passa a ter coordenadas verificáveis da
unidade estudada.

### 2.1.1 Correção aplicada: Craters of the Moon (aprovada pela usuária em 2026-11-14)

**O que mudou**
- **Só no JSON geomorfológico** (`app/data/earth_site_geomorphology.json`), a entrada `craters_of_the_moon` passou
  a medir a unidade documentada: Highway Flow, amostra HF16001.
  - Coordenada: 43.463336, −113.571361, precisão de 0,1 km.
  - O texto literal e a fonte ficam em `measured_unit`.
  - O ponto antigo do catálogo fica em `catalog_reference_point`.
- O catálogo mineral (`terrestrial_analog_sites.json`) **não mudou**. Por isso `terrestrial_analogs` fica idêntico.
- A correção é reproduzível: o script `scripts/build_earth_geomorphology.py` ganhou `UNIT_OVERRIDES` e a opção
  `--only`.
  - A opção `--only` reconstrói só os sítios pedidos. Os outros 15 ficaram byte a byte iguais.
  - A marcação de Rio Tinto (`relief_modification`) é preservada em qualquer reconstrução.
- A resposta da API mostra `measured_unit` quando o sítio aparece numa comparação.

**Resultado**
- Perfil real L60: mediana 5,18±1,30°, p90 17,8±2,5°, rugosidade 2,79±0,25 m, σ 29 m, A 97 m, 9/9 janelas.
- `represents_site` passa a `true`, então o sítio fica elegível.
- Elegíveis agora são 11; os comparáveis como relevo natural são 10, porque Rio Tinto ficou como relevo modificado.

**Impacto**, medido com os perfis LOLA reais (`scripts/geomorph_db_impact.py`, saída em `var/cotm_impact.txt`)
- O espalhamento de referência diminui até cerca de 5%: a mediana de θ vai de 8,58 para 8,18°.
- **Nenhuma correspondência existente foi perdida ou ganha.**
- A única correspondência nova é o próprio Craters of the Moon:
  - **Shackleton:** traverse e rugged. É **fraca**: a mediana é 5,2 contra 12,1°, e o portão só passa pela
    incerteza de Shackleton (±3,5°). Também falha no W1 (3,0° contra q95 2,1°).
  - **Polo sul (L4, −89,5°):** rugged.
  - Malapert e Haworth: só parcial, com o portão de declividade reprovado.
- **Verificação:**
  - 218 testes aprovados.
  - L4 rodado com dados reais: PASS, com `terrestrial_analogs` e famílias idênticos a `ed1ee18`.
  - `environment` tem valores idênticos; só a numeração interna da fonte muda na execução em processo.

### 2.2 Auditoria especial: Rio Tinto

Fontes:
- OpenStreetMap via Overpass, 2026-11-14 (`var/rio_tinto_osm_overpass.json`);
- CORINE Land Cover 2012 e 2018 pelo serviço REST da EEA (`var/rio_tinto_clc2012.json`);
- NASA Astrobiology, "Drilling for weird life" (projeto MARTE);
- es.wikipedia (Mina de Peña del Hierro, Corta Cerro Colorado);
- Atalaya Mining (RNS), para o reinício em 2015.

**Fatos sobre o ponto e a mina**
- O ponto do catálogo (37,72512, −6,55643) fica a 0,05 km do castelete do Pozo Maestro da mina de Peña de Hierro.
- A cava de Peña de Hierro está a 0,12–0,23 km, dentro da janela central:
  - 330 × 190 m e cerca de 85 m de profundidade;
  - lavrada a céu aberto de 1883 a 1960 e fechada em 1972;
  - não mudou durante a época do DSM.
- O antigo leito ferroviário da mina passa a 0,03 km do ponto.
- C. Stoker (MARTE, NASA) descreve o local assim: o cerro de Peña de Hierro "was a mountain, is now a pit".

**Feições mapeadas na área das 9 janelas**

| Fonte | Fração da área | Distribuição |
|---|---|---|
| OSM `landuse=quarry` | 2,0% | — |
| CORINE classe 131 (extração mineral) | 8,6% | janela central 13%, S 17%, SW 18% |

- A cava de Cerro Colorado (230 m de profundidade) e as barragens de rejeito ficam a mais de 2 km. Só tocam a
  borda das janelas SW.
- As frações mapeadas são **limite inferior**: escombreiras históricas, cortes e aterros não estão completamente
  mapeados, e a unidade mínima do CORINE é 25 ha.
- O resto da área é relevo de colinas e barrancos com pinheiro, eucalipto e mato. O DSM inclui a altura do dossel.

**Sensibilidade com dados reais** (`scripts/geomorph_rio_tinto_mask.py`, saída em `var/rio_tinto_mask.txt`)
- Mascarei os pixels dentro dos polígonos OSM e CORINE 131 e recalculei o perfil.
- Os 9/9 perfis continuam válidos.
- A declividade mediana muda de 11,82 para 11,45° em 60 m (e de 8,44 para 8,10° em 120 m). Todas as métricas
  ficam dentro da incerteza.
- As correspondências com Shackleton e Malapert (traverse e rugged) não mudam em 60 m nem em 120 m.
- Ou seja: as feições **mapeadas** não produzem a correspondência. Mas a modificação **não mapeada** não pode ser
  limitada sem um MDE anterior à mineração.

**Decisão**
- Rio Tinto foi classificado como `relief_modification.class = "mixed_natural_and_mining"` em
  `app/data/earth_site_geomorphology.json`, com a evidência e as fontes.
- O código (`app/science/geomorph_analogs.py`) passa a fazer o seguinte:
  - o sítio **nunca** aparece em `matches`, nem como correspondência natural;
  - quando corresponde, aparece em `modified_relief_references`, com a relação
    `calculated_correspondence_with_anthropogenically_modified_relief` e uma nota explicativa (traduzida para pt-BR);
  - os dados são preservados;
  - o espalhamento de referência continua incluindo Rio Tinto, que é terreno real. Por isso o resultado de todos os
    outros sítios fica idêntico, como verifica o teste
    `test_mining_modified_relief_is_never_a_natural_correspondence`.

**Observação:** Sudbury (Creighton) tem "um século de mineração e fundição" registrado no catálogo e merece a mesma
auditoria na fase 3B. Hoje não corresponde a nenhuma região lunar testada.

## 3. Tarefa 3 — novos candidatos terrestres

### 3.1 Método e conjunto experimental

**Seleção dirigida pela lacuna.** A lacuna é Haworth e outros terrenos polares com declividade mediana de 11–16°.
Também comparei com Shackleton e Malapert.

**Regras de coordenada**
- Coordenadas citadas literalmente, com a fonte em `var/phase3a_candidates.json`.
- Nenhuma coordenada foi escolhida por ser íngreme: isso viciaria o resultado a favor da correspondência.

**Comparação**
- Perfis reais Copernicus GLO-30, com o mesmo método e as mesmas escalas usados para a Lua.
- O espalhamento de referência é o de produção (10 sítios elegíveis). **Os candidatos não entram no espalhamento
  nem no catálogo.** Script: `scripts/geomorph_candidates_compare.py`; saída: `var/geomorph_candidates.txt`.

**Classificação por região lunar e finalidade**

| Classe | Critério |
|---|---|
| Correspondência exploratória | todas as métricas da finalidade e o portão de declividade mediana correspondem |
| Parcial | só algumas métricas correspondem |
| Não correspondente | nenhuma métrica corresponde |
| Inconclusiva | perfil insuficiente |

**Autoconsistência:** fração de finalidades em que o próprio terreno deslocado 4–6 km corresponde. Indica se a
unidade é homogênea nessa escala.

### 3.2 Perfis reais (L = 60 m, 9/9 janelas válidas em todos)

| Candidato | Documentação de análogo | Coordenada (fonte) | Precisão | Mediana θ (°) | p90 (°) | IQR (°) | Rugosidade (m) | σ (m) | A (m) | Autoconsist. |
|---|---|---|---|---|---|---|---|---|---|---|
| Haughton, centro | lunar/Marte documentado (HMP; Lee et al. LPSC 2009 #2498) | 75°22′38″N 89°40′48″W (Patterson & Ernst 2020, após Osinski 2005) | ~1 km | 3,19±0,50 | 6,26±1,32 | 2,42±0,67 | 1,04±0,24 | 9,9±2,1 | 31±7 | 33/72 |
| Haughton, base do HMP | base dos traverses do HMP | 75°26′N 89°52′W (marsinstitute.no) | ~2 km | 3,64±0,81 | 7,92±1,78 | 3,13±0,71 | 1,70±0,47 | 10,3±2,5 | 35±8 | 69/72 |
| Puʻu Hiwahine, Mauna Kea | **lunar documentado**: ISRU/PISCES 2010 (CSA/DLR/NASA) | 19°45'39.29"N 155°28'14.56"W (Klingelhöfer et al., NTRS 20140008708) | ~0,5 km | 17,02±1,00 | 24,42±1,30 | 7,74±1,24 | 3,51±0,71 | 41,2±7,4 | 137±24 | **4/72** |
| Haleakalā, cume | **nenhuma** (terreno plausível) | 20°42′35″N 156°15′12″W (Wikipedia, cume) | ~1 km | 15,41±1,37 | 23,10±4,82 | 6,85±2,33 | 2,42±0,61 | 58,4±20,6 | 183±69 | 24/72 |
| Vales Secos ADV83-10 (Asgard, Upper Wright) | **Marte**, não Lua (MSSS) | 77°36'46"S 160°52'13"E (msss.com) | ~0,2 km | 13,22±6,57 | 34,62±7,22 | 16,97±4,47 | 4,55±1,08 | 69,9±29,8 | 196±91 | 9/72 |
| Vales Secos ADV83-5 (Olympus) | Marte (MSSS) | 77°26'26"S 162°04'48"E | ~0,2 km | 9,92±3,73 | 31,66±6,26 | 17,65±5,91 | 2,34±1,02 | 58,3±13,6 | 192±46 | 16/72 |
| Craters of the Moon, Highway Flow | linha FINESSE (lunar) | HF16001 (Tolometti 2021) | ~0,1 km | 5,18±1,30 | 17,78±2,52 | 9,94±3,42 | 2,79±0,25 | 28,7±7,1 | 97±23 | 8/72 |
| Craters of the Moon, North Crater | linha FINESSE (lunar) | COTM16010 (Tolometti 2021) | ~0,1 km | 1,98±1,88 | 8,35±6,34 | 4,39±2,85 | 1,31±0,68 | 12,0±11,6 | 35±40 | 44/72 |

Para comparação, os perfis lunares em L60:
- Haworth: 15,85±1,13 / 20,40±2,01 / 3,68±0,95 / 3,28±0,20 / 13,9±7,8 / 46±28.
- Shackleton: 12,07±3,48.
- Malapert: 10,99±1,83.

### 3.3 Correspondências com Haworth (60 / 120 / 240 m)

| Candidato | Rover | Traverse | Rugged | Leitura |
|---|---|---|---|---|
| Haughton (centro e base) | não / parcial / parcial | parcial, portão FALHA | parcial, portão FALHA | **Rejeitado**: mediana de 3° contra 16° (z 8,8–11). Haughton é análogo de Shackleton só em diâmetro, não em relevo nessa escala. |
| Puʻu Hiwahine | **exploratória** / parcial / **exploratória** | parcial (p90) | não | Mediana 17,0 contra 15,8° (z 0,78), mas W1 1,95° > q95 1,19°. Não é estável em 120 m. Autoconsistência 4/72: unidade local (campo de cones). **Exploratória e frágil.** |
| Haleakalā, cume | exploratória nas 3 escalas | parcial (60, 120) / exploratória (240) | parcial / parcial / exploratória | Sem documentação de análogo. O disco mistura o flanco externo (W) com a borda da depressão (E), além de observatórios no cume. **Não é defensável.** |
| ADV83-10 | exploratória (60, 120) / parcial (240) | parcial | parcial | Gelo e neve; mediana ±6,6° (muito heterogênea); autoconsistência 9/72; análogo de Marte. |
| ADV83-5 | exploratória (3 escalas) | parcial | não | Mediana 9,9 contra 15,8°. Só passa porque a incerteza (±3,7°) é grande. **Fraca.** |
| CotM Highway e North Crater | parcial, portão FALHA | parcial, portão FALHA | parcial, portão FALHA | Não correspondente. |

### 3.4 Outras correspondências exploratórias (Shackleton e Malapert, L60)

- **Shackleton:**
  - Haleakalā: as 3 finalidades;
  - Puʻu Hiwahine: rugged;
  - CotM Highway Flow: traverse e rugged. A mediana é 5,2 contra 12,1°: o portão só passa pela incerteza de
    Shackleton (±3,5°). Fraca.
- **Malapert:**
  - Haleakalā: as 3 finalidades em 60 m e em 240 m;
  - Puʻu Hiwahine: rugged só em 240 m.
- Haughton: nenhuma correspondência em nenhuma escala.

### 3.5 Candidatos sem coordenada documentada (não perfilados)

| Candidato | Situação |
|---|---|
| Etna (ARCHES 2022, ROBEX 2017) | coordenadas do local de teste não encontradas; DSM possivelmente desatualizado pelas erupções de 2021 |
| Teide / Las Cañadas (ESA LUCID 2017) | coordenadas das Minas de San José não encontradas |
| Mistastin | a única coordenada encontrada é o centro, no lago |
| "Apollo Valley", Mauna Kea | localizado só em relação à antena VLBA |

Nenhum deles foi perfilado com um ponto substituto, como cume, centro de parque ou centro de cratera.

## 4. Correspondências encontradas e rejeitadas (consolidado)

A coluna "API (V1)" é o que a seção `geomorphology` devolve agora com os perfis LOLA salvos (L60). A coluna
"Leitura" é a interpretação científica.

| Região lunar | API (V1): `matches` | API: `modified_relief_references` | Leitura | Exploratória (candidato fora do catálogo) | Rejeitada |
|---|---|---|---|---|---|
| Shackleton | rover: El Tatio, Cuprite, Merriam; traverse e rugged: Cuprite e Craters of the Moon (fraca, após a correção 2.1.1) | Rio Tinto (traverse, rugged) | **Merriam (rover)** é a mais sustentada: também passa no W1. El Tatio e Cuprite são fracas: a mediana terrestre é 2–2,5× menor e falham no W1. | Haleakalā (sem documentação); Puʻu Hiwahine (rugged); CotM Highway (fraca) | Haughton |
| Malapert | rover: El Tatio, Merriam, Cuprite; traverse e rugged: Cuprite | Rio Tinto (traverse, rugged) | Merriam: compatível só pelo V1 (falha no W1). El Tatio e Cuprite são fracas. | Haleakalā | Haughton, CotM |
| Haworth | rover: Merriam | — | Merriam (rover) só pelo V1; W1 7,2° contra q95 4,1°. **Traverse e rugged: nenhuma correspondência demonstrável.** | Puʻu Hiwahine (rover, frágil) | Haughton |
| Copernicus, Mare Imbrium | — | — | inconclusivo (cobertura LOLA; não abordado nesta fase) | — | — |

## 5. Validação obrigatória

### 5.1 Resultados

| Verificação | Resultado |
|---|---|
| Suíte automatizada | **218 aprovados, 3 ignorados** (os mesmos testes ao vivo de antes; +1 teste novo de relevo modificado) |
| 21 cenários científicos (servidor local, dados reais) | **20 PASS + M8 INCONCLUSIVE**, igual a `ed1ee18`. Detalhes de L1–L4 e L2 abaixo. |
| `terrestrial_analogs` (ranking mineral, inclusive Marte) | idêntico a `ed1ee18` em 20/20 casos concluídos pelo servidor, e em L2 |
| `environment` (iluminação e sombras) | idêntico em 20/20 e em L2 |
| Famílias minerais detectadas (mineralogia lunar e marciana) | idênticas em 20/20 e em L2 |
| Limitações e altimetria | limitações idênticas em 20/20; altitude idêntica (5 casos diferem só na 13ª casa decimal, pela ordem da soma em ponto flutuante) |
| Marte sem seção `geomorphology` | confirmado (M1–M9) |
| `geomorphology` contra a fase 2 | idêntica em 19 casos. A única diferença esperada é em L4: Rio Tinto sai de `matches` (rugged) e vai para `modified_relief_references`. Os outros sítios ficam idênticos. |
| Controle de sombra M3 (L4, polo sul) | PASS |
| Testes adversariais do ranking | A1, A2, A3 e A5 OK. A4: 13 achados, os mesmos 14 da fase 2 menos o caso L2 (ausente desta execução). Em L1, o valor mudou porque outro produto M3 foi usado (abaixo). |
| Candidatos experimentais na API | **nenhum**: 0 ocorrências em `app/` e nas saídas dos cenários |
| JSON da Terra | 16/16 sítios com URLs reais do Copernicus; a única alteração é `relief_modification` em Rio Tinto |
| Latência da seção | 0,06–0,12 s (Shackleton, Malapert, Haworth), dentro de análises de 20–30 s |
| Compatibilidade com o Skip | o contrato só ganha a chave opcional `modified_relief_references` dentro de `comparisons.*`; respostas antigas continuam válidas (testes de schema) |
| Falhas de provedor | testes de integração aprovados (LOLA 503, mineralogia indisponível, falha da seção) |

### 5.2 Incidente durante a execução: PDS/M3 lento

- **O que aconteceu:**
  - Na primeira execução, os 4 cenários lunares (L1–L4) passaram do limite de 240 s do job.
  - Causa: 73 ReadTimeout em `planetarydata.jpl.nasa.gov` (M3) no log do servidor. Marte, que não usa M3, passou
    inteiro.
- **Retentativas:** usei o script `scripts/science_tests_retry.py`, que só repete casos não concluídos e reavalia
  com os mesmos critérios pré-registrados.
  - L3 passou em 150 s e L4 em 84 s.
  - L1 passou em 186 s, na segunda tentativa.
- **Controle para L2:** o mesmo caso rodado com o código de **produção `ed1ee18`**, numa cópia separada (porta
  8011), **também excedeu 240 s** (`var/l2_control_ed1ee18.log`). A causa é externa.
- **L2 sem o limite de 240 s:** rodei o pipeline real em processo (`var/l2_inprocess.log`). Concluiu em 202,6 s com
  o mesmo produto M3 de `ed1ee18`, famílias, `terrestrial_analogs` e `environment` idênticos, e veredito
  pré-registrado **PASS**.
- **Achado de reprodutibilidade (comportamento já existente, não desta fase):**
  - Com o M3 degradado, L1 usou outro produto que também contém o ponto (`M3G20090416T101921` em vez de
    `M3G20090513T191408`). A mediana de IBD1000 mudou (0,97 contra 1,33), mas as famílias, o veredito e os análogos
    não mudaram.
  - Recomendação para outra fase: registrar no relatório por que um produto alternativo foi escolhido.
- **Tempo em produção:** os tempos lunares de hoje (84–203 s) vêm da lentidão do PDS, não do código. No Render, o
  limite de 240 s pode ser atingido enquanto o PDS estiver lento.

## 6. Limitações científicas ainda abertas

1. **Discriminação modesta.**
   - O mesmo terreno sem sobreposição corresponde em 41% dos casos; pares distintos em 23%.
   - A ordenação acerta só em cerca de 0,65 das combinações, com a mediana ou com a distribuição completa.
   - Com 10 sítios elegíveis, aparecem cerca de 2 coincidências por finalidade.
2. **O controle positivo não é puro.** A 4–6 km, o terreno deslocado pode sair da unidade geológica. Assim, 41% é
   uma mistura de sensibilidade com heterogeneidade real. Na Lua, só há controle positivo com sobreposição (raio
   LOLA de 2,5–3 km).
3. **A incerteza é heterogeneidade espacial.** Sítios muito heterogêneos passam no z por incerteza larga (ADV83-5,
   CotM Highway contra Shackleton). O teste de poder discriminante impede só os casos extremos.
4. **DSM.** Copernicus inclui dossel, construções e gelo:
   - Rio Tinto: pinheiro e eucalipto;
   - Haleakalā e Mauna Kea: observatórios e instalações;
   - Vales Secos: neve e gelo.
5. **Catálogo pequeno e enviesado.** Há poucos terrenos de 11–16° naturais, sem mineração e documentados como
   análogos lunares. Merriam continua sendo o único análogo lunar documentado com correspondência completa (rover)
   no catálogo.
6. **Coordenadas.** 4 dos 5 análogos lunares documentados excluídos continuam sem coordenada verificável da
   unidade estudada.
7. **Haleakalā mistura duas unidades** no disco de 2 km. A unidade de 2 km de raio é grande para crateras pequenas
   e pequena para maciços.

## 7. Recomendação sobre o catálogo

| Candidato | Recomendação | Justificativa |
|---|---|---|
| **CotM Highway Flow** (HF16001) | **aplicado** (2.1.1): coordenada corrigida no JSON geomorfológico | Coordenada GPS de fonte acadêmica, sobre um derrame estudado pela linha FINESSE. É uma correção de precisão, não um sítio novo. Corresponde fracamente a Shackleton em traverse e rugged. |
| **Puʻu Hiwahine** (Mauna Kea) | **revisar**; se aprovado, entrar como sítio experimental de terreno íngreme | Análogo lunar documentado (ISRU), coordenada de 0,5 km, terreno pouco vegetado. A correspondência com Haworth é só exploratória e instável entre escalas. Precisa checar o impacto das instalações de Hale Pōhaku no DSM. |
| **Haughton** (centro) | **revisar como referência documentada de baixa declividade** | Útil como controle negativo de terreno polar. Não é análogo geomorfológico de Haworth, Shackleton ou Malapert nessa escala. |
| Haleakalā | **não incluir** | Sem documentação de análogo; ponto de cume que mistura unidades; observatórios. |
| Vales Secos ADV83-10 e ADV83-5 | **não incluir no catálogo lunar** | Análogos de Marte; gelo e neve; heterogeneidade alta. |
| Rio Tinto | **manter só como referência de relevo modificado** (já implementado) | — |

Nenhum candidato foi adicionado ao catálogo de produção.

## 8. Arquivos alterados nesta fase

| Arquivo | Mudança |
|---|---|
| `app/science/geomorph_analogs.py` | `MODIFIED_RELIEF` e `modified_relief_references`; nota condicional; docstring sem "statistically indistinguishable" |
| `app/i18n.py` | tradução pt-BR da nova nota |
| `app/data/earth_site_geomorphology.json` | `relief_modification` em `rio_tinto`; `craters_of_the_moon` remedido no Highway Flow (`measured_unit`, `catalog_reference_point`, `updated_at`) |
| `app/science/geomorph_analogs.py` (2) | expõe `measured_unit` nas correspondências |
| `scripts/build_earth_geomorphology.py` | `UNIT_OVERRIDES`, `--only` e preservação de `relief_modification` |
| `tests/unit/test_geomorphology.py` | +1 teste |
| scripts de validação (não usados em produção) | `geomorph_dist_lib.py`, `geomorph_dist_build.py`, `geomorph_dist_study.py`, `geomorph_rio_tinto_mask.py`, `geomorph_candidates_compare.py`, `scenario_diff.py`, `compare_scenarios.py` |
| evidências em `var/` (não versionado) | `geomorph_dist_*`, `geomorph_candidates.*`, `rio_tinto_*`, `phase3a_candidates.json`, `dem_cache/`, `*_dem.png` |

Nada mudou em mineralogia, ranking marciano, iluminação, `environment`, frontend, infraestrutura ou autenticação.
