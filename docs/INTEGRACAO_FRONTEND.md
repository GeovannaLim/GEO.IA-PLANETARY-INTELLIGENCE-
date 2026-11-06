# Integração Skip → Render

Fluxo: **Vercel** (site institucional, não chama a API) → **Skip** (plataforma 3D) → **Render** (esta API) → NASA/USGS.
Todas as consultas científicas ficam no backend; o Skip só chama os endpoints abaixo por HTTPS.

## 1. URL base
```
https://geoia-planetary-backend.onrender.com
```
Em produção desde 2026-11-05 (Render, plano Free). Configure no Skip como variável (ex.: `GEOIA_API_BASE`). Documentação interativa: https://geoia-planetary-backend.onrender.com/docs

## 2. Endpoints
| Método | Caminho | Uso |
|---|---|---|
| POST | `/v1/lunar/analyze` | iniciar análise da Lua |
| POST | `/v1/mars/analyze` | iniciar análise de Marte |
| POST | `/v1/earth/analyze` | iniciar análise da Terra (requer Earth Engine configurado) |
| GET | `/v1/jobs/{analysis_id}` | estado / resultado |
| GET | `/v1/reports/{report_id}` | relatório JSON (`?format=pdf` para PDF) |
| GET | `/v1/planetary/datasets` | fontes e convenções (opcional, painel “sobre os dados”) |
| GET | `/health` | disponibilidade (útil para “acordar” a instância free) |

Query opcionais do POST: `wait_s` (0–60, espera antes de responder), `use_cache` (padrão `true`).

## 3. Payload
```json
{ "latitude": 25.8, "longitude": -15.2, "radius_km": 10 }
```
* `latitude` planetocêntrica −90..90; `longitude` leste-positiva −180..180 (ou 0..360 com `"longitude_convention": "east_360"`).
* `radius_km` > 0; limites: Lua 25, Marte 50, Terra 25.
* Campos extras são rejeitados (422).

## 4. Fluxo assíncrono
```
POST /v1/{corpo}/analyze ──► 202 {status:"processing", analysis_id, links.self}
       │                     (ou 200 direto: resultado em cache ou concluído dentro de wait_s)
       ▼
GET links.self a cada 3 s ──► 202 enquanto processing (campo progress cresce)
       ▼
                         ──► 200 {status:"completed"|"failed", ...seções..., report_id}
```
Tempos medidos com serviços reais: Lua 12–35 s, Marte 8–16 s; polo sul lunar ~30 s. No plano free a primeira chamada após inatividade pode levar ~1 min extra (instância acordando). Use timeout total de 5 min no cliente.

## 5. Estados de carregamento (para a UI)
| Condição | Exibir |
|---|---|
| `status = processing` | spinner + passos de `progress[]`: `imagery` (mosaicos), `topography` (LOLA/MOLA), `m3_discovery`/`crism_discovery` (busca de observações), `m3_extraction`/`crism_extraction` (leitura espectral), `pds_discovery`, `usgs_discovery` |
| `status = completed` | painéis por seção, cada um segundo seu próprio `status` |
| `status = failed` | mensagem de `problems[-1].message` + botão “tentar de novo” |

## 6. Estado por seção (dados ausentes ≠ erro)
Cada seção (`imagery`, `topography`, `mineralogy`, `earth_analogs`) tem `status` e `reason`:

| `status` / `reason` | Mensagem sugerida |
|---|---|
| `available` | mostrar valores |
| `partial` / `insufficient_data` | mostrar valores com selo “dados esparsos” |
| `unavailable` / `no_coverage` | “Nenhuma observação deste instrumento cobre o ponto.” |
| `unavailable` / `no_compatible_observations` | “Há observações, mas nenhuma utilizável para este ponto.” |
| `unavailable` / `not_configured` | “Fonte não configurada no servidor.” (Terra sem Earth Engine) |
| `unavailable` / `not_attempted` | “Depende de outra seção indisponível.” (ex.: análogos sem espectro) |
| `failed` / `provider_error` | “Serviço da NASA/USGS indisponível agora; tente mais tarde.” |

Nunca preencher valores ausentes na UI: `null` significa “não medido”.

