# Relatório — testes científicos e adversariais (2026-11-14)

## Em uma frase
Os testes adversariais acharam **sete formas de o sistema chegar a uma conclusão científica errada**. As sete foram corrigidas e cobertas por testes. A bateria final passou em **20 de 21** casos com dados reais; o caso restante (Olympus Mons) não tem dado do CRISM, por isso não dá para julgar. Em **9 lugares cobertos de poeira que não entraram na calibração**, não houve **nenhum** mineral falso.

> Estado: validado localmente com o código novo e dados reais da NASA (commit local). **Ainda não publicado em produção.**

---

## 1. Como foi feito (simples)
1. **Testes de acerto:** lugares onde a ciência já sabe o que existe (pousos de sondas, minerais publicados). O resultado esperado foi escrito **antes** de rodar (`scripts/science_tests.py`).
2. **Testes adversariais:** procurar de propósito situações em que o sistema erraria:
   * lugares **sem** o mineral (poeira de Tharsis, regiões sem gelo) para ver se ele "inventa" detecções;
   * lugares **com** gelo, sem sol, com observações ruins;
   * ataques ao ranking de análogos (`scripts/adversarial_analogs.py`): ordem do arquivo, empates, evidência fraca, mistura Lua/Marte.
3. **Calibração honesta:** quando foi preciso criar um limite numérico, ele foi calculado com um grupo de lugares e **conferido em outro grupo que nunca foi usado para calibrar**.

---

## 2. As sete formas de erro encontradas e o que foi feito

| # | O problema (simples) | Exemplo real | Correção |
|---|---|---|---|
| 1 | **Minerais falsos na poeira.** Com milhares de pixels, o teste estatístico aceitava valores minúsculos (ruído de calibração). | Na poeira do Olympus Mons, o sistema "detectava" olivina, argila de alumínio, sulfato e gelo, e oferecia análogos de sulfato. | Valor mínimo físico por índice, calibrado com 26 observações de poeira; **validado em 9 outras: 0 falsos positivos**. |
| 2 | **Gelo falso perto do equador.** | "Gelo" em Jezero, Nili, Mawrth e Gale. | Mesmo método; calotas polares de verdade continuam com gelo (0,05 a 0,41). |
| 3 | **Minerais "vistos" através do gelo.** As bandas do gelo imitam outros minerais. | Na calota polar, "sulfato" e "olivina". | Com gelo confirmado, esses minerais são mostrados mas **não** geram análogos, e o sistema explica o porquê. |
| 4 | **Medir sem sol.** | Polo sul da Lua: Sol abaixo do horizonte, valores absurdos (IBD1000 = −4,4) marcados como "disponível". | Com incidência solar ≥ 85°, a mineralogia fica "indisponível". |
| 5 | **Observação ruim decidindo o resultado.** | Pico de Copernicus: uma observação do M³ dizia "sem banda", outra dizia "olivina forte". O sistema usava a ruim. | Banda de 1 µm fortemente negativa (fisicamente impossível em rocha) marca a observação como suspeita e o sistema usa a próxima. **Copernicus agora acerta a olivina.** |
| 6 | **Ausência contada como semelhança.** | "Nem a região nem o sítio têm a banda de 2 µm" virava ponto a favor e mudava o 1º lugar em Mawrth. | Só conta a **presença** compartilhada. |
| 7 | **Empates decididos por detalhe sem significado.** | Samail × Río Tinto empatados; quem desempatava era a precisão da coordenada ou a ordem no arquivo. O óxido férrico, presente em 100% de Marte, empatava com argila. | Empates recebem a **mesma posição** e um aviso; o óxido férrico vira evidência "ampla" e não empata com mineral específico. |

**Achado de engenharia que destravou os controles:** as observações do CRISM perto dos polos usam outra projeção de mapa (estereográfica polar), que o sistema não lia. Ou seja, Marte acima de ~65° nunca tinha mineralogia. Foi implementada com as equações elipsoidais que o próprio catálogo do PDS indica, conferida contra os limites do rótulo de 3 produtos (erro de 0,01 a 0,03°). As equações "de reserva" do mesmo catálogo erravam 3 a 5 km, por isso foram descartadas.

---

## 3. Resultados finais (dados reais, código novo)

| # | Lugar | Esperado | Obtido | |
|---|---|---|---|---|
| M1 | Jezero | olivina + argila Fe/Mg | olivina, argila Fe/Mg, óxido férrico | ✅ |
| M2 | Jezero de novo | idêntico | idêntico | ✅ |
| M3 | Jezero +1 km | quase igual | igual | ✅ |
| M4 | Nili Fossae | olivina / argila | olivina, argila Fe/Mg, carbonato | ✅ |
| M5 | Mawrth (0–360°) | argila | argila Fe/Mg | ✅ |
| M6 | Mawrth (−180–180°) | igual a M5 | idêntico | ✅ |
| M7 | Pouso Curiosity | −4.501 m | −4.506 m | ✅ |
| M8 | Olympus Mons | sem minerais hidratados | sem dado CRISM | ⚪ |
| M9 | Marte sem CRISM | não inventar | "indisponível" + contexto global com aviso | ✅ |
| L1 | Pouso Chang'e-3 | −2.630/−2.640 m; basalto | −2.628 m; piroxênio | ✅ |
| L2 | Pico de Copernicus | olivina | **olivina** (antes falhava) | ✅ |
| L3 | Mare Imbrium | piroxênio | piroxênio | ✅ |
| L4 | Polo sul da Lua | não medir no escuro | mineralogia "indisponível", 0 sítios | ✅ |
| D1–D6 | Poeira (6 pontos) | nada além de óxido férrico | só óxido férrico | ✅ |
| I1 | Calota norte (fora da calibração) | gelo; minerais mascarados | gelo; olivina/sulfato mascarados | ✅ |
| I2 | Calota sul (fora da calibração) | gelo; minerais mascarados | gelo de CO₂; olivina/sulfato mascarados | ✅ |
| V1–V9 | Poeira, **validação** (nunca usada na calibração) | nada além de óxido férrico | **9/9 limpos** | ✅ |

