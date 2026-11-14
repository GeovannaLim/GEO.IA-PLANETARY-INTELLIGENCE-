# Validação — comparação geomorfológica Lua–Terra (2026-11-14)

**Base:** `ed1ee18` (produção) + esta fase, só local. **Nada foi commitado, enviado ao GitHub ou publicado.**
Rollback continua sendo `ed1ee18` (e antes dele `46f3a88`).

## 1. Fontes de dados
| Corpo | Produto | Acesso | Uso |
|---|---|---|---|
| Lua | **LOLA RDR** (disparos individuais do altímetro), via ODE GDS `lolardr` (Washington University / NASA PDS Geosciences Node) | o mesmo pedido de altimetria que o pipeline já fazia; nenhuma chamada nova à NASA | elevação relativa ao redor do ponto |
| Terra | **Copernicus DEM GLO-30** (ESA / programa Copernicus), `Copernicus_DSM_COG_10_*`, 1″ (~30 m), alturas EGM2008 | bucket público do AWS Open Data `copernicus-dem-30m.s3.amazonaws.com`, sem credenciais; leitura por faixas (*range*) só dos blocos internos necessários | perfil de referência de cada sítio do catálogo, calculado **uma vez** e versionado |

* O arquivo de referência `app/data/earth_site_geomorphology.json` foi gerado em **2026-11-14 08:10 UTC** por `scripts/build_earth_geomorphology.py`, com dados reais. Ele registra, por sítio, os blocos (*tiles*), as URLs, o tamanho do pixel e o horário de leitura.
* Em produção, **a Terra não é lida a cada análise**: só o JSON é consultado. Uma falha do Copernicus não afeta uma análise em curso (ver seção 7).
* O decodificador COG (DEFLATE + preditor 3 de ponto flutuante) foi conferido com valores conhecidos: o pico do Mauna Kea dá **4.204 m** e o Mar Morto, **−427 m**.
* O catálogo **não foi ampliado**: os 16 sítios verificados já existentes. Haughton não está no catálogo (seção 10).

## 2. Definição das métricas
Todas calculadas sobre a mesma grade de base horizontal **L** (mediana dos pontos em cada célula), numa projeção azimutal equidistante local. **Elevação absoluta nunca é comparada.**

| Métrica | Unidade | Definição |
|---|---|---|
| `slope_median_deg` | graus | mediana de θ = atan(\|∇z\|), gradiente por diferenças centrais entre células vizinhas (distância 2L) |
| `slope_p90_deg` | graus | percentil 90 de θ (encostas mais íngremes da janela) |
| `slope_iqr_deg` | graus | intervalo interquartil de θ (variedade de inclinações) |
| `roughness_m` | m | RMS de z − média dos 4 vizinhos (afastamento da planaridade local na escala L; não é declividade nem relevo) |
| `relief_sigma_m` | m | RMS das elevações das células em torno do plano de mínimos quadrados da janela |
| `relief_amplitude_m` | m | p95 − p05 das elevações sem a tendência do plano |

Cada valor sai com `{value, uncertainty, unit, n, scale_m, definition}`.

**Validade (suporte amostral, não similaridade):** cobertura ≥ 80% das células da janela e ≥ 30 células de declividade e de rugosidade. Abaixo disso a janela é `insufficient` e não gera número.

**Unidade de terreno:** um terreno é descrito por uma **família de 9 janelas de 1 km** (centro + 8 deslocadas 1 km a cada 45°). Valor = mediana entre as janelas válidas; incerteza = desvio-padrão entre elas (heterogeneidade natural do terreno nessa escala). São exigidas ≥ 5 janelas válidas, e os dados precisam cobrir 2 km ao redor do ponto.

*Por que a família:* no controle "mesmo terreno deslocado 1 km", a janela única com bootstrap interno declarou "diferente" em ~70% dos casos (a incerteza não captava a variação real entre janelas vizinhas). Com a família, o mesmo controle dá **100% de correspondência**.

