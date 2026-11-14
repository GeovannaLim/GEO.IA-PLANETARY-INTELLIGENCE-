# Validação final do backend — NASA Space Apps 2026

**Desafio:** Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars.
**Data:** 2026-11-14.

**Versões**

| Item | Valor |
|---|---|
| Base de produção e de rollback | `ed1ee18` (Render) |
| Commit local não publicado | `481fdc2` (relatório de validação de produção) |
| Estado deste trabalho | fases 2, 3A e integração final consolidadas localmente; **sem commit, push ou deploy** |

**Decisão: APROVADO para publicação, com riscos operacionais documentados (Seção 8).** A publicação depende de
autorização explícita para commit, push e deploy.

## 1. Resumo das mudanças consolidadas

| Área | Mudança | Efeito em `ed1ee18` |
|---|---|---|
| Geomorfologia Lua–Terra (fase 2) | Nova seção opcional `geomorphology`, só para a Lua: perfis LOLA RDR × Copernicus GLO-30, comparação por finalidade com z ≤ 2, teste de poder discriminante e portão de declividade mediana | aditiva; Marte recebe `geomorphology: null` |
| Fase 3A | Rio Tinto marcado como relevo misto (`modified_relief_references`); Craters of the Moon remedido no Highway Flow (HF16001); estudo de distribuição de declividades **não adotado** | só dentro de `geomorphology` |
| Integração (esta etapa) | `experimental: true` e nota "Seção experimental" na geomorfologia | aditiva |
| Integração (esta etapa) | **Prazo próprio para a mineralogia M3** (`mineralogy_deadline_s = 200 s`): se o PDS estiver lento, só a mineralogia falha (`failed/provider_error`), em vez do job inteiro | corrige perda de seções (Seção 5) |
| Integração (esta etapa) | Proveniência: quando a observação M3 preferida não pode ser lida e outra é usada, a resposta passa a declarar isso em `limitations` e `problems` | aditiva (texto) |
| Integração (esta etapa) | **Cache:** um resultado com seção em `provider_error` não é reaproveitado do cache de 24 h; o pedido seguinte recalcula | evita servir uma queda temporária como resultado |
| i18n | Traduções pt-BR de todos os textos novos | aditiva |

**Arquivos alterados em relação a `ed1ee18`**

| Grupo | Arquivos |
|---|---|
| Rastreados | `app/config.py` (+3), `app/services/jobs.py` (+12/−1, cache), `app/i18n.py` (+75), `app/pipelines/common.py` (+9/−3), `app/pipelines/lunar.py` (+45/−3), `app/providers/http.py` (+1, host do Copernicus na lista de hosts permitidos), `app/schemas/analysis.py` (+19), `tests/live/test_live_services.py` (+5/−1) |
| `docs/VALIDACAO_SOMBRA_MINERALOGIA_LUNAR.md` | já está em `481fdc2` |
| Novos (produção) | `app/science/geomorphology.py`, `app/science/geomorph_analogs.py`, `app/providers/copernicus_dem.py`, `app/data/earth_site_geomorphology.json` (97 KB, dados reais) |
| Novos (testes) | `tests/unit/test_geomorphology.py`, `tests/integration/test_lunar_geomorphology.py`, `tests/integration/test_lunar_m3_resilience.py` |
| Novos (validação, fora do runtime) | `scripts/build_earth_geomorphology.py`, `scripts/geomorph_*.py`, `scripts/final_regression.py`, `scripts/science_tests_retry.py`, `scripts/provider_timing.py`, `scripts/scenario_diff.py`, `scripts/compare_scenarios.py` |
| Novos (documentação) | `docs/VALIDACAO_GEOMORFOLOGIA_LUA_TERRA.md`, `docs/VALIDACAO_FASE3A_ANALOGOS_TERRESTRES.md` e este documento |
| **Sem nenhuma mudança** | API e rotas, `main.py`, armazenamento, autenticação, CORS, dependências (`requirements`), infraestrutura do Render, frontend Skip, limiares mineralógicos, critérios de sombra permanente, ranking marciano |

## 2. Fontes de dados e proveniência