## 7. Campos de resposta usados pela UI
| Campo | Uso |
|---|---|
| `coordinates` | coordenadas efetivamente usadas (+ `longitude_east_360`, `reference_frame`) |
| `imagery.layers[]` | `tile_url_template` WMTS (substituir `{Style}`→`default`, `{TileMatrixSet}`, `{TileMatrix}`, `{TileRow}`, `{TileCol}`); `role`: `basemap`/`shaded_relief`/`regional_product` |
| `topography` | `elevation_m{mean,median,min,max,p05,p95}`, `relief_m`, `regional_slope_degrees`, `local_slope_degrees.median`, `roughness_m`, `n_points`, `datum` |
| `mineralogy` | `instrument`, `product_used`, `valid_pixels`, `indicators[]` (`name`, `value.median`, `sensitive_to`, `interpretation`), `spectral_character`, `mean_spectrum` (Lua) |
| `earth_analogs` | `matches[]` (`name`, `country`, `setting`, `similarity`), `disclaimer` — **ranking, não probabilidade** |
| `confidence` | `level`, `criteria[]`, `limitations[]` |
| `data_sources[]` | painel de proveniência (provedor, instrumento, produto, datas, URL) |
| `problems[]` | avisos |
| `report_id`, `links` | relatório |

Schema completo (OpenAPI): `GET /openapi.json`, UI em `/docs`.

## 8. Erros HTTP
| Código | Quando | Ação no Skip |
|---|---|---|
| 200 | concluído / cache | renderizar |
| 202 | em processamento | continuar polling |
| 404 | `analysis_id`/`report_id` inexistente | reiniciar análise |
| 409 | relatório pedido antes de concluir | aguardar |
| 422 | payload inválido (`detail` explica) | mostrar mensagem de validação |
| 5xx / rede | instância acordando ou indisponível | retry com backoff (ex.: 3 tentativas, 2/4/8 s) |

## 9. CORS
O backend só aceita as origens em `GEOIA_CORS_ORIGINS` (sem curinga). Origem da plataforma Skip, confirmada em 2026-11-05 (HTTPS 200; HTTP redireciona para HTTPS):

```
GEOIA_CORS_ORIGINS=https://geoai-interplanetary.goskip.app
```

Se o Skip usar outro domínio para pré-visualização, acrescentá-lo separado por vírgula. A URL da Vercel não é adicionada porque o site institucional não chama a API.
Se o Skip fizer as chamadas a partir do servidor (não do navegador), CORS não se aplica.

## 10. Exemplo TypeScript (fetch, sem dependências)
```ts
const API = "https://geoia-planetary-backend.onrender.com"; // ou a variável de ambiente do Skip
type Body = "lunar" | "mars" | "earth";

export async function runAnalysis(
  body: Body, latitude: number, longitude: number, radius_km: number,
  onProgress?: (steps: string[]) => void, timeoutMs = 300_000,
) {
  const t0 = Date.now();
  let res = await fetchRetry(`${API}/v1/${body}/analyze?wait_s=20`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latitude, longitude, radius_km }),
  });
  if (res.status === 422) throw new Error((await res.json()).detail?.toString() ?? "invalid request");
  let doc = await res.json();
  while (doc.status === "processing") {
    if (Date.now() - t0 > timeoutMs) throw new Error("analysis timed out");
    onProgress?.(doc.progress ?? []);
    await new Promise(r => setTimeout(r, 3000));
    res = await fetchRetry(`${API}${doc.links.self}`);
    doc = await res.json();
  }
  return doc; // status "completed" | "failed"; check each section's status
}

export const reportPdfUrl = (reportId: string) => `${API}/v1/reports/${reportId}?format=pdf`;

async function fetchRetry(url: string, init?: RequestInit, tries = 3): Promise<Response> {
  for (let i = 0; ; i++) {
    try {
      const r = await fetch(url, init);
      if (r.status < 500 || i >= tries - 1) return r;
    } catch (e) { if (i >= tries - 1) throw e; }
    await new Promise(r => setTimeout(r, 2000 * 2 ** i));
  }
}

// Uso:
// const d = await runAnalysis("lunar", 25.8, -15.2, 10, s => console.log(s.at(-1)));
// if (d.mineralogy.status === "available") showIndicators(d.mineralogy.indicators);
// else showNotice(d.mineralogy.reason);   // no_coverage, provider_error, ...
// window.open(reportPdfUrl(d.report_id));
```

