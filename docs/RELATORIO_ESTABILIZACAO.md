# Relatório — estabilização, QA e auditoria dos análogos (2026-11-06)

## A. Estado de produção

| Componente | Estado | Evidência |
|---|---|---|
| Render (backend, plano Free) | No ar, versão `e035653` | Regressão real em produção **29/29** (`scripts/validate_production.py`, testes A–G, com origem do Skip) |
| Skip (`geoai-interplanetary.goskip.app`) | Lua e Marte funcionando, bundle `index-BMJCBHYs.js` | Análises reais pela interface antes e depois do deploy; histórico e PDF protegidos |
| GitHub (privado) | Em dia | CI agora roda `pyflakes` + `pytest` + build Docker |
| Testes do backend | **86 aprovados**, 3 pulados (ao vivo, de propósito); `pyflakes` limpo | Local, antes do push |
| QA do Skip (typecheck, lint, build) | **Não executado** — sem acesso ao código | Pedido no `docs/PROMPT_SKIP_QA.md` §9 |

### Testes executados
* **Backend local:** 86 testes (unitários, integração com dublês, API, localização, ausência de fabricação).
* **Produção (29/29):** saúde; Lua (LOLA 35.896 disparos, M3 1.681 pixels, 13 s); Marte Jezero (MOLA, CRISM, 8,8 s); Marte sem cobertura (`no_coverage`); Terra via Earth Engine (infraestrutura interna); relatórios JSON+PDF; erros 422/404; polo sul (33 s); antimeridiano (47 s); CORS do Skip; idioma pt-BR sem alterar ciência; explicabilidade dos análogos e corte após a média.
* **Skip pela interface (navegador do app, logado):** navegação `/`, `/moon`, `/mars`; Lua 14.64°N 24.07°W (202 → 9 consultas → 200, ~56 s, espectro e análogos, PDF salvo); Marte 0.99°N 328.53°E (longitude enviada −31,47; ausência de CRISM exibida sem números); celular 375×812 (sem rolagem horizontal, painel em folha inferior com rolagem); acessibilidade básica.
* **PocketBase:** ver item D.
* **Cold start:** 3 medições reais da 1ª requisição após repouso: 22,4 s, 21,4 s e 21,4 s (`uptime` 3,8 s). Com o servidor quente: `/health` 0,3 s; aceitação da análise 0,27 s; Lua completa ~10–13 s; Marte ~9 s.

## B. Correções realizadas (backend)

| Arquivo | O quê |
|---|---|
| `app/i18n.py` (novo) | Localização pt-BR das frases (interpretações, `sensitive_to`, limitações, métodos, datum, avisos, critérios, mensagens de cobertura). Nunca toca números, unidades, códigos, instrumentos, URLs nem `data_sources`. |
| `app/api/routes.py` | `?lang=en|pt-BR` em analyze, jobs e reports (JSON); `links.self` mantém o idioma no polling. Resultado canônico (cache, histórico, PDF) continua em inglês. |
| `app/science/spectral.py`, `app/pipelines/lunar.py`, `mars.py`, `earth.py` | `legacy_bd1000/2000`: valores por pixel **sem corte** (negativo = contínuo convexo = sem absorção, com explicação); valor dos análogos = `max(0, média)`, igual à biblioteca. Teste de detecção sobre valores sem corte. Terra mostra o valor negativo com a mesma explicação. |
| `app/science/similarity.py`, `app/schemas/analysis.py` | Campos novos (opcionais): `differences`, `query_uncertainty`, `top5_distance_spread`, `indistinguishable_sites`, `discrimination` + `discrimination_note`; aviso sobre a composição da biblioteca para Lua/Marte. **Fórmula da pontuação inalterada.** |
| `tests/unit/test_i18n.py`, `tests/unit/test_spectral_similarity.py`, `tests/integration/test_api.py` | Cobertura da tradução sobre respostas reais e de dublês; ordem do corte; discriminação; idioma na API. |
| `scripts/validate_production.py` | Testes G (idioma e explicabilidade) em produção. |
| `.github/workflows/tests.yml` | `pyflakes` no CI. |
| `docs/CIENCIA.md`, `docs/INTEGRACAO_FRONTEND.md`, `docs/PROMPT_SKIP_QA.md` | Auditoria, contrato atualizado, prompt de correções do Skip. |

