# GEØ.IA Planetary Intelligence — backend científico

API FastAPI que analisa regiões da **Terra**, da **Lua** e de **Marte** a partir de coordenadas, usando somente fontes científicas rastreáveis (NASA PDS/ODE, NASA Trek, USGS Astrogeology, Google Earth Engine). Cada valor devolvido aponta para a fonte, o produto e o processamento de onde veio. Nenhum dado lunar local, vetor fixo ou resultado pré-calculado é usado como medição.

## Arquitetura

```
Vercel (site institucional) ──► Skip (plataforma 3D) ──HTTPS──► Render (esta API) ──► NASA / USGS / Earth Engine
```

```
app/
  main.py              FastAPI, CORS por variável de ambiente, logs JSON, ciclo de vida
  config.py            configuração GEOIA_* (limites, timeouts, concorrência)
  api/routes.py        endpoints
  schemas/analysis.py  contrato único Terra/Lua/Marte (estados por seção + motivo)
  providers/           clientes HTTP: ODE REST/GDS, Trek, PDS, USGS STAC, M3, CRISM, Earth Engine
  pipelines/           orquestração por corpo (common, lunar, mars, earth)
  science/             coordenadas, topografia, espectroscopia, similaridade
  services/            jobs assíncronos, SQLite, relatórios PDF, cache, catálogo de fontes
  data/                biblioteca terrestre EMIT (90 sítios, com proveniência)
```

## Tecnologias
Python 3.12 · FastAPI · Pydantic v2 · HTTPX · NumPy · ReportLab · SQLite · Docker · pytest/respx · earthengine-api (opcional).

## Fontes científicas

| Corpo | Topografia (numérica) | Espectroscopia | Imagem / descoberta |
|---|---|---|---|
| Lua | LRO LOLA RDR (ODE GDS) | Chandrayaan-1 M3 L2 (leitura parcial por HTTP Range) | Trek WMTS, PDS Registry (LOLA, Diviner), USGS STAC (DTMs Kaguya) |
| Marte | MGS MOLA PEDR (ODE GDS) | MRO CRISM MTRDR (parâmetros-sumário + I/F) | Trek WMTS, USGS STAC (DTMs CTX/HiRISE) |
| Terra | Copernicus DEM GLO-30 (Earth Engine) | EMIT L2A (Earth Engine) | — |

Detalhes, definições e referências: [docs/CIENCIA.md](docs/CIENCIA.md).

## Endpoints

| Método | Caminho | Descrição |
|---|---|---|
| POST | `/v1/lunar/analyze` · `/v1/mars/analyze` · `/v1/earth/analyze` | `{"latitude", "longitude", "radius_km"}` → 202 + polling, ou `?wait_s=` (0–60) |
| GET | `/v1/jobs/{analysis_id}` | estado e resultado |
| GET | `/v1/reports/{report_id}` | relatório JSON; `?format=pdf` para PDF |
| GET | `/v1/planetary/datasets` | fontes, convenções e o que cada uma não responde |
| GET | `/health` | saúde (banco, jobs, Earth Engine sem segredos) |

OpenAPI em `/docs`. Contrato para o Skip, com exemplos TypeScript: [docs/INTEGRACAO_FRONTEND.md](docs/INTEGRACAO_FRONTEND.md).

## Instalação local
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## Configuração de ambiente
Todas as variáveis estão em [.env.example](.env.example). Principais:

| Variável | Função |
|---|---|
| `GEOIA_CORS_ORIGINS` | origens exatas permitidas (separadas por vírgula; sem curinga) |
| `GEOIA_DB_PATH` | arquivo SQLite de jobs e relatórios |
| `GEOIA_MAX_CONCURRENT_JOBS`, `GEOIA_JOB_TIMEOUT_S` | limites de processamento |
| `GEOIA_MAX_RADIUS_KM_{MOON,MARS,EARTH}` | limites operacionais |
| `GEE_PROJECT`, `GEE_SERVICE_ACCOUNT_JSON` ou `GEE_SERVICE_ACCOUNT_KEY_FILE` | Earth Engine (só o endpoint da Terra) |

Segredos ficam apenas no painel do Render ou em `.env` local; nunca são logados nem devolvidos pela API.

## Testes
```bash
.venv/bin/python -m pytest -q                                   # offline: unitários, integração com mocks, API
GEOIA_LIVE_TESTS=1 .venv/bin/python -m pytest -m live -q        # chamadas reais à NASA/USGS
PYTHONPATH=. .venv/bin/python scripts/validate_production.py https://<servico>.onrender.com   # testes A–F contra um deploy
```
Os mocks (`tests/fakes.py`) existem só nos testes; um teste garante que o pacote `app` não os importa nem contém o vetor lunar antigo.

## Deploy
Docker + blueprint Render (`render.yaml`, plano **free** por padrão). Passo a passo, opções de persistência e validação: [docs/DEPLOY.md](docs/DEPLOY.md). O GitHub Actions (`.github/workflows/tests.yml`) roda os testes e faz build + health check da imagem.

## Robustez operacional
Timeouts e retries com backoff exponencial; allow-list de hosts (inclusive para URLs devolvidas pelos provedores) contra SSRF; limite de bytes por download; concorrência por host e por job; cache de metadados (12 h) e de resultados (24 h, sinalizado em `cache.hit`); cada etapa isolada (falha de um provedor não derruba as outras seções); jobs interrompidos por reinício são retomados automaticamente enquanto o banco persistir.

## Limitações científicas
* Indicadores espectrais são **triagem** (detecção estatística de absorção), não identificação nem abundância mineral.
* M3: correção térmica empírica afeta a região de 2 µm; 140–280 m/pixel.
* CRISM: só onde há observações direcionadas (~10 km); parâmetros-sumário sensíveis a ruído e CO2 residual.
* Análogos terrestres: **ranking** por 2 profundidades de banda com definição idêntica — discriminação fraca; biblioteca dominada por sistemas hidrotermais. Não é probabilidade de depósito.
* Altimetria laser deixa lacunas entre trilhas; a cobertura é reportada.
* Terra exige credencial Earth Engine; sem ela responde `not_configured`.

Auditoria do backend anterior e verificação das APIs: [docs/DIAGNOSTICO.md](docs/DIAGNOSTICO.md).
