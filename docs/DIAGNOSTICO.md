# Diagnóstico — auditoria do backend antigo e verificação das APIs

Fonte auditada: `geoia-mining-backend-main/` (ZIP extraído, 175 arquivos, 5,3 MB). O projeto original **não foi modificado**.

## 1. Inventário

| Grupo | Arquivos | Conteúdo |
|---|---|---|
| API legada | `backend/co2ia_api.py` (593 l.) | FastAPI com `/v1/earth/analyze`, `/v1/lunar/analyze`, `/v1/report*`, `/health`, + router de mineração |
| Terra | `run_earth_pipeline.py`, `earth_translator_v2.py`, `compare_earth_to_library.py`, `gee_auth.py` | Extração GEE (S2, ASTER, EMIT), tradução para 8 “proxies”, comparação |
| Lua | `run_lunar_pipeline.py`, `compare_lunar_to_earth.py`, `planetary_translator.py` (só a tupla de nomes) | Pipeline lunar e comparação Terra–Lua |
| Relatórios | `report_engine.py` (ReportLab), `build_report.py` (matplotlib; depende de `build_report_core.py`, **ausente**) | PDF |
| Mineração | `backend/mining/**` (≈60 arquivos: cobre, lítio, calibração, taxonomia, gates) | Motor de commodities |
| Dados | `data/earth_proxy_library_100.json`, `data/lunar_earth_similarity_result.json`, `backend/reports/lunar_intelligence_result.json`, `data/mining/**`, `data/calibration*/**` | Bibliotecas e resultados pré-calculados |
| Outros | `tests/` (31), `scripts/` (10), 11 relatórios `.md`, `frontend/co2ia.html`, `render.yaml` | |

## 2. Componentes reutilizados (após revisão)

| Componente legado | Uso no novo projeto | Revisão aplicada |
|---|---|---|
| `gee_auth.py` | `app/providers/earth_engine.py` | Mantida ordem de credenciais e “nunca expor segredo”; credencial interativa só em `development` |
| `extract_gee_indices` (S2/ASTER/EMIT) | `earth_engine.extract` | Mantidos máscaras SCL, índices Ninomiya, nomes de banda EMIT sem zero-padding. **Removido** o fallback “depósito mais próximo da biblioteca”. Adicionado DEM Copernicus GLO-30 |
| Definição de profundidade de banda EMIT (800/1000/1300, 1700/2000/2300 nm, clamp ≥ 0) | `science/spectral.legacy_band_depth` | Mesma fórmula aplicada a M3 e CRISM → única base diretamente comparável entre corpos |
| `masked_cosine` | ideia em `science/similarity.py` | Substituída por distância euclidiana apenas sobre atributos de definição idêntica (ver §5) |
| `report_engine.py` | `services/reports.py` | Paleta/layout; conteúdo 100 % lido do JSON armazenado |
| `earth_proxy_library_100.json` | `app/data/earth_emit_reference_library.json` (90 sítios) | Só os valores EMIT medidos; script reprodutível `scripts/build_earth_reference_library.py` com SHA-256 da origem |

## 3. Componentes descartados

* **Todos os dados lunares locais** (`lunar_earth_similarity_result.json`, `lunar_intelligence_result.json`) — proibidos como fonte; um teste garante que o vetor Imbrium e esses nomes não aparecem no código.
* `run_lunar_pipeline.py`: **devolvia o vetor fixo de Mare Imbrium (M3G20090418T132620) para qualquer coordenada** quando não havia M3 local — exatamente o comportamento proibido.
* Fallback terrestre por “depósito mais próximo”: devolvia medições de outro local para coordenadas arbitrárias.
* `backend/mining/**`, endpoints de cobre/lítio, taxonomias de commodities, calibrações, gates, scores “potential/confidence/sustainability” heurísticos.
* Eixos de 8 proxies (`basaltic_signature`, `plagioclase_proxy`, …): mesmos nomes, físicas diferentes (ASTER TIR na Terra × VSWIR M3 na Lua).
* `build_report.py` (dependência `build_report_core.py` ausente), `frontend/co2ia.html`, scripts de calibração.

## 4. Dependências ausentes no ZIP

* `m3reader` e a classe `PlanetaryTranslator` (o módulo só tinha a tupla de nomes) — o caminho “M3 real” do pipeline antigo nunca podia executar.
* `build_report_core.py`.
* Nenhum leitor de PDS/ODE/Trek existia. Tudo foi escrito do zero (`app/providers/*`).

## 5. Avaliação científica dos algoritmos antigos