| Uso | Fonte | Proveniência na resposta |
|---|---|---|
| Imagem | NASA Trek (WMTS) | `imagery.layers[]`, `data_sources[]` |
| Topografia da Lua | LOLA RDR via ODE GDS | `topography`, `data_sources[]` (consulta) |
| Topografia de Marte | MOLA via ODE GDS | idem |
| Mineralogia da Lua | M3 L2 (PDS Imaging via ODE) | `mineralogy.product_used`, `data_sources[].product_id`/`url`, datas de observação |
| Mineralogia de Marte | CRISM MTRDR (PDS Geosciences) | idem |
| Iluminação e sombra (polo sul) | modelo LOLA/PGDA (Mazarico et al. 2011) | `environment.products`, `data_sources[]` |
| Geomorfologia, Lua | os mesmos disparos LOLA da topografia | `geomorphology.moon_profile`, `source_ids` |
| Geomorfologia, Terra | Copernicus DSM GLO-30 (AWS Open Data), pré-medido em `earth_site_geomorphology.json` | por sítio: `dem_tiles`, `dem_retrieved_at` e `measured_unit` quando houver |
| Análogos minerais | catálogo curado (`terrestrial_analog_sites.json`), referências publicadas | `terrestrial_analogs` |

Nenhum dado sintético entra em produção. Os dados sintéticos existem só nos testes automatizados.

## 3. Estado final das três fases científicas

| Fase | Estado | Para o público |
|---|---|---|
| Mineralogia e análogos minerais (`ed1ee18`) | estável e validada; nada mudou | resultado principal |
| Fase 2: geomorfologia | funcional; discriminação **modesta**: o mesmo terreno sem sobreposição corresponde em 41% dos casos, contra 23% para terrenos distintos e 0/45 para contrastes fortes | **experimental**, nunca recomendação |
| Fase 3A | alternativas de distribuição sem melhora demonstrável, então o critério atual foi mantido; Rio Tinto ficou como referência de relevo modificado; Craters of the Moon corrigido; candidatos novos fora do catálogo | idem |

**Confirmações do catálogo**

| Item | Situação |
|---|---|
| Craters of the Moon | `43.463336, -113.571361`; precisão de 0,1 km; Highway Flow HF16001; Tolometti 2021 em `measured_unit`; ponto antigo em `catalog_reference_point` |
| `UNIT_OVERRIDES` | a correção é reaplicada em qualquer reconstrução; `relief_modification` é preservado |
| Rio Tinto | `mixed_natural_and_mining`; nunca aparece em `matches` |
| Candidatos da fase 3A | 0 ocorrências em `app/` e nas respostas |
| Inelegíveis por coordenada | `kau_desert` (3 km), `dresser` (5), `timanfaya` (3), `stillwater` (5) e `sittampundi` (15) só aparecem em `not_comparable` |

**Correspondência Craters of the Moon × Shackleton (travessia e terreno acidentado).** Ela segue o critério
operacional. A documentação a classifica como **fraca**:
- a declividade mediana é 5,2° contra 12,1°;
- o portão só passa pela incerteza de Shackleton (±3,5°);
- falha no teste de distribuição.

A API não faz nenhuma interpretação além disso.

## 4. Testes automatizados

| Bateria | Resultado | Evidência |
|---|---|---|
| Suíte unitária e de integração | **222 aprovados, 3 ignorados** (os testes ao vivo, que precisam de `GEOIA_LIVE_TESTS=1`) | `var/pytest_final.log` |
| Testes ao vivo (NASA real) | 3/3 com o PDS normal. Num momento de PDS lento, Imbrium devolveu mineralogia `failed/provider_error` pelo prazo de 150 s, o que levou ao ajuste para 200 s (Seção 5). | `var/pytest_live_final.log` |
| Testes novos de resiliência do M3 | 3/3: só a mineralogia falha no timeout; o fallback de observação é declarado; geomorfologia marcada `experimental` | `tests/integration/test_lunar_m3_resilience.py` |
| Teste novo de cache | 1/1: resultado com `provider_error` não é reaproveitado | `tests/integration/test_api.py` |
| Controles geomorfológicos positivos e negativos, com dados reais | idênticos à fase 3A | `var/geomorph_dist_study_final.txt` |
| Cobertura insuficiente, raio pequeno, falha de LOLA, crash da seção | aprovados | `tests/integration/test_lunar_geomorphology.py` |
| Coordenadas e proveniência | aprovados (relevo modificado, espalhamento inalterado, `measured_unit`) | `tests/unit/test_geomorphology.py` |
| Adversariais do ranking (A1–A5) | **idênticos à fase 2 e a `ed1ee18`**: A1, A2, A3 e A5 OK; A4 com 14 achados, os mesmos de antes | `var/adversarial_final.log` |
| Schemas | 21/21 respostas reais válidas em `AnalysisResult`; uma resposta antiga sem `geomorphology` continua válida | — |
| Falhas de provedor | aprovados (ODE, GDS 503, M3 ausente, iluminação, timeout do M3) | `tests/integration/*` |