## 11. Exemplos reais
* `examples/response_lunar_accepted_202.json`, `examples/response_lunar_25.8N_15.2W.json`, `examples/response_mars_jezero.json`, `examples/report_lunar_25.8N_15.2W.pdf`
* `examples/local_validation_run.json` — 27 verificações reais (testes A–F) contra servidor local em modo produção.
* `examples/production_validation_render.json` — as mesmas 27 verificações contra o Render em produção (27/27, 2026-11-05).

## 12. Teste de integração (2026-11-05, Skip publicado, usuário logado)
1. `GEOIA_CORS_ORIGINS=https://geoai-interplanetary.goskip.app` configurado no Render; preflight 200, origem desconhecida recusada.
2. **Marte — integrado e verificado pela interface:**
   * 5.81°N 328.34°E (exibido 0–360) enviado como −31.66 → `POST /v1/mars/analyze?wait_s=20` 200; MOLA 615 pontos, CRISM `hrl0000c0cb_07_if182j_mtr3` (2.040 pixels), análogos com aviso, confiança, fontes, coordenadas usadas.
   * Mesmo ponto, raio 8 → nova análise, topografia com selo “dados esparsos”.
   * 40.25°S 347.49°E → mineralogia “Nenhuma observação deste instrumento cobre este ponto.”, análogos “Depende de dados espectrais indisponíveis.”, sem números.
   * `/health` chamado ao abrir; PDF da análise exibida: 200 `application/pdf` (o botão abre `geoia-planetary-backend.onrender.com` em nova aba).
3. **Lua — integrada e verificada pela interface** (bundle `index-qmj_GhG5.js`): 14.64°N 24.07°W, raio 10 → `POST /v1/lunar/analyze?wait_s=20` **202**, polling de `/v1/jobs/{id}` a cada ~3,3 s (9 × 202, depois 200; ~63 s com a instância recém-acordada), passos de `progress` em português. Resultado: LOLA 28.710 pontos; M3 `M3G20090610T113334_V01_RFL` (1.681 pixels), IBD1000/IBD2000 positivos, gráfico do espectro médio (541–2577 nm), análogos com aviso, 5 camadas WMTS, confiança “Alta”, fontes; PDF 200 (9,9 KB). Painel demonstrativo antigo removido.
4. Ajustes de UI aplicados: selos “ANÁLISE DEMONSTRATIVA”/“DEMO” e “Demo score” removidos; campos nulos das fontes ocultados.
5. Terra não tem tela no Skip (fora do escopo deste teste).
6. **Persistência no PocketBase do Skip** (bundle `index-niSobUxa.js`, coleção `analyses`):
   * Funciona: análise concluída gera registro com `result` completo; “Minhas análises” lista o item e o abre **sem nenhuma requisição ao backend** (“análise salva · nada é reprocessado”).
   * **Falha:** o PDF não é guardado. O Skip baixa o PDF por `GET {pocketbase}/api/geoai-pdf/{report_id}`, rota inexistente (404 “File not found.”); `pdf_file` fica vazio e o botão mostra “não há cópia guardada”, embora o backend sirva o mesmo PDF (200). Correção pedida: baixar direto de `{API}/v1/reports/{id}?format=pdf` sem `credentials: "include"` (o CORS do backend não usa credenciais).
   * Ajustes menores: longitude salva na convenção de exibição (349.42) em vez da usada (−10.58); item de Marte abre sobre o globo da Lua; sem opção de apagar.
7. **Persistência corrigida** (bundle `index-2u5xtw-v.js`): análise nova (0.99°N 328.53°E) → `GET {API}/v1/reports/{id}?format=pdf` 200 → registro com `pdf_file` (5,9 KB, `%PDF-`) e longitude usada (−31.47). Histórico mostra “PDF guardado”, tem botão de apagar, abre o item no globo certo (`/mars` a partir de `/moon`) sem requisição ao backend, e “Abrir relatório PDF” abre a cópia do PocketBase. Visitante anônimo não lista registros.
   * ~~`pdf_file` sem proteção~~ — **corrigido** (bundle `index-BMJCBHYs.js`): sem token o arquivo responde 404 (testado sem cache no navegador e por `curl` externo); o botão chama `/api/files/token` (200) e abre a URL com token, que devolve `application/pdf` (5.977 bytes).
   * Registro antigo (antes da correção) continua sem PDF.
