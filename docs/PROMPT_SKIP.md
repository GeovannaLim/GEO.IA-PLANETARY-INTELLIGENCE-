# Prompt para o Skip — integração com o backend científico GEØ.IA

Cole o texto abaixo no assistente do Skip.

---

Conecte a interface existente da GEØ.IA ao backend científico em produção. **Não recrie a interface, não troque o visual 3D e não remova telas existentes.** Apenas ligue as ações atuais (escolher Terra/Lua/Marte, clicar numa coordenada, definir o raio, iniciar análise, ver resultados e relatório) à API abaixo.

## API
- URL base: `https://geoia-planetary-backend.onrender.com` (guarde como uma constante ou variável de configuração `GEOIA_API_BASE`, num único lugar).
- Todas as chamadas são HTTPS feitas pelo navegador. O CORS já libera a origem `https://geoai-interplanetary.goskip.app`.
- Não chame NASA, USGS ou Earth Engine diretamente do frontend. Não invente, simule nem preencha valores científicos: se um campo vier `null`, mostre "não medido".

## Endpoints
| Ação | Método e caminho |
|---|---|
| Analisar Lua | `POST /v1/lunar/analyze` |
| Analisar Marte | `POST /v1/mars/analyze` |
| Analisar Terra | `POST /v1/earth/analyze` |
| Consultar andamento/resultado | `GET {links.self}` (ex.: `/v1/jobs/{analysis_id}`) |
| Relatório PDF | `GET /v1/reports/{report_id}?format=pdf` (abrir em nova aba) |
| Acordar o servidor | `GET /health` (chamar ao abrir a tela de análise) |

Corpo do POST (JSON, `Content-Type: application/json`):
```json
{ "latitude": 25.8, "longitude": -15.2, "radius_km": 10 }
```
- `latitude` −90 a 90; `longitude` −180 a 180 (leste positivo).
- `radius_km` maior que 0; máximo Lua 25, Marte 50, Terra 25. Valide no formulário antes de enviar.
- Não envie outros campos (a API responde 422).

## Fluxo assíncrono (obrigatório)
1. `POST .../analyze?wait_s=20`.
2. Se a resposta for **202** (ou `status: "processing"`), consultar `GET` em `links.self` a cada 3 segundos.
3. Parar quando vier **200** com `status` `"completed"` ou `"failed"`. Tempo máximo: 5 minutos.
4. A primeira análise depois de um período sem uso pode levar ~1 minuto a mais (o servidor está acordando). Mostre "Preparando o servidor científico…" nesse caso, não um erro.
5. Em erro de rede ou HTTP 5xx, tente de novo até 3 vezes com espera de 2, 4 e 8 segundos.

Cliente pronto (TypeScript, só `fetch`):
```ts
const API = "https://geoia-planetary-backend.onrender.com";
type Body = "lunar" | "mars" | "earth";

export async function runAnalysis(body: Body, latitude: number, longitude: number, radius_km: number,
  onProgress?: (steps: string[]) => void, timeoutMs = 300_000) {
  const t0 = Date.now();
  let res = await fetchRetry(`${API}/v1/${body}/analyze?wait_s=20`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ latitude, longitude, radius_km }),
  });
  if (res.status === 422) throw new Error("Parâmetros inválidos: " + JSON.stringify((await res.json()).detail));
  let doc = await res.json();
  while (doc.status === "processing") {
    if (Date.now() - t0 > timeoutMs) throw new Error("A análise excedeu o tempo limite.");
    onProgress?.(doc.progress ?? []);
    await new Promise(r => setTimeout(r, 3000));
    doc = await (await fetchRetry(`${API}${doc.links.self}`)).json();
  }
  return doc;
}

export const reportPdfUrl = (reportId: string) => `${API}/v1/reports/${reportId}?format=pdf`;

async function fetchRetry(url: string, init?: RequestInit, tries = 3): Promise<Response> {
  for (let i = 0; ; i++) {
    try { const r = await fetch(url, init); if (r.status < 500 || i >= tries - 1) return r; }
    catch (e) { if (i >= tries - 1) throw e; }
    await new Promise(r => setTimeout(r, 2000 * 2 ** i));
  }
}
```
Use `"lunar"` para a Lua, `"mars"` para Marte e `"earth"` para a Terra.