## 3. Harmonização
* **Mesmo método nos dois corpos:** a mesma função (`terrain_profile`) recebe pontos irregulares do LOLA ou centros de pixel do Copernicus.
* **Mesma escala:** a comparação só usa perfis com o **mesmo L**. Para a Lua, escolhe-se o menor L em {60, 120, 240, 480} m em que a família é válida; a Terra é lida no mesmo L. Escalas nunca são misturadas (teste dedicado).
* **Mesma janela física:** 1 km por janela, 2 km de extensão, nos dois corpos.
* **Precisão das coordenadas:** um sítio cuja coordenada tem precisão pior que 2 km fica `represents_site=false` e **não é comparado** (a família poderia cair fora da unidade documentada). São 6 de 16: Kaʻū (3 km), Dresser (5), Craters of the Moon (5), Timanfaya (3), Stillwater (5), Sittampundi (15).
* **Regra de correspondência por métrica:** z = |Δ| / √(s_Lua² + s_Terra²) ≤ 2 **e** comparação discriminante: a incerteza combinada não pode passar do espalhamento da métrica entre os sítios de referência no mesmo L. Sem isso, um terreno muito heterogêneo "combinaria" com tudo (caso real: Samail, declividade 5,2 ± 9,8°).
* **Por finalidade:** a finalidade só corresponde se **todas** as suas métricas corresponderem **e** a declividade mediana também corresponder (exigência de nível de declividade, introduzida pela auditoria da seção 6). Correspondência parcial é mostrada como parcial, com o resultado da exigência (`slope_level_gate`), sem recomendar o sítio.
* **O que z ≤ 2 é e não é:** um **critério operacional** ("a diferença não passa de duas vezes a variabilidade espacial combinada"), **não** um teste estatístico de equivalência. A incerteza usada é a **heterogeneidade espacial** entre as 9 janelas, não erro de medição. Não ter detectado diferença não prova semelhança; por isso há a verificação de poder discriminante e a exigência de declividade.
* **Sem pontuação universal:** o z máximo só ordena os sítios correspondentes e nunca vira porcentagem.

| Finalidade | Métricas |
|---|---|
| A. Mobilidade de rover | `slope_median_deg`, `slope_p90_deg`, `roughness_m` |
| B. Planejamento de travessia | `slope_p90_deg`, `slope_iqr_deg`, `relief_sigma_m` |
| C. Operações em terreno acidentado | `relief_amplitude_m`, `relief_sigma_m`, `slope_iqr_deg` |

Os limiares (z ≤ 2, cobertura 80%, 30 células, 5 de 9 janelas) são convenções estatísticas declaradas, não calibradas para produzir um resultado. Nenhum limiar mineralógico foi tocado.

## 4. Arquitetura e arquivos
| Arquivo | Mudança |
|---|---|
| `app/providers/copernicus_dem.py` | **novo**: leitor COG GLO-30 (cabeçalho TIFF, DEFLATE + preditor 3, montagem entre blocos de 1°) |
| `app/providers/http.py` | hosts permitidos: `copernicus-dem-30m.s3.amazonaws.com` |
| `app/science/geomorphology.py` | **novo**: métricas, famílias, comparação |
| `app/science/geomorph_analogs.py` | **novo**: monta a seção `geomorphology` a partir da altimetria lunar e do JSON de referência |
| `app/data/earth_site_geomorphology.json` | **novo**, gerado com dados reais (97 KB) |
| `scripts/build_earth_geomorphology.py` | **novo**: gera o JSON |
| `app/schemas/analysis.py` | `GeomorphologySection`; campo opcional `AnalysisResult.geomorphology` |
| `app/pipelines/common.py` | o contexto guarda a altimetria já baixada; `finalize` aceita a seção |
| `app/pipelines/lunar.py` | a seção é calculada depois dos análogos minerais, em thread, com captura de erro |
| `app/i18n.py` | traduções para português |
| Testes | `tests/unit/test_geomorphology.py`, `tests/integration/test_lunar_geomorphology.py` (novos) |
| Validação (fora da produção) | `scripts/geomorph_regions.py` (5 regiões), `scripts/geomorph_controls.py` (perfis deslocados no Copernicus), `scripts/geomorph_audit.py` e `scripts/geomorph_audit_variants.py` (controles e sensibilidade, sem rede) |

