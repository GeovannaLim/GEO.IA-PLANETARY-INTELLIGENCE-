# Validação em produção — coerência espacial da olivina (2026-11-14)

## Status
**Em produção: commit `46f3a88`.** Inclui `a38b176`, o relatório anterior. Nenhuma regressão; **rollback não executado**. Para voltar atrás, a versão anterior é **`abb10cb`**: `git revert 46f3a88` + push.

## Antes do deploy
* Commit com código, testes, os 59 controles fixos (`tests/data/olivine_controls.json`), o script de estudo (`scripts/olivine_study.py`, que agora lê os pontos do arquivo fixo e por isso é reproduzível) e a documentação (`docs/DIAGNOSTICO_OLIVINA.md`). Ficaram de fora os prompts do Skip, `var/` e outros arquivos temporários; nenhum dado sensível.
* Schema: só quatro campos **opcionais novos** (`indicators[].spatial_coverage`, `indicators[].uncertain`, `mineralogy.analyzed_extent`, `terrestrial_analogs.uncertain_evidence`). Compatível com o Skip.
* Limiares existentes não foram alterados; o critério de 75% está marcado no código como provisório.

## Resultados verificados em produção (dados reais, sem cache)
| Verificação | Resultado |
|---|---|
| Testes automatizados (commit publicado) | **182/182** |
| Bateria científica (21) | **20 PASS + Olympus Mons inconclusivo** (sem CRISM), igual à versão anterior |
| Integração com os endpoints do Skip | **34/34** |
| Ataques adversariais ao ranking | ordem do catálogo, ausência, Lua×Marte e amplo×específico: OK |
| **59 controles de olivina + Aram Chaos** | **60/60 como esperado**: 14 positivos confiáveis, Elysium incerto, 44 negativos não detectados |
| Campos novos na resposta | presentes em **60/60** análises |
| Português | interpretação "Detecção incerta…", nota em `notes` e limitação da janela traduzidas |

### Locais-chave
| Local | OLINDEX3 | Cobertura | Resultado | 1º lugar no ranking |
|---|---|---|---|---|
| Jezero | 0,0708 | 99% | olivina **confiável** | Samail, Twin Sisters (sem mudança) |
| Nili Fossae | 0,063 | 89% | olivina **confiável** | Samail (sem mudança) |
| **Elysium** | 0,0521 | **66%** | olivina **incerta**, visível em `uncertain_evidence`, sem análogos de olivina | Dresser, Kaʻū, Puʻu Nēnē (antes: Samail, Twin Sisters) |
| Aram Chaos | 0,0482 | 44% | sem olivina; **sulfato continua detectado** | Kaʻū (sem mudança) |

### Área analisada (`analyzed_extent`)
Em todos os casos a janela do CRISM é de **1,1 × 1,1 km** (~1,2 km²), entre **0,4% e 4,3%** do círculo pedido (por exemplo, 0,4% em Nili Fossae, com raio de 10 km). A resposta agora traz isso em `mineralogy.analyzed_extent` e na limitação "não representa a região inteira".

## Limitações que permanecem
1. **O critério de 75% não foi validado de forma independente.** Ele foi calibrado nos mesmos 59 controles e só um falso positivo (Elysium) motivou a regra.
2. **Afloramentos pequenos:** olivina que ocupa menos de ~50% da janela é perdida, e entre ~50% e 75% fica incerta (documentado nos testes).
3. **Os positivos de olivina são todos de Nili Fossae/Jezero**; Argyre, Hellas e Valles Marineris não foram testados.
4. **A mineralogia de Marte cobre só ~1 km² em volta do ponto**, qualquer que seja o raio pedido. Agora isso está declarado, mas a cobertura em si não mudou.
5. Continuam valendo as limitações anteriores: sulfato detectado por margem mínima (Aram Chaos), Apollo 17 sem identificação satisfatória, possível efeito sistemático do filtro do M³ em terras altas lunares, risco de tempo limite quando o PDS está lento, e valores mínimos derivados de controles, não de números publicados.

## Evidências (locais, não versionadas)
`var/prod_46f3a88/`: `pytest.log`, `science.log`, `science_tests.json`, `adversarial.log`, `validate_production.log`, `olivine.log`, `olivine_prod_check.json`.
