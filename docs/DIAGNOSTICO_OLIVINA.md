# Diagnóstico — olivina em Marte: OLINDEX3 × BDI1000IR (2026-11-14)

**Atualização (2026-11-14):** a regra C foi aprovada e implementada como **critério provisório** (`spectral.SPATIAL_COVERAGE_MIN`, cobertura ≥ 75%). A olivina que falha na cobertura aparece como incerta (`uncertain`, `uncertain_evidence`) e não gera análogos. Testes: `tests/unit/test_olivine_coverage.py` (os 59 controles fixos estão em `tests/data/olivine_controls.json`). A extensão analisada pelo CRISM é exposta em `mineralogy.analyzed_extent`. O critério **ainda não foi validado de forma independente**.

Texto original do diagnóstico, de antes da implementação: Dados reais do CRISM (MTRDR), medidos localmente com o código de produção (`abb10cb`). Script: `scripts/olivine_study.py`; dados: `var/olivine_study.json`.

## Conclusão em uma frase
**Os dados não sustentam a regra de coerência entre OLINDEX3 e BDI1000IR**: os dois índices se sobrepõem entre olivina real e poeira. Uma regra diferente, a **coerência espacial** (a maior parte dos pixels da janela acima do mínimo), separou os dois grupos sem nenhum erro nesta amostra. Porém ela se apoia em **um único** falso positivo observado, então é uma proposta, não uma certeza.

## 1. Controles usados (59 janelas, todas com dado CRISM)
| Grupo | n | Origem |
|---|---|---|
| Positivo, literatura | 4 | Jezero (Ehlmann et al. 2008; seleção do Mars 2020); vale de Nili Fossae (EPSC 2018-578; Mangold et al. 2007); **FRT00003E12**, cristas de olivina em Nili Fossae (preprint ESS Open Archive); dunas ricas em olivina, 20,5°N 78,5°E (imagem CRISM de 2006) |
| Positivo, regional | 10 | observações sorteadas dentro da unidade regional de olivina de Nili Fossae (Ody et al. 2013; Mustard et al.), sem verificação ponto a ponto |
| Negativo | 45 | poeira: 29 Tharsis/Amazonis, 8 Elysium, 8 Arabia (as duas últimas **fora de Tharsis**) |

Isidis (FRT00007F47) não existe como MTRDR e ficou de fora. **Copernicus não se aplica:** é Lua (M³), que não tem OLINDEX3, então nenhuma regra estudada aqui o afeta.

## 2. O que os dados mostram
| Medida | Maior valor nos negativos | Menor valor nos positivos | Separa? |
|---|---|---|---|
| OLINDEX3 (mediana) | 0,0521 (Elysium) | 0,0630 (Nili trough) | sim, mas por **0,011** |
| **BDI1000IR** (mediana) | 0,0223 | **0,0166** | **não**: sobrepõem |
| Correlação pixel a pixel OLINDEX3 × BDI1000IR | 0,72 | 0,27 | **não**: poeira também correlaciona |
| % de pixels com OLINDEX3 ≥ 0,05 | **0,66** (Elysium); o 2º maior é 0,29 | **0,89** | **sim, com folga de 0,23** |

**Por que o BDI1000IR não funciona.** A ideia física era que a olivina real teria também uma banda de 1 µm forte (BDI1000IR alto). Na prática, três positivos regionais têm BDI1000IR entre 0,017 e 0,023, a mesma faixa da poeira, e as dunas de olivina documentadas têm 0,0237, só 0,0014 acima do maior valor da poeira. A poeira férrica também deprime a região de 1 µm, e isso mascara a diferença.

## 3. Regras avaliadas (antes/depois)
| Regra (além do OLINDEX3 ≥ 0,05 atual) | Falsos positivos (de 45) | Falsos negativos (de 14) | Literatura perdida (de 4) |
|---|---|---|---|
| **Atual** | **1** (Elysium 0,0521) | 0 | 0 |
| A: BDI1000IR ≥ 0,020 | 0 | 2 | 0 |
| A: BDI1000IR ≥ 0,023 | 0 | 3 | 0 |
| A: BDI1000IR ≥ 0,025 | 0 | 5 | **1** (dunas) |
| B: correlação ≥ 0,3 | 0 | 2 | 1 |
| B: correlação ≥ 0,5 | 0 | 5 | **3** (Jezero, Nili, dunas) |
| **C: ≥ 75–80% dos pixels com OLINDEX3 ≥ 0,05** | **0** | **0** | **0** |