## 5. Problema corrigido: falha externa do PDS/M3

**Antes (comportamento de `ed1ee18`)**
- Não havia prazo para a etapa M3.
- Com o PDS lento, o job inteiro passava dos 240 s e terminava `failed`. Perdiam-se topografia, imagem, ambiente e
  geomorfologia já concluídas.
- Medições de hoje:
  - 73 ReadTimeout do PDS;
  - L1–L4 falharam assim;
  - um controle com o código `ed1ee18`, rodado à parte, também falhou em L2. A falha é externa.

**Medição por provedor** (`scripts/provider_timing.py`, `var/provider_timing.txt`; soma das requisições
concorrentes)

| Caso | Tempo total | M3 (PDS Imaging) | ODE GDS | Demais provedores |
|---|---|---|---|---|
| Mare Imbrium | 42 s | 103 requisições, soma 129 s, máx. 32 s | 7 s | < 3 s cada |
| Shackleton | 138 s | 249 requisições, soma 690 s, máx. 44 s | 57 s (máx. 51 s) | < 3 s |
| Copernicus | 132 s | 206 requisições, soma 337 s, **máx. 67 s numa única leitura** | 6 s | < 2 s |
| Jezero (Marte) | 6 s | CRISM: 24 requisições, máx. 1,8 s | 6 s | < 2 s |

**Correção mínima.** Usa o mesmo padrão já existente para a altimetria (`altimetry_deadline_s`):
- `mineralogy_with_deadline` em `app/pipelines/lunar.py` limita a etapa M3 a `mineralogy_deadline_s = 200 s`.
- Os 200 s cobrem os 150–203 s observados sob lentidão e deixam 40 s antes do limite do job. Em operação normal o
  M3 leva 10–60 s.
- **Quando o prazo estoura:**
  - `mineralogy.status = failed` e `reason = provider_error`;
  - `indicators` vazio e `product_used` nulo;
  - limitação explícita: "A timeout is not evidence that minerals are absent" (traduzida);
  - um registro em `data_sources` com `status=error` e um em `problems`;
  - `terrestrial_analogs` não usa a medição ausente (0 sítios, `not_attempted`);
  - o job termina `completed`, com as outras seções entregues.
- **Garantias científicas:**
  - nenhum valor inventado;
  - timeout nunca é tratado como ausência;
  - nenhum resultado de outro ponto;
  - o resultado parcial é declarado pelos status de cada seção.
- **Proveniência:** se a observação M3 preferida falha e outra que contém o ponto é usada, a resposta diz qual foi
  ignorada, por quê e qual foi usada. Isso resolve a diferença de produto vista em L1 na fase 3A.
- **Contrato:** nenhuma mudança de schema para a mineralogia. `failed/provider_error` já existia (falha da busca
  ODE).

## 6. Regressão científica com dados reais: 21 cenários

**Execução**
- Servidor local com o código final, dados reais, `use_cache=false`, critérios pré-registrados
  (`scripts/science_tests.py`).
- Comparação com `ed1ee18` (`var/prod_ed1ee18/science_tests.json`) por `scripts/final_regression.py`.
- A comparação cobre valores científicos de mineralogia, ranking (`terrestrial_analogs`), `environment`,
  topografia, imagem, `earth_analogs` e confiança.
- Os `source_ids` são resolvidos para (serviço, instrumento, produto, status). A numeração `src-NN` segue a ordem de
  conclusão das requisições paralelas, então só o conteúdo é comparado.

**Resultado**

| Cenários | Veredito final | Comparação com `ed1ee18` |
|---|---|---|
| M1–M7, M9 (Marte) | PASS | idênticos |
| M8 Olympus (controle negativo) | INCONCLUSIVE, igual a `ed1ee18` | idêntico |
| D1–D6 (poeira) e I1–I2 (gelo) | PASS | idênticos |
| L1 Chang'e-3 | PASS | idêntico; mesmo produto M3 (`M3G20090513T191408`) |
| L2 Copernicus (olivina) | PASS **na segunda execução** | idêntico; produto `M3G20090416T122951`, igual à produção |
| L3 Mare Imbrium | PASS **na segunda execução** | idêntico; produto `M3G20090609T183254` |
| L4 polo sul (controle de sombra M3) | PASS | idêntico; geomorfologia `available` e `experimental` |