## Carregamento
Enquanto `status === "processing"`, mostre os passos de `progress` (lista que cresce):
- `imagery` → "Mosaicos de superfície"
- `topography` → "Topografia (altímetro laser)"
- `m3_discovery` / `crism_discovery` → "Buscando observações espectrais"
- `m3_extraction` / `crism_extraction` → "Lendo espectros"
- `pds_discovery`, `usgs_discovery` → "Consultando catálogos NASA/USGS"
- `earth_engine` → "Processando imagens de satélite"

## Exibição do resultado
Cada seção (`topography`, `mineralogy`, `earth_analogs`, `imagery`) tem `status` e `reason`. Mostre cada painel conforme o próprio status:

| status / reason | Mensagem |
|---|---|
| `available` | mostrar os valores |
| `partial` | mostrar valores com selo "dados esparsos" |
| `unavailable` + `no_coverage` | "Nenhuma observação deste instrumento cobre este ponto." |
| `unavailable` + `no_compatible_observations` | "Há observações, mas nenhuma utilizável neste ponto." |
| `unavailable` + `not_configured` | "Fonte não configurada no servidor." |
| `unavailable` + `not_attempted` | "Depende de dados espectrais indisponíveis." |
| `failed` + `provider_error` | "Serviço da NASA/USGS indisponível agora. Tente novamente mais tarde." |

Campos:
- **Topografia** (`topography`): `elevation_m.mean` e `elevation_m.median` (m), `relief_m`, `regional_slope_degrees`, `local_slope_degrees.median`, `roughness_m`, `n_points` (número de medições), `datum` e `method` (fonte).
- **Mineralogia** (`mineralogy`): `instrument`, `product_used`, `valid_pixels`; lista `indicators` com `name`, `value.median`, `sensitive_to`, `interpretation`; frase `spectral_character`. Na Lua, `mean_spectrum.wavelength_nm` × `mean_spectrum.reflectance` pode virar um gráfico de linha. Mostre sempre o aviso: "Indicadores de triagem espectral — não constituem identificação mineral."
- **Análogos terrestres** (`earth_analogs.matches`): `name`, `country`, `setting`, `similarity` (0–1). Rotule como "Ranking de similaridade espectral" e mostre o texto de `earth_analogs.disclaimer`. Nunca chame de probabilidade nem de indício de jazida.
- **Confiança** (`confidence.level`): `high`/`moderate`/`low`/`not_assessed`, com a lista `confidence.limitations` num item expansível.
- **Fontes** (`data_sources`): painel "Fontes científicas" com `provider`, `instrument`, `product_type`, `product_id`, `observation_start`, `observation_end`, `url`.
- **Coordenadas usadas** (`coordinates`): `latitude`, `longitude`, `radius_km`.
- **Mosaicos** (`imagery.layers`): se a cena 3D aceitar camadas WMTS, use `tile_url_template` trocando `{Style}` por `default`, `{TileMatrixSet}` por `tile_matrix_set`, e `{TileMatrix}`/`{TileRow}`/`{TileCol}` pelos índices do tile. Se não aceitar, ignore.
- **Relatório**: botão "Abrir relatório PDF" usando `reportPdfUrl(doc.report_id)`, habilitado só quando `status === "completed"`.

## Erros
- 422 → mensagem de validação no formulário.
- `status: "failed"` → mostrar `problems[problems.length-1].message` e um botão "Tentar novamente".
- Tempo esgotado → "A análise demorou mais que o esperado. Tente novamente."
- 404 em consulta → reiniciar a análise.

## Teste de aceite
1. Lua, latitude 25.8, longitude −15.2, raio 10 → concluir com topografia e mineralogia disponíveis.
2. Marte, latitude 18.44, longitude 77.45, raio 5 → concluir com dados CRISM.
3. Marte, latitude −85, longitude 150, raio 10 → mineralogia "Nenhuma observação… cobre este ponto", sem números inventados.
4. Abrir o PDF de uma análise concluída.