Jezero (99% dos pixels acima do mínimo), Nili Fossae (89%), FRT00003E12 (100%) e as dunas (100%) continuam detectados com a regra C.

## 4. Impacto no ranking dos análogos
* **Elysium:** antes, 1º lugar Samail e Twin Sisters (análogos de olivina, ou seja, conclusão errada). Com a regra C, sobra só o óxido férrico, e os 1ºs passam a ser Kaʻū, Puʻu Nēnē, Dresser e Río Tinto, como evidência **ampla**, coerente com poeira.
* **Positivos:** com a regra C, nenhum muda. Com a regra A (BDI1000IR ≥ 0,023), três positivos regionais **perderiam** a olivina e o 1º lugar trocaria Samail/Twin Sisters por sítios de óxido férrico, o que seria um erro.
* **Lua:** sem impacto.

## 5. Justificativa física da regra C (e seus limites)
* **Por quê.** Uma unidade rica em olivina que ocupa a janela eleva o OLINDEX3 de forma **coerente no espaço**: quase todos os pixels passam do mínimo. Na poeira, a mediana fica em torno do mínimo e uma parte grande dos pixels cai abaixo dele (Elysium: 34%).
* **Relação com o teste atual.** Hoje se exige mediana ≥ mínimo, ou seja, ≥ 50% dos pixels acima. A regra C pede ≥ 75–80%. É o **mesmo critério de valor** aplicado a quase toda a janela, não um limiar novo.
* **Limites:**
  1. **Só um falso positivo observado** (Elysium). A regra C comprovadamente corrige esse caso, mas não há outros casos para medir quanto ela reduz falsos positivos em geral.
  2. **Afloramentos pequenos.** Se a olivina ocupar só parte da janela de ~2 km (um afloramento estreito, como em Juventae), a regra perde a detecção. Não houve positivo desse tipo na amostra, então o risco não foi medido.
  3. Os positivos são todos da região de Nili Fossae/Jezero. Olivina de Argyre, Hellas ou Valles Marineris não foi testada.

## 6. Achado lateral: janela do CRISM
O número de pixels não muda com o raio pedido: a janela é limitada a ~61×61 pixels (≈ 2,2 km de lado). Para a mineralogia de Marte, **o sistema sempre analisa só os ~2 km centrais**, mesmo que o usuário peça 10 ou 25 km. Isso aparece no processamento registrado, mas não fica claro na interface. Não é erro, mas deveria ser explícito.

## 7. Recomendação (aguarda aprovação)
* **Não implementar a regra A nem a B**: os dados não as sustentam.
* **Opção recomendada:** implementar a **regra C com 75%**, ponto médio da folga entre 0,66 e 0,89, com teste de regressão e como **critério provisório**. Na resposta, marcar a olivina que passa no valor mas falha na coerência como "**incerta**", em vez de apagá-la: aparece para o usuário, mas não gera análogos. Validar depois com mais negativos (outras regiões) e com positivos de afloramento pequeno.
* **Alternativa mais conservadora:** não mudar a regra e só marcar como "**incerta**" toda olivina com mediana entre 0,05 e 0,065. Custo: Nili trough (0,063) e um positivo regional ficariam "incertos".
* Em qualquer caso: deixar explícito na resposta da API que a janela do CRISM cobre ~2 km.

## Fontes
* FRT00003E12, olivina em Nili Fossae: https://essopenarchive.org/doi/full/10.22541/essoar.176235473.32635438/v4
* Unidade regional de olivina de Nili Fossae: https://www.sciencedirect.com/science/article/abs/pii/S0019103518306031
* Olivina global no OMEGA (Ody et al. 2013): https://sci.esa.int/web/mars-express/-/51850-ody-a-et-al-2013
* Jezero: https://authors.library.caltech.edu/87552 · Nili trough: https://meetingorganizer.copernicus.org/EPSC2018/EPSC2018-578.pdf
* Dunas de olivina (CRISM, 2006, 20,5°N 78,5°E): a coordenada veio do resumo de uma busca e **não foi conferida na página original** (candidata: https://science.nasa.gov/photojournal/olivine-phyllosilicates-and-ancient-crater-rims/). O ponto fica dentro da unidade regional de olivina; mesmo tratado como positivo regional, as conclusões não mudam (100% dos pixels acima do mínimo).