**Total: 21/21 idênticos a `ed1ee18`** em valores e proveniência. A única chave nova é `geomorphology`, só na Lua.

**Primeira execução de L2 e L3**
- O PDS estava lento, e o novo prazo devolveu mineralogia `failed/provider_error` com 0 análogos.
- O avaliador pré-registrado marcou L2 INCONCLUSIVE e L3 FAIL ("no M3 data"). Esses vereditos **não** foram
  aceitos como aprovação nem como regressão.
- Repeti só esses casos (`scripts/science_tests_retry.py`, que reexecuta casos com `provider_error` sem mudar
  critério). Com o PDS normal, passaram em 90 s e 60 s.
- Evidências: `var/science_tests_final.log` e `var/science_tests_final_retry.log`.

## 7. Prontidão pública

| Item | Resultado |
|---|---|
| Endpoints | inalterados: `POST /v1/{earth,lunar,mars}/analyze`, `GET /v1/jobs/{id}`, `GET /v1/reports/{id}`, `GET /v1/planetary/datasets` e `GET /health` |
| JSON válido em falha parcial | sim: `status=completed` com seções `failed`/`unavailable` e `problems[]` (21/21 validados) |
| Estados representáveis | `processing` (202 com placeholders), `completed`, `failed`; por seção: `available`, `partial`, `unavailable`, `failed` com `reason`. Testado: 422 com entrada inválida, 422 com raio acima do limite, 404 para job inexistente, cache com `cache.hit` |
| Português e inglês | `?lang=pt-BR`; todos os textos novos traduzidos e verificados nas respostas reais |
| Informação sensível | 0 caminhos locais, tracebacks, chaves ou tokens nas 21 respostas reais |
| Latência | a geomorfologia leva 0,06–0,12 s. Lua: 40–140 s com o PDS normal e até 205 s com o PDS lento. Marte: cerca de 6–12 s. |
| Login | não mudou: os endpoints públicos continuam como em `ed1ee18`; CORS restrito pela configuração; sem `allow_origins=["*"]` |
| Mudanças involuntárias | nenhuma (Seção 6) |

## 8. Riscos operacionais remanescentes

1. **PDS/M3 lento: risco médio.** Com o PDS degradado, a mineralogia lunar pode vir `failed/provider_error`. Agora
   isso é seguro, porque o resto é entregue. O frontend deve mostrar como "fonte indisponível, tente mais tarde", e
   nunca como "sem minerais".
2. **Cache de um resultado com falha de provedor: corrigido.**
   - O problema: o prazo do M3 faz um job lento terminar `completed`, e não mais `failed`. Esse resultado degradado
     seria servido do cache por 24 h.
   - A correção (`app/services/jobs.py`, `provider_failure`): um resultado com qualquer seção em `provider_error`
     ainda é devolvido a quem o pediu, mas não é reaproveitado; o pedido seguinte recalcula.
   - Efeito colateral aceito: um ponto com o provedor fora do ar recalcula a cada pedido.
3. **ODE GDS no polo: risco baixo.** Até 51 s numa requisição; já tem o prazo de 150 s.
4. **Plano gratuito do Render:** hibernação e arranque a frio, e concorrência de 3 jobs. Já existia.
5. **Limite do job de 240 s:** iluminação e imagem não têm prazo próprio, mas nas medições ficaram abaixo de 3 s.

## 9. Limitações científicas que o frontend precisa mostrar

**Geomorfologia**
- Comparação **experimental**: as correspondências não são análogos validados nem recomendações.
- z ≤ 2 é um critério operacional, não prova de equivalência. A incerteza é heterogeneidade espacial.
- A discriminação é limitada entre relevos intermediários (cerca de 2 coincidências por finalidade).
- O Copernicus é um modelo de superfície e inclui vegetação e construções.
- Copernicus e Mare Imbrium são inconclusivos por cobertura LOLA.
- Rio Tinto é relevo modificado por mineração.

**Mineralogia**
- `provider_error` não significa ausência.
- `inconclusive_evidence` (`lunar_no_mafic_band`) nunca escolhe sítios.
- Pixels em sombra permanente são excluídos.
- Similaridade não é probabilidade de ocorrência mineral.

**Ambiente**
- Iluminação derivada de modelo, válida só para o polo sul.
- O ambiente não mede gelo.

**Análogos minerais**
- Relação documentada na literatura, diferente de correspondência calculada.

## 10. Contrato de integração para o Skip

