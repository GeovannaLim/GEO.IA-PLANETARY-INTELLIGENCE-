# Integração com a interface 3D

## Fluxo recomendado
1. Usuário escolhe corpo + clica coordenada + define raio.
2. `POST /v1/{earth|lunar|mars}/analyze` com o corpo JSON abaixo.
   * Resposta **202** com `status: "processing"` e `links.self` → fazer polling (2–3 s) em `GET /v1/jobs/{analysis_id}` até **200**.
   * Opcional: `?wait_s=25` faz o POST esperar até 25 s e devolver 200 direto quando der tempo.
   * Mesma coordenada/raio em 24 h → resposta imediata com `cache.hit = true` (use `?use_cache=false` para refazer).
3. Durante o processamento, `progress` lista os passos concluídos (`imagery`, `topography`, `m3_discovery`, `m3_extraction`, `crism_*`, `pds_discovery`, `usgs_discovery`) — use para a barra de carregamento.
4. Relatório: `GET /v1/reports/{report_id}` (JSON) ou `?format=pdf`.

```bash
curl -X POST "https://<host>/v1/lunar/analyze?wait_s=25" -H "Content-Type: application/json" -d '{"latitude": 25.8, "longitude": -15.2, "radius_km": 10}'
```

## Requisição
```json
{"latitude": 25.8, "longitude": -15.2, "radius_km": 10}
```
`longitude_convention` opcional: `"east_180"` (padrão) ou `"east_360"`. Erros de validação → **422** com mensagem.

## Resposta (campos que a interface usa)
| Campo | Uso na UI |
|---|---|
| `status` | `processing` / `completed` / `failed` |
| `imagery.layers[]` | `tile_url_template` (WMTS REST: substituir `{Style}`→`default`, `{TileMatrixSet}`, `{TileMatrix}`, `{TileRow}`, `{TileCol}`), `role` = `basemap` / `shaded_relief` / `regional_product` |
| `topography.elevation_m`, `relief_m`, `regional_slope_degrees`, `local_slope_degrees`, `roughness_m` | painel “Topografia”; `elevation_m_mean` e `slope_degrees` são atalhos |
| `mineralogy.status` + `reason` | mostrar “indisponível: sem cobertura” × “falha do provedor” × “sem observação compatível” |
| `mineralogy.indicators[]` | `name`, `value.median`, `sensitive_to`, `interpretation` |
| `mineralogy.spectral_character` | frase-resumo (sempre com ressalva) |
| `mineralogy.mean_spectrum` | gráfico (Lua) |
| `earth_analogs.matches[]` | `name`, `country`, `setting`, `similarity` (ranking, não probabilidade) + `disclaimer` |
| `confidence.level` / `criteria` / `limitations` | selo de confiança |
| `data_sources[]` | painel “Fontes”: provedor, instrumento, produto, datas de observação, URL |
| `problems[]` | avisos por seção |

Cada seção traz `source_ids` que apontam para `data_sources[].source_id`.

## Exemplos reais (gerados contra os serviços da NASA)
* `examples/response_lunar_accepted_202.json` — resposta imediata do POST.
* `examples/response_lunar_25.8N_15.2W.json` — resultado completo (LOLA 35 896 tiros, M3 1 681 pixels).
* `examples/response_mars_jezero.json` — Marte, cratera Jezero (MOLA + CRISM).
* `examples/report_lunar_25.8N_15.2W.pdf` — relatório PDF.

## CORS
Defina `GEOIA_CORS_ORIGINS` com as origens exatas do frontend (separadas por vírgula). Não há curinga.
