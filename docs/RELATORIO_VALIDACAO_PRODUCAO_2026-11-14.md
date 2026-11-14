# Validação em produção — 2026-11-14

## Status
**Em produção: commit `abb10cb`** (contém `877571a`), publicado em 2026-11-14. Nenhuma regressão crítica; **rollback não executado**. Duas divergências não críticas e quatro limitações científicas estão registradas abaixo, com correções propostas que **não** foram aplicadas, porque precisam da sua aprovação.

## Antes do deploy
| Verificação | Resultado |
|---|---|
| Branch | `main`; 2 commits à frente de `origin/main` (`877571a`, `abb10cb`) |
| Versão anterior em produção (rollback) | `fa2d329`. Rollback: `git revert abb10cb 877571a` + push (sem reescrever histórico) |
| Schema | Só **acréscimos opcionais**: `terrestrial_analogs.sites[].rank` e `terrestrial_analogs.masked_evidence`. Nada removido nem renomeado; o contrato de entrada (`extra="forbid"`) não mudou. Compatível com o Skip. |
| Deploy confirmado | `/openapi.json` passou a expor `masked_evidence` ~36 s após o push |

## Resultados efetivamente verificados (produção, dados reais, `use_cache=false`)
| Bloco | Resultado |
|---|---|
| Testes automatizados no commit publicado | **114/114** |
| Bateria científica (21 cenários) | **20 PASS, 1 INCONCLUSIVO** (M8 Olympus Mons: sem cobertura CRISM, como esperado). Idêntica à execução local. |
| Falsos positivos de poeira (Tharsis/Amazonis, 6 cenários) | **0** (só óxido férrico, que é real na poeira) |
| Mascaramento por gelo (calotas norte e sul, fora da calibração) | gelo detectado; olivina/sulfato mascarados; nenhum sítio por família mascarada |
| Iluminação lunar (polo sul) | mineralogia "indisponível", 0 sítios |
| Copernicus (olivina do pico central) | **acerta** (antes falhava) |
| Ranking (adversarial) | A1 ordem do catálogo OK · A2 ausência não conta OK · A3 corpos não se misturam OK · A5 amplo não supera específico OK · A4: o 1º lugar só muda ao remover detecções fortes (esperado) |
| Integração com os endpoints do Skip (`validate_production.py`) | **33/34** na 1ª execução; o caso que falhou passou na repetição (ver divergência 1) |
| Controle positivo de **sulfato** (Aram Chaos, FRT000098B2) | **detectado**, com margem mínima (ver limitação 2) |
| Poeira **fora de Tharsis** (8 Elysium + 8 Arabia) | **15/16 limpos**; 1 olivina em Elysium, na margem (ver limitação 1) |
| Skip, ponta a ponta | calota polar: evidência de gelo, aviso de mascaramento, "evidência ampla" e avisos de empate exibidos; polo sul da Lua: "Dados indisponíveis", sem sítios, sem erro |

## Divergências encontradas
1. **Tempo de análise lunar (não crítico).** Na 1ª execução, a Lua no antimeridiano (0,5°N, 179,95°E) estourou o limite de 240 s. Na repetição, completou em 45 s. Causa: o servidor de imagens do PDS estava lento (leituras de 69 s com retentativas), e o novo filtro de qualidade do M³ leu **3 observações** em vez de 1. O filtro aumenta o risco de estourar o tempo quando o PDS está lento. **Correção proposta:** dar ao filtro um orçamento de tempo, como já existe na topografia.
2. **Filtro de qualidade do M³ em terras altas (científico).** Nesse ponto do lado oculto, as **três** observações independentes tiveram banda de 1 µm negativa (−0,63 a −1,00). Isso sugere um efeito sistemático do produto M³ em terreno claro, e não um defeito de uma observação isolada, que era a premissa do filtro. O resultado é conservador (o sistema não infere mineral), mas pode estar descartando uma leitura válida de "terra alta feldspática". **Proposta:** investigar com controles de terras altas documentadas antes de mudar o filtro.

## Limitações científicas que permanecem
1. **Olivina com folga pequena.** Poeira chega a 0,043, a olivina documentada fica em 0,063 a 0,071, e o mínimo é 0,05. Em Elysium (27,44°N, 143,34°E) a poeira deu 0,052 e foi aceita, com índice de 1 µm genérico baixo (0,015), o que indica provável falso positivo. **Proposta** (não aplicada): exigir coerência física entre OLINDEX3 e BDI1000IR, validada com novos controles.
2. **Sulfato com margem mínima.** Em Aram Chaos o sulfato foi detectado só acima do mínimo (BD2100_2 0,0061 contra 0,0054; SINDEX2 0,0195 contra 0,019). Um depósito um pouco mais fraco não seria detectado.
3. **Apollo 17 sem identificação mineral satisfatória.** Duas observações foram descartadas como suspeitas e a terceira não sustenta nenhuma família mineral. O sistema não erra, mas também não acerta o basalto do vale de Taurus-Littrow.
4. **Mínimos vêm de controles, não de valores publicados** (45 controles em `data/calibration/crism_controls.json`). Arabia e Elysium podem ter mineralogia local real; nenhum desses pontos foi verificado na literatura um a um.

## Frontend (Skip) — o que falta
* `rank` não é exibido como número, mas os empates aparecem pelos avisos em `notes`. Funciona sem mudança.
* `masked_evidence` aparece pelo aviso em `notes`. Funciona sem mudança.
* "Mineralogia indisponível" mostra só a mensagem genérica, sem o motivo (por exemplo, Sol abaixo do horizonte). **Proposta:** o Skip mostrar a mensagem de `problems` da seção, como já foi pedido para a topografia.

## Arquivos de evidência (locais, não versionados)
`var/prod_abb10cb/`: `pytest.log`, `science.log`, `science_tests.json`, `adversarial.log`, `validate_production.log`, `extra_checks.json`.

## Fontes das novas verificações
* Aram Chaos, sulfatos: Lichtenberg et al. 2010, JGR Planets, doi:10.1029/2009JE003353
* Arabia, Elysium e Tharsis como regiões de poeira de baixa inércia térmica: Putzig et al. 2005, Icarus 173; Haberle 2001 (resumo DPS)