**Análogos:** em todos os casos, cada sítio oferecido é verificado, tem referência e tem geologia que explica o mineral detectado. Mesma ordem com o catálogo embaralhado (20 ordens testadas). Nenhum sítio aparece para o corpo errado. Nenhuma evidência "ampla" fica à frente de uma "específica".

---

## 4. Como ficou o ranking (exemplos reais)
* **Jezero:** Samail e Twin Sisters **empatados em 1º** (os dois explicam olivina + argila); depois, os sítios de óxido férrico.
* **Mawrth Vallis:** Samail e Twin Sisters (argila de Fe/Mg) em 1º; antes, sítios que só explicavam o óxido férrico empatavam em 1º.
* **Copernicus:** Craters of the Moon e Merriam (olivina).
* **Poeira de Marte:** Kaʻū e Puʻu Nēnē, sítios de solo basáltico alterado; Puʻu Nēnē é a fonte do simulante de solo marciano JSC Mars-1. É uma correspondência coerente para poeira, marcada como evidência ampla.

---

## 5. O que ainda é limitação (não esconder)
1. **Os mínimos dos índices vêm de controles, não de um valor publicado.** O artigo de referência do CRISM (Viviano-Beck et al. 2014) não pôde ser acessado (site recusou, editora bloqueou), e não há limiares publicados ao nosso alcance. Os valores estão em `app/science/spectral.py` e as medições que os definem em `data/calibration/crism_controls.json` (45 controles).
2. **A folga da olivina é pequena:** poeira chega a 0,043, a olivina documentada fica em 0,063 a 0,071, e o mínimo é 0,05.
3. **A poeira usada é de uma única grande região** (Amazonis/Olympus/oeste de Tharsis). Outras regiões empoeiradas (Arabia, Elysium) não foram testadas.
4. **Sulfato não teve controle positivo** (lugar com sulfato documentado e coordenada verificada); só foi testado que ele não aparece onde não deve.
5. **Apollo 17:** duas observações do M³ foram descartadas como suspeitas e a terceira não sustenta nenhuma família mineral. O sistema diz isso, mas não acerta o basalto do vale.
6. **Projeção polar:** precisão de 1 a 2 km perto do polo.
7. **Lua com várias observações ruins** pode levar mais tempo (o sistema tenta até 3).

---

## 6. O que mudou no código
* `app/science/spectral.py`: mínimos calibrados (`MAGNITUDE_FLOOR`), limite de iluminação (`MAX_USABLE_INCIDENCE_DEG = 85`), filtro de qualidade do M³ (`M3_CONVEX_1UM = −0,1`).
* `app/providers/crism.py`: projeção estereográfica polar (elipsoidal).
* `app/pipelines/lunar.py`, `mars.py`: sem sol → indisponível; observação suspeita ou sem pixels válidos → tenta a próxima.
* `app/science/analog_sites.py`: mascaramento por gelo; só presença compartilhada conta; empates com mesma posição e aviso; óxido férrico como evidência ampla.
* `app/schemas/analysis.py`: campos novos e opcionais `rank` (sítio) e `masked_evidence` (seção). Compatível com o Skip atual.
* Testes: 114 automatizados (eram 100), incluindo os adversariais (`tests/unit/test_adversarial_analogs.py`, `tests/unit/test_science_fixes.py`).

## 7. Fontes
* Jezero: https://authors.library.caltech.edu/87552
* Nili Fossae e Mawrth: https://meetingorganizer.copernicus.org/EPSC2018/EPSC2018-578.pdf
* Curiosity: Vasavada et al. 2014 — https://deepblue.lib.umich.edu/bitstream/2027.42/108017/1/jgre20266.pdf
* Chang'e-3: https://www.lroc.asu.edu/images/751 · https://www.lroc.asu.edu/images/811
* Copernicus, olivina do pico central: Isaacson et al. 2011 — https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2010JE003731
* Projeção polar do CRISM: PDS, `mrocr_4001/catalog/mtr_map.cat` — https://pds-geosciences.wustl.edu/mro/mro-m-crism-5-rdr-mptargeted-v1/mrocr_4001/catalog/mtr_map.cat
* Definições dos índices CRISM: Viviano-Beck et al. 2014, doi:10.1002/2014JE004627