**Separação:** a seção `geomorphology` é **nova e aditiva**. Não lê nem escreve `terrestrial_analogs`, não altera o ranking mineral, e uma falha dela vira `status: failed` só nela. Cada sítio correspondente traz `relationship: "calculated_geomorphological_correspondence"` e `documented_lunar_analog` (se o catálogo documenta o sítio como análogo lunar), para não confundir correspondência calculada com análogo documentado. Marte não recebe a seção.

**Frontend Skip:** nada foi mudado. Campo novo e opcional; o Skip atual o ignora.

## 5. Resultados reais (pipeline completo, código final, 2026-11-14)
Execução local, uma região por vez, dados reais e sem cache (`scripts/geomorph_regions.py` → `var/geomorph_regions_final.json`). As 6 métricas abaixo são **mediana ± desvio entre as 9 janelas** (heterogeneidade espacial), em L = 60 m.

| | Shackleton (interior) | Mons Malapert | Haworth | Copernicus (pico) | Mare Imbrium |
|---|---|---|---|---|---|
| Ponto, raio pedido | −89,63; 132,32; 3 km | −85,98; −1,67; 5 km | −86,8; −4,0; 5 km | 9,65; −20,05; 5 km | 32,80; −15,60; 10 km |
| Raio de LOLA efetivo | 3 km | 2,5 km (reduzido pelo limite do GDS) | 2,5 km (idem) | 5 km | 10 km |
| Disparos LOLA | 205.038 | 113.543 | 75.686 | 12.102 | 46.130 |
| Escala efetiva L | 60 m | 60 m | 60 m | nenhuma válida até 480 m | nenhuma válida até 480 m |
| Cobertura mediana | 100% | 100% | 99,8% | 54% (a 480 m) | 62% (a 480 m) |
| Janelas válidas | 9/9 | 9/9 | 9/9 | 0/9 | 0/9 |
| Declividade mediana (°) | 12,07 ± 3,48 | 10,99 ± 1,83 | 15,85 ± 1,13 | — | — |
| Declividade p90 (°) | 17,11 ± 0,85 | 15,41 ± 3,39 | 20,40 ± 2,01 | — | — |
| IQR de declividade (°) | 7,68 ± 1,93 | 5,54 ± 0,75 | 3,68 ± 0,95 | — | — |
| Rugosidade (m) | 2,06 ± 0,20 | 2,44 ± 0,40 | 3,28 ± 0,20 | — | — |
| σ do relevo (m) | 40,5 ± 6,1 | 32,7 ± 11,4 | 13,9 ± 7,8 | — | — |
| Amplitude do relevo (m) | 131 ± 21 | 106 ± 36 | 46 ± 28 | — | — |
| Sítios comparados | 10 elegíveis (6 excluídos por coordenada) | 10 | 10 | 0 | 0 |
| Resultado | correspondência nas 3 finalidades | correspondência nas 3 | só mobilidade | **inconclusivo** | **inconclusivo** |
| Mineralogia | indisponível (100% sombra permanente) | indisponível | indisponível | disponível | disponível: piroxênio; 5 sítios minerais **inalterados** |
| Tempo total / geomorfologia | 26,8 s / 0,15 s | 29,6 s / 0,08 s | 27,6 s / 0,07 s | 20,0 s / 0,05 s | 29,2 s / 0,10 s |

Copernicus com raio 1,5 km (o cenário L2) dá `insufficient_data` com a nota "pedir raio de pelo menos 2 km", e a mineralogia (olivina; Craters of the Moon, Merriam) fica **idêntica** à de `ed1ee18`.