**Fluxo**
1. `POST /v1/lunar/analyze?lang=pt-BR&wait_s=0` com o corpo `{latitude, longitude, radius_km}`.
2. Consultar `GET /v1/jobs/{analysis_id}?lang=pt-BR` até `status != "processing"` (código HTTP 202 → 200).
3. Mostrar o progresso por `progress[]`.
4. O raio mínimo útil para a geomorfologia é 2 km (com menos, a seção vem `unavailable/insufficient_data`).

| Campo | O que exibir | Estados e observações |
|---|---|---|
| `status` | estado do job | `processing`: carregando; `completed`: mostrar seções; `failed`: erro com `problems[]` |
| `<seção>.status` e `<seção>.reason` | estado de cada seção | `available`, `partial`, `unavailable`, `failed`; `reason`: `provider_error` ("fonte indisponível"), `no_coverage`, `insufficient_data`, `not_supported`, `not_attempted`, `invalid_data` |
| `mineralogy.indicators[]`, `spectral_character`, `product_used`, `limitations[]` | indicadores, produto M3/CRISM e limitações | `detected: null` significa indeterminado. Nunca exibir ausência quando `reason=provider_error`. |
| `terrestrial_analogs.sites[]` (`rank`, `name`, `latitude`/`longitude`, `coordinate_precision_km`, `justification`, `similarities`, `differences`, `limitations`), `basis`, `inconclusive_evidence`, `uncertain_evidence` | análogos minerais documentados | `basis=global_context` deve aparecer como contexto, não como análogo regional. Empates compartilham `rank`. |
| `environment.sunlit_fraction`, `permanent_shadow_fraction`, `earth_visible_fraction`, `centre`, `analyzed_extent`, `notes[]`, `limitations[]` | iluminação e sombra no polo sul | fora do polo: `unavailable/not_supported`; selo "derivado de modelo" |
| `geomorphology.experimental` | selo **"Experimental"** obrigatório | sempre `true` |
| `geomorphology.status`, `reason`, `notes[]` | estado da comparação | `unavailable/insufficient_data` (raio ou cobertura): "inconclusivo" |
| `geomorphology.moon_profile` (`baseline_m`, `windows_valid`, `metrics.{nome}.value`, `uncertainty`, `unit`, `definition`) | perfil lunar | métricas: `slope_median_deg`, `slope_p90_deg`, `slope_iqr_deg`, `roughness_m`, `relief_sigma_m`, `relief_amplitude_m` |
| `geomorphology.comparisons.{rover_mobility, traverse_planning, rugged_terrain_operations}` | uma aba ou bloco por finalidade (`label`) | `result`: `correspondence`, `no_demonstrable_correspondence` ou `inconclusive` |
| `…matches[]` | correspondências **calculadas** completas | mostrar `metrics.*.z`, `documented_lunar_analog` e `relationship = calculated_geomorphological_correspondence`; `measured_unit` quando existir |
| `…partial_only[]` | parciais: **não** são correspondência | `corresponding_metrics`, `slope_level_gate`, `non_discriminating` |
| `…not_comparable[]` | sítios sem coordenada precisa | lista simples |
| `…modified_relief_references[]` | relevo modificado (Rio Tinto) | selo "relevo modificado por mineração"; nunca listar como análogo |
| `geomorphology.limitations[]`, `earth_reference` | limitações e referência Copernicus | exibir sempre que houver comparação |
| `data_sources[]` (`provider`, `instrument`, `product_id`, `url`, `status`, `message`) e `problems[]` | fontes científicas e problemas | `status=error` identifica falha de provedor |
| `cache.hit` | "resultado em cache" | um resultado com `provider_error` nunca vem do cache; para tentar de novo, basta repetir o pedido |

**Compatibilidade.** Todos os campos novos são aditivos e opcionais (`geomorphology`, `experimental`,
`modified_relief_references`, `measured_unit`). Um frontend que os ignore continua funcionando, e nenhum campo
existente mudou de tipo ou de significado.

## 11. Checklist de publicação e rollback

**Antes do deploy** (cada passo só com autorização)
- [ ] Revisar o diff.
- [ ] Fazer commit **incluindo os arquivos novos** de `app/`, `tests/`, `scripts/` e `docs/`:
  - `app/science/geomorphology.py`, `app/science/geomorph_analogs.py`, `app/providers/copernicus_dem.py`;
  - `app/data/earth_site_geomorphology.json`;
  - os 3 arquivos de teste novos;
  - os scripts e os 3 documentos de validação.