### Efeito da correção do corte com dados reais (mesmos pixels, dois métodos)
| Caso | Produto | `legacy_bd2000` mediana bruta | Antes → depois (entrada dos análogos) | Top-5 |
|---|---|---|---|---|
| Lua 25.8 / −15.2 | M3G20090609T183254 | +0,0108 | 0,01085 → 0,01082 | igual |
| Lua 14.64 / −24.07 | M3G20090610T113334 | +0,0119 | 0,0117 → 0,0117 | igual |
| Marte Jezero | frt0001fb74 | **−0,0147 (97% dos pixels negativos)** | 0,0001 → 0,0000 | igual |
| Marte 5.81 / −31.66 | hrl0000c0cb | +0,0447 | 0,0445 → 0,0445 | igual |

Nas janelas reais (1.681–3.721 pixels, ruído baixo) o ranking não mudou. A correção protege janelas pequenas ou ruidosas e, principalmente, corrige a **apresentação**: em Jezero o indicador antes aparecia como ~0 e agora mostra o valor negativo com a explicação "sem absorção em 2 µm" (coerente com olivina, que não tem banda em 2 µm).

### Pendente no Skip (prompt pronto em `docs/PROMPT_SKIP_QA.md`)
Título da aba (hoje "Visualizador 3D de Marte" em todas as páginas; `<html lang="en">`), selo "CANDIDATO 3D" no histórico, envio de `lang=pt-BR`, exibição de discriminação/atributos dos análogos, mensagem de cold start com contador, `aria-label` do globo e de botões só com ícone, "Pinça para aproximar" no celular, regras do PocketBase, e **rodar typecheck/lint/build**.

## C. Auditoria científica dos análogos
Detalhe completo em `docs/CIENCIA.md#análogos-terrestres`.

* **Fórmula:** distância euclidiana sobre `legacy_bd1000` e `legacy_bd2000`, pesos iguais; `similarity = 1 − d/(0,4·√2)`; top-5. Só ordena; não é probabilidade.
* **Atributos:** profundidades de 3 bandas com definição idêntica nos três corpos — a única compatibilidade física garantida. IBD lunares e parâmetros CRISM ficam fora da pontuação (definições diferentes).
* **Fontes:** Lua M3 L2 (reflectância); Marte CRISM MTRDR (I/F); Terra: 90 sítios EMIT L2A (média de 10 km do composto mediano, extraída pelo backend anterior; data e cenas não arquivadas).
* **Inconsistências encontradas:**
  1. Corte em zero antes da média (Lua/Marte) × depois da média (biblioteca/Terra) — **corrigido**.
  2. Biblioteca dominada por vegetação/umidade em 2 µm: 6 de 7 basaltos de derrame com 1 µm negativo e 2 µm de 0,19–0,50; mediana 0,24 contra ~0–0,05 na Lua/Marte.
  3. Por isso o ranking repete sempre os mesmos sítios áridos: Etendeka, Hamersley, Escondida, Candelaria e Carrapateena aparecem em 3 dos 4 casos reais, na Lua **e** em Marte.
  4. Repetibilidade da biblioteca (~0,006) maior que a incerteza da consulta (~0,001) e do tamanho da separação dos primeiros (0,008–0,053). Autoconsistência: Escondida remedida só é 1ª com o mesmo buffer de 10 km, e por 0,004.
  5. Instrumentos e correções diferentes (EMIT/M3/CRISM), intemperismo espacial e poeira não corrigidos.