### Correspondências completas, com a evidência (lua/terra e z de cada métrica; "gate" = declividade mediana)
| Região | Finalidade | Sítio | Evidência | Leitura |
|---|---|---|---|---|
| Shackleton | mobilidade | **Merriam (JSC-1)** · análogo lunar documentado | gate 12,1/8,9 (0,45); p90 17,1/27,4 (1,68); rug. 2,06/2,39 (0,72) | compatível; p90 terrestre mais íngreme |
| Shackleton | mobilidade | El Tatio | gate 12,1/5,8 (1,27); p90 17,1/16,3 (0,10); rug. 2,06/1,44 (1,09) | **fraca**: declividade mediana 2× menor, compatível só pela heterogeneidade dos dois |
| Shackleton | mobilidade | Cuprite | gate 12,1/4,8 (1,58); p90 17,1/15,4 (0,42); rug. 2,06/2,58 (0,52) | **fraca**: mediana 2,5× menor |
| Shackleton | travessia + acidentado | **Rio Tinto** | gate 12,1/11,8 (0,06); p90 17,1/20,5 (1,25); IQR 7,68/7,67 (0,01); σ 40,5/32,1 (0,74); A 131/102 (0,72) | **a mais próxima**: valores próximos, não só compatíveis |
| Shackleton | travessia + acidentado | Cuprite | gate (1,58); σ 40,5/22,0 (1,90); A 131/74 (1,74) | **fraca**: relevo terrestre ~metade |
| Malapert | mobilidade | **Merriam (JSC-1)** · documentado | gate 11,0/8,9 (0,33); p90 15,4/27,4 (1,72); rug. 2,44/2,39 (0,08) | compatível; p90 terrestre mais íngreme |
| Malapert | mobilidade | El Tatio | gate 11,0/5,8 (1,31); rug. 2,44/1,44 (1,49) | **fraca** |
| Malapert | mobilidade | Cuprite | gate 11,0/4,8 (1,76); p90 15,4/15,4 (0,01); rug. 2,44/2,58 (0,13) | **fraca** na mediana |
| Malapert | travessia + acidentado | **Rio Tinto** | gate 11,0/11,8 (0,26); p90 15,4/20,5 (1,20); IQR 5,5/7,7 (1,47); σ 32,7/32,1 (0,04); A 106/102 (0,08) | **a mais próxima** |
| Malapert | travessia + acidentado | Cuprite | gate (1,76); σ 32,7/22,0 (0,78); A 106/74 (0,73); IQR 5,5/6,2 (0,26) | moderada; mediana 2,3× menor |
| Haworth | mobilidade | **Merriam (JSC-1)** · documentado | gate 15,9/8,9 (1,14); p90 20,4/27,4 (1,09); rug. 3,28/2,39 (1,92) | no limite (rugosidade z 1,92) |

**Ponto adicional (cenário L4, polo sul −89,5°; 0°, 5 km, 9/9 janelas):** terreno mais suave (declividade 7,1 ± 2,3°, σ 15,8 ± 8,6 m).
* **Mobilidade:** El Tatio e Cuprite.
* **Travessia:** **Shawmere** (análogo lunar documentado): IQR 3,39/3,46 (0,04), σ 15,8/9,8 (0,70), gate 7,1/3,6 (1,49); e Cuprite.
* **Terreno acidentado:** Shawmere, Cuprite, **Lonar** (amplitude 50/96, z 1,60) e **Rio Tinto** (gate 7,1/11,8, z 1,35).

As duas últimas mostram o efeito da heterogeneidade: valores distantes ainda passam no critério.

"Fraca / moderada / a mais próxima" é a **minha leitura dos números**, para esta revisão. Não é uma categoria da API, que só informa os valores, os z e o resultado.