| Algoritmo | Avaliação |
|---|---|
| Pipeline lunar | **Inválido**: resultado independente da coordenada. |
| `earth_translator_v2` (8 proxies) | Normalizações ancoradas em 20 depósitos; `plagioclase_proxy` = índice de sílica ASTER (não é plagioclásio); `spectral_complexity` sem análogo. Não reutilizado para comparação entre corpos. |
| Profundidade de banda EMIT | Fisicamente justificável, mas continuum = média simples dos ombros (não interpolação linear). Mantida *apenas* por compatibilidade com a biblioteca, e documentada como tal. |
| `masked_cosine` | Cosseno sobre 2–3 dimensões não negativas satura perto de 1 para quase qualquer par; misturava eixos de físicas diferentes. Substituído. |
| Scores “potential/confidence” | Heurísticos sem critério documentado. Removidos. A nova `confidence` é baseada em regras explícitas (docs/CIENCIA.md). |

## 6. Verificação das APIs (executada em 2026-11-05, chamadas reais)

| Serviço | Endpoint verificado | Formato / convenção | Resultado |
|---|---|---|---|
| ODE REST | `oderest.rsl.wustl.edu/live2/?query=product&results=opmf&output=JSON&ihid=CH1-ORB&iid=M3&pt=REFIMG&loc=f&…` | JSON; lat planetocêntrica; lon leste 0–360; `"Products": "No Products Found"` (string) quando vazio | M3 em Imbrium: 3 footprints, 2 contendo o ponto; CRISM MTRDR em Jezero: 4 |
| ODE GDS | `oderest.rsl.wustl.edu/livegds/?query=lolardr` / `molapedr` | JSON + URLs de CSV (só tiros válidos, flag 0); LOLA: raio − 1737,4 km; MOLA: raio − areoide | 10 761 tiros LOLA (5 km, Imbrium); 393 MOLA (Jezero); 86 937 no polo sul lunar |
| PDS imaging / geosciences | `planetarydata.jpl.nasa.gov`, `pds-geosciences.wustl.edu` | ENVI/PDS3 brutos; **HTTP Range = 206** | Leitura parcial de cubos de 2,5 GB (M3) e 650 MB (CRISM) sem download completo |
| Trek WMTS | `trek.nasa.gov/{moon,mars}/TrekServices/ws/index/eq/searchItems` + `…/WMTSCapabilities.xml` | Solr JSON (bbox lon −180..180) + OGC WMTS 1.0 RESTful | 1 096 camadas lunares, 146 marcianas |
| PDS Registry | `pds.nasa.gov/api/search/1/products` → 307 → `pds.mcp.nasa.gov` | JSON; `keywords=` ignorado; filtro espacial `cart:Bounding_Coordinates` funciona (PDS4) | LOLA/Diviner indexados; **CRISM: 0 produtos** (PDS3 não indexado) |
| USGS Astrogeology | `stac.astrogeology.usgs.gov/api` ; WMS `planetarymaps.usgs.gov` | STAC 1.0; WMS para visualização | 18 coleções (DTMs Kaguya TC, CTX, HiRISE); 5 DTMs CTX em Jezero |
| Earth Engine | — | — | **Não testado**: não há credencial neste ambiente. Sem credencial o endpoint responde `not_configured`. |

## 7. Arquitetura final

```
app/
  main.py              FastAPI, CORS restrito, logs JSON, lifespan
  config.py            todas as variáveis GEOIA_* e limites
  api/routes.py        /v1/{earth,lunar,mars}/analyze, /v1/jobs/{id}, /v1/reports/{id}, /v1/planetary/datasets, /health
  schemas/analysis.py  contrato único (estados available/unavailable/partial/processing/failed + reason)
  providers/           http (SSRF, retries, limites, Range), ode (REST+GDS), trek, pds, usgs, envi, m3, crism, earth_engine
  pipelines/           common (imagem, topografia, descoberta, confiança), lunar, mars, earth
  science/             coordinates, topography, spectral, similarity
  services/            jobs (assíncronos, concorrência limitada), store (SQLite em disco persistente), reports (PDF), cache, datasets
  data/                earth_emit_reference_library.json
```
Simplificação em relação à estrutura sugerida: um único `api/routes.py` (as rotas são finas) e `provenance` incorporado ao `SourceRecord` do schema.

## 8. Plano incremental (status)

| Dia | Entrega | Status |
|---|---|---|
| 1 | Auditoria, projeto novo, conectores ODE/GDS/Trek/PDS/USGS | **Feito** |
| 2 | Lua: LOLA + M3 por coordenada, primeiro resultado real | **Feito** (Imbrium, 25,8N/15,2W, polos, antimeridiano) |
| 3 | Marte: MOLA + CRISM MTRDR | **Feito** (Jezero, 0/0, polo sul sem cobertura) |
| 4 | Motor compartilhado, análogos, relatórios, contratos | **Feito em versão MVP** |
| 5 | Estabilização, deploy Render, demo | Pendente: build Docker e deploy não executados aqui (Docker indisponível nesta máquina); integração com o frontend real |