* **Melhorias seguras já feitas:** ordem do corte, explicabilidade, selo de discriminação, aviso sobre a biblioteca, tradução.
* **Recomendadas (exigem aprovação):** remedir a biblioteca com máscara de vegetação e metadados arquivados; escolher sítios por geologia (basaltos áridos, anortositos, análogos marcianos clássicos); acrescentar centro de banda e razão de áreas; comparar espectros reamostrados com propagação de incerteza dos dois lados; validar com autoconsistência, controle positivo (mare × terra alta, sítios Apollo) e negativo (ruído → `low`).

## D. Riscos

### Críticos (antes da demonstração)
* **Leitura indevida dos análogos.** A ciência atual não sustenta "esta região parece com Escondida". Mitigado no backend (selo `low`, aviso), mas só visível depois que o Skip exibir `discrimination`. Até lá, apresentar os análogos verbalmente como "ilustrativos".
* **QA do Skip não executado** (typecheck/lint/build). Sem isso, não há como afirmar que o frontend está livre de erros.

### Moderados
* **Isolamento entre usuários não provado com duas contas.** Testado com uma conta + anônimo: anônimo não lê, não altera e não apaga (404); listagem autenticada sem filtro só traz registros próprios e um filtro `owner != eu` retorna 0; lista de usuários só mostra a própria conta; esquema da coleção negado (403); PDF sem token 404. **Pendente:** teste A × B (procedimento abaixo).
* **Dono pode editar o próprio registro**, inclusive `result` (PATCH vazio aceito). Risco de adulterar o próprio histórico e, se a regra não travar `owner`, de inserir registros na conta de outra pessoa que conheça o ID. Regras propostas no prompt §8.
* **Cold start de ~21–22 s** na 1ª requisição e análises de ~50–60 s logo após acordar. Interface já avisa; o prompt pede contador.
* **Leitura do M3 na JPL varia muito** (local: ~220 s por caso; produção: ~10–56 s).

### Baixos
* Erro de CORS do `skip.js` da plataforma Skip no console (fora do app).
* Avisos `THREE.Clock` obsoleto; um "WebGL context lost" isolado durante navegação.
* `<html lang="en">`, canvas sem rótulo, "Scroll para aproximar" no celular.
* PDF continua em inglês.

### Procedimento de teste com duas contas (pendente)
1. Conta A e conta B logadas em navegadores diferentes; cada uma roda uma análise.
2. Em A, anotar o `id` do próprio registro; em B, anotar o `id` do registro de B.
3. Em A, com o token de A: `GET`, `PATCH {}` e `DELETE` em `/api/collections/analyses/records/<id de B>` → todos devem responder **404**.
4. Em A: `GET /api/files/analyses/<id de B>/<pdf de B>?token=<token de arquivo de A>` → **404**.
5. Em A: `POST` criando registro com `owner = <id de B>` → **400/403**.
6. Em A: `PATCH` do próprio registro mudando `owner` ou `result` → **403** (após aplicar as regras do §8).

## E. Próximos passos

**Antes da demonstração**
1. Aplicar `docs/PROMPT_SKIP_QA.md` no Skip e trazer a saída de typecheck/lint/build.
2. Eu testo de novo pela interface: pt-BR, selo de discriminação, título, histórico, celular.
3. Teste de isolamento com duas contas (procedimento acima).
4. No dia: abrir a plataforma ~2 min antes para o servidor acordar.

**Depois**
* Reconstrução da biblioteca terrestre e novos atributos (seção C), com validação.
* PDF em português.
* Plano pago do Render, se a espera de cold start for inaceitável (decisão sua).

**Não alterar agora**
* Fórmula e pesos dos análogos, conjunto de atributos, biblioteca de 90 sítios.
* Critérios de detecção e de confiança.
* Arquitetura Skip → Render → NASA/USGS, identidade visual, telas de Lua e Marte.
* Não criar tela da Terra; não usar dados fictícios como substituto.