### Sem correspondência demonstrável
* **Haworth, travessia e terreno acidentado:** nenhum sítio. Antes da exigência de declividade, Puʻu Nēnē, Cuprite, Shawmere e Sudbury "correspondiam" com declividade mediana de 1,3–4,8° contra 15,9° na Lua. Agora aparecem como **parciais**.
* **Copernicus e Mare Imbrium:** **inconclusivo, não "sem correspondência"**. A cobertura do LOLA a baixa latitude (54% e 62% das células, mesmo a 480 m) não sustenta um perfil, então nenhum valor é produzido. A mineralogia dessas regiões fica intacta.

### Correspondências parciais
Elas aparecem em `partial_only`, com as métricas que corresponderam e o resultado da exigência de declividade, e **nunca** como recomendação. Exemplos: Lonar em Shackleton e Malapert (todas as métricas de travessia correspondem, mas a declividade mediana é 2,6° contra 11–12°) e Rio Tinto em Haworth.

## 6. Capacidade discriminante (controles com dados reais)
Scripts: `scripts/geomorph_controls.py` (perfis reais do Copernicus nos 16 sítios, deslocados 1, 2, 3 e 5 km em N/L/S/O, nas 4 escalas) e `scripts/geomorph_audit*.py`. Saídas: `var/geomorph_audit.txt` e `var/geomorph_audit_variants.txt`. Unidade de contagem: pares × 3 finalidades.

### 6.1 Problema encontrado e correção
Com a regra inicial (z ≤ 2 + poder discriminante), **contrastes claros correspondiam**:

| Par | Declividade mediana | Antes | Agora |
|---|---|---|---|
| Haworth × Puʻu Nēnē | 15,8° × 1,3° | travessia **e** acidentado | nenhuma |
| Malapert × Puʻu Nēnē | 11,0° × 1,3° | travessia **e** acidentado | nenhuma |
| Haworth × Shawmere | 15,8° × 3,6° | acidentado | nenhuma |
| Haworth × Twin Sisters | 15,8° × 30,3° | nenhuma | nenhuma |

**Causa:** as finalidades de travessia e terreno acidentado não usavam a declividade mediana, e um sítio muito heterogêneo (Puʻu Nēnē: p90 6,3 ± 7,4°) é "compatível" com quase tudo nas outras métricas.
**Correção (só no componente geomorfológico):** toda finalidade exige também a declividade mediana compatível, porque o nível de declividade é o controle de primeira ordem das operações de superfície. A correção **só remove** correspondências e não mudou nenhum limiar.
**Alternativas testadas e rejeitadas:**
* **k = 2** (incerteza combinada ≤ metade do espalhamento) derruba o autocontrole de 65% para 22%.
* **Espalhamento robusto** (MAD) derruba o autocontrole de 65% para 38–43% (com e sem a exigência de declividade).

Os dois eliminam falsos positivos à custa de não reconhecer o próprio terreno.

### 6.2 Controles, L = 60 m (regra final)
| Controle | Taxa de correspondência |
|---|---|
| Positivo: mesmo sítio deslocado 1 km (famílias sobrepostas) | 78/120 (65%) |
| Positivo: 2 km | 76/120 (63%) |
| Positivo: 3 km (sem sobreposição) | 51/120 (43%) |
| Positivo: 5 km | 47/120 (39%) |
| Positivo lunar: Shackleton, Malapert e Haworth deslocados 0,5 e 1 km | 72/72 (100%), só com sobreposição |
| Negativo: pares de sítios terrestres distintos | 30/135 (22%) |
| Contrastes nomeados (Twin Sisters × Shawmere, Puʻu Nēnē, Sudbury; Haworth × Twin Sisters, Shawmere, Puʻu Nēnē; Malapert × Puʻu Nēnē) | 0 correspondências |