- [ ] **Não** versionar `var/`, `.env`, SQLite, caches ou venvs (o `.gitignore` já cobre).
- [ ] Rodar `pytest -q` no commit (esperado: 222 aprovados, 3 ignorados).
- [ ] Push para `origin/main` (inclui `481fdc2`) e deploy automático no Render.
- [ ] Não há dependências novas nem variáveis de ambiente obrigatórias novas. `GEOIA_MINERALOGY_DEADLINE_S` é
  opcional; o padrão é 200 s (o nome segue o prefixo da configuração; conferir em `app/config.py`).

**Depois do deploy**
- [ ] `GET /health` com o commit novo.
- [ ] Rodar `scripts/validate_production.py` e os 21 cenários contra a URL do Render (`scripts/science_tests.py`).
  Se aparecer `provider_error` de M3, usar `scripts/science_tests_retry.py`.
- [ ] Rodar `scripts/final_regression.py var/prod_ed1ee18/science_tests.json var/science_tests.json`. Esperado:
  21/21 idênticos.
- [ ] Conferir uma resposta lunar polar com `?lang=pt-BR` (`geomorphology.experimental=true`).

**Rollback**
- Redeploy de `ed1ee18` no Render, por "Manual Deploy" do commit, ou `git revert` dos commits novos.
- O schema é aditivo e respostas antigas no SQLite continuam válidas, então não há migração a desfazer.

## 12. Decisão

| Critério | Situação |
|---|---|
| Sem regressões científicas não explicadas | ✔ 21/21 idênticos; a primeira falha de L2/L3 é externa e foi explicada |
| Testes automatizados relevantes | ✔ 222/222 aprovados; ao vivo 3/3 com o PDS normal |
| Geomorfologia experimental e independente | ✔ `experimental: true` e nota; nenhuma seção existente mudou (teste de crash) |
| Limitações e proveniência preservadas | ✔ inclusive o fallback de observação M3 |
| Falhas externas tratadas com segurança | ✔ prazo do M3; timeout nunca vira ausência |
| Contrato da API estável | ✔ só campos aditivos |
| Frontend existente compatível | ✔ campos antigos inalterados (não modifiquei o Skip) |

**APROVADO para publicação**, com os riscos da Seção 8 aceitos. Commit, push e deploy aguardam autorização
explícita. Rollback: `ed1ee18`.

## 13. Publicação e validação em produção (`8df1d61`)

Publicação autorizada pela usuária ("Commit and deploy") em 2026-11-14.

**Publicação**
- Commit `8df1d61` com 35 arquivos.
- Push `ed1ee18..8df1d61` para `origin/main`; o push levou junto o commit local `481fdc2`.
- O deploy foi automático no Render (`autoDeploy`).
- Versão confirmada pelo `/openapi.json`, que agora tem `GeomorphologySection.experimental`. Esse schema não
  existe em `ed1ee18`.
- Ficaram fora do commit `var/`, `.env` e os documentos antigos `docs/PROMPT_SKIP_*.md` e `docs/AUDITORIA_*.md`.

**21 cenários reais contra `https://geoia-planetary-backend.onrender.com`**

| Item | Resultado |
|---|---|
| Vereditos | **20 PASS + M8 INCONCLUSIVE**, iguais a `ed1ee18`, **na primeira execução, sem retentativas** |
| Comparação com `ed1ee18` (`scripts/final_regression.py`) | **21/21 idênticos** em mineralogia, `terrestrial_analogs`, `environment`, topografia, imagem, `earth_analogs` e confiança, com a proveniência resolvida |
| Produtos M3 | os mesmos da produção anterior: L1 `M3G20090513T191408`, L2 `M3G20090416T122951`, L3 `M3G20090609T183254`, L4 `M3G20090202T151458` |
| Schema e segurança | 21/21 respostas válidas; 0 caminhos locais, tracebacks ou credenciais |
| Geomorfologia em L4 | `available`, `experimental: true`, nota em pt-BR. Rio Tinto só em `modified_relief_references`; Craters of the Moon em rugged (fraca, conforme a Seção 3) |
| Tempos | Marte 6,5–13 s; Lua 45–103 s, abaixo do prazo do M3 (200 s) e do limite do job (240 s) |

Evidência: `var/prod_8df1d61/science.log` e `var/prod_8df1d61/science_tests.json` (não versionados).

**Rollback:** se necessário, novo deploy de `ed1ee18` no Render.