**Leitura:**
1. **Sobreposição infla o controle positivo.** A 1 km, as famílias compartilham boa parte das janelas; os 100% lunares só valem com sobreposição. O raio do LOLA polar (≤ 3 km, limite do GDS) não permite deslocamentos lunares sem sobreposição.
2. **Os 35% de falha a 1 km vêm todos da verificação de poder discriminante** (o teto não muda de z ≤ 1,5 a z ≤ 3): sítios heterogêneos (Samail, El Tatio) são declarados não discriminantes, como deveriam.
3. **Sem sobreposição, o mesmo sítio corresponde em ~40% e sítios distintos em 22%.** É uma separação real, mas modesta. Parte dos "negativos" pode ser semelhança verdadeira (por exemplo Shawmere × Sudbury, os dois de baixo relevo no Escudo Canadense), então 22% é um teto para a taxa de falso positivo, não uma medida exata dela.
4. **Consequência prática:** com 10 sítios elegíveis, ~2 correspondências por finalidade seriam esperadas mesmo entre terrenos distintos. Por isso cada correspondência deve ser lida pelos seus valores (seção 5), não pela simples presença.

### 6.3 Sensibilidade
* **Escala** (negativos / positivos a 3 km): 60 m: 30/135 e 51/120 · 120 m: 26/135 e 55/120 · 240 m: 30/135 e 60/120 · 480 m: **nenhum sítio válido** (janela de 1 km pequena demais para 30 células). O comportamento é estável entre 60 e 240 m, e as escalas nunca são misturadas.
* **Critério z**, só como sensibilidade, sem recalibrar a produção. Negativos / positivos a 3 km:

  | z | 1,0 | 1,5 | 2,0 | 2,5 | 3,0 |
  |---|---|---|---|---|---|
  | Negativos | 9/135 | 25/135 | 36/135 | 40/135 | 41/135 |
  | Positivos a 3 km | 31/120 | 47/120 | 54/120 | 62/120 | 71/120 |

  (regra inicial, sem exigência de declividade). Nenhum valor de z dá ao mesmo tempo autocontrole alto e falso positivo baixo. **O limite é o conteúdo informativo das métricas diante da heterogeneidade, não o limiar.**
* **Número de janelas válidas** (subamostras de 5 a 8 das 9 janelas lunares): com 8, a mediana muda ≤ 0,4 desvio; com 5, até 1,2 desvio. O mínimo de 5 é marginal, mas todos os casos reais tiveram 9/9.
* **Métricas de baixo poder discriminante:** a fração de pares não discriminantes é maior no IQR de declividade (26/45), seguido da declividade mediana e da rugosidade (9/45 cada). σ e amplitude de relevo: 0/45.
* **Coordenadas imprecisas:** os 6 sítios com precisão pior que 2 km aparecem em `not_comparable` em **todas** as comparações e em nenhuma correspondência, completa ou parcial.

### 6.4 Categorias (não equivalentes)
| Categoria | Sítios |
|---|---|
| Perfil válido (GLO-30) | 16/16 |
| Elegível para comparação (precisão ≤ 2 km) | 10: Samail, Rio Tinto, El Tatio, Cuprite, Puʻu Nēnē, Lonar, Twin Sisters, Merriam, Shawmere, Sudbury |
| Correspondência completa nas 5 regiões | Merriam, Rio Tinto, Cuprite, El Tatio (+ Shawmere e Lonar no ponto L4) |
| Só parcial nas 5 regiões | Samail, Puʻu Nēnē, Lonar, Shawmere, Sudbury |
| Nunca corresponde | Twin Sisters (dunito íngreme, 30°) |
| Análogo lunar documentado no catálogo | 8: Merriam, Shawmere, Sudbury, Kaʻū, Craters of the Moon, Timanfaya, Stillwater, Sittampundi. **Só 3 são elegíveis**; os outros 5 têm coordenada imprecisa. Merriam é o único documentado com correspondência completa |

## 7. Testes, regressões e desempenho
| Verificação | Resultado |
|---|---|
| Suíte automatizada | **217 aprovados, 3 ignorados** (testes ao vivo, já ignorados antes). Eram 198 em `ed1ee18`; +19 de geomorfologia |
| 21 cenários com dados reais (código final) | **20 PASS + Olympus Mons inconclusivo**. **21/21 idênticos a `ed1ee18`** em mineralogia, indicadores, limitações, `terrestrial_analogs` inteiro, `environment` e altitude. Única chave nova: `geomorphology` |
| Marte | inalterado; sem seção `geomorphology` (`null`) |
| Mineralogia lunar | inalterada (L1–L4, Copernicus, Imbrium) |
| Sombra permanente do M³ | Shackleton: mineralogia indisponível, 100% de sombra permanente, 0 sítios (igual); testes de sombra passam |
| `environment` | idêntico; teste de independência passa |
| `geomorphology` × `terrestrial_analogs` | teste dedicado: com a seção forçada a falhar, as outras seções ficam idênticas |
| Ataques adversariais ao ranking | A1–A3 e A5 OK; A4 como antes. **Idêntico a `ed1ee18`** |
| Endpoints usados pelo Skip | `test_api` passa; a resposta é um superconjunto da anterior (campo novo e opcional). Payload antigo sem o campo valida |
| Falhas de provedor | LOLA indisponível → `geomorphology: unavailable / not_attempted` e o resto disponível; mineralogia ausente → a geomorfologia roda; erro interno → só a seção falha. Falha do Copernicus não afeta produção (o JSON é pré-calculado; o gerador registra o erro por sítio) |
| Inconclusivo não recomenda | `comparisons` vazio; testes de raio pequeno e cobertura parcial |
| JSON terrestre | 16/16 sítios com URL real do bucket Copernicus, blocos e horário; nenhum valor sintético |
| Latência | seção geomorfológica: **0,05–0,15 s**, contra 20–30 s de análise (< 1%); 0,13 s com 200 mil disparos |

**Diff:** 5 arquivos alterados (+98/−6) e 10 novos (~1.150 linhas, contando scripts e testes), mais o JSON de 97 KB. Íntegra em `var/geomorphology.diff`.

## 8. Limitações (as quatro últimas também vão na resposta da API)
1. **Discriminação limitada entre relevos intermediários** (22% dos pares distintos correspondem); só contrastes fortes são confiáveis. *(API)*
2. **A incerteza é heterogeneidade espacial**, não erro de medição; z ≤ 2 é critério operacional, não prova de equivalência. *(API)*
3. **DSM:** vegetação e construções entram na altitude terrestre (Shawmere e Sudbury têm floresta). **Rio Tinto é distrito mineiro:** parte do relevo pode ser antrópica (cavas), o que **não foi verificado**. *(API, a parte DSM)*
4. **Escala:** nada abaixo de 60 m (blocos, rochas, regolito). Não há avaliação de rota, trafegabilidade ou segurança. *(API)*
5. **Fora dos polos, o LOLA é esparso:** Copernicus e Imbrium ficam inconclusivos. O controle positivo lunar sem sobreposição não foi possível (limite de tamanho do GDS no polo).
6. **Só 3 dos 8 análogos lunares documentados são comparáveis** (coordenadas).
7. **Correspondência não implica** composição, gravidade, iluminação, temperatura ou regolito semelhantes (nota na API).

## 9. Prontidão
| Critério | Situação |
|---|---|
| Nenhuma regressão (Marte, mineralogia, sombra, environment, ranking, Skip) | ✅ |
| Inconclusivo explícito sem valores artificiais | ✅ |
| Rejeita contrastes claros | ✅ (depois da correção da seção 6.1) |
| Reconhece o mesmo terreno | ⚠ 65% com sobreposição; ~40% sem |
| Distingue relevos intermediários | ⚠ só modestamente (40% × 22%) |
| Proveniência e dados reais | ✅ |
| Português e inglês | ✅ |

**Recomendação:** publicável **como seção experimental e aditiva**, porque não altera nada do que já existe e informa os próprios limites. Mas a fase **não está concluída como método de recomendação**: as correspondências são evidência fraca a moderada e devem ser apresentadas como tal. Sem commit, push ou deploy até sua autorização. Rollback: `ed1ee18`.

## 10. Fase 3: lacunas concretas
1. **Coordenadas precisas para os 5 análogos lunares documentados** hoje excluídos (Kaʻū, Craters of the Moon, Timanfaya, Stillwater, Sittampundi), com fonte publicada; sem isso, o catálogo lunar comparável tem só 3 sítios.
2. **Terrenos de parede de cratera e maciço com declividade mediana de 11–16°** e baixa heterogeneidade: nenhum sítio elegível cobre Haworth em travessia ou terreno acidentado. Candidato já identificado: **Haughton** (cratera de impacto, Ártico canadense), fora do catálogo.
3. **Análogos sem vegetação e sem mineração**, para que o DSM represente o terreno (e para verificar Rio Tinto).
4. **Altimetria lunar de maior resolução fora dos polos** (por exemplo SLDEM2015 ou DTMs do LROC NAC), para Copernicus e Imbrium: é um provedor novo, fora do escopo desta fase.
5. **Controle positivo lunar sem sobreposição:** pedidos LOLA em mosaico para cobrir mais de 3 km no polo.
6. **Métricas com mais poder discriminante** antes de ampliar o catálogo, como distribuição completa de declividades (por exemplo, distância entre histogramas) em vez de três estatísticas resumo, a validar contra os mesmos controles.

## Decisão científica
**A. O método distingue terrenos semelhantes e diferentes?** Em parte.
* **Contrastes fortes:** sim. 0 de 7 contrastes nomeados correspondem, e Twin Sisters nunca corresponde.
* **Relevos intermediários:** só modestamente. Sem sobreposição, o mesmo terreno corresponde em ~40% e sítios distintos em 22%.
* **Falsos positivos claros:** existiam (Haworth × Puʻu Nēnē) e foram corrigidos pela exigência de declividade, sem perda no autocontrole.

**B. Correspondências sustentadas pelos dados:**
* **Mais fortes (valores próximos, não só compatíveis):** Rio Tinto × Malapert e Rio Tinto × Shackleton, em travessia e terreno acidentado. Ressalva: Rio Tinto não é análogo lunar documentado, e parte do seu relevo pode ser de mineração.
* **Compatível, e o único análogo lunar documentado nessa situação:** Merriam (JSC-1) × Shackleton, Malapert e Haworth, para mobilidade (Haworth no limite da rugosidade).
* **Fracas:** El Tatio e Cuprite em mobilidade (mediana 2–2,5× menor).

**C. Sem correspondência demonstrável:**
* **Haworth:** travessia e terreno acidentado.
* **Copernicus e Mare Imbrium:** **inconclusivos** por cobertura do LOLA. Isso é diferente de "sem correspondência".

**D. Limitações que devem ficar na API:** já estão nela.
* critério operacional, não prova de equivalência;
* incerteza = heterogeneidade espacial;
* discriminação limitada em relevo intermediário (22%);
* DSM com vegetação e construções;
* escala mínima de 60 m;
* sem avaliação de rota ou segurança;
* não implica composição nem condições semelhantes;
* correspondência calculada ≠ análogo documentado.

**E. Pronta para deploy?** **Tecnicamente sim** (zero regressões; seção aditiva e honesta sobre os próprios limites). **Cientificamente, só como seção experimental**: ela não sustenta "recomendações" de análogos geomorfológicos. A fase **não** fica declarada concluída como método de recomendação. Aguardo sua decisão.

**F. Lacunas para a fase 3:** seção 10. Em resumo:
* coordenadas precisas para 5 dos 8 análogos lunares documentados;
* análogos de parede de cratera e maciço (11–16°), como Haughton;
* sítios sem vegetação e sem mineração;
* altimetria lunar melhor fora dos polos;
* controle lunar sem sobreposição;
* métricas mais discriminantes.
