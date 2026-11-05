# GEØ.IA Planetary Intelligence — backend

Backend FastAPI independente para análise por coordenadas da **Terra**, **Lua** e **Marte**, usando somente fontes científicas rastreáveis (NASA PDS / ODE, NASA Trek, USGS Astrogeology, Google Earth Engine). Nenhum dado lunar local, vetor fixo ou resultado pré-calculado é usado como medição.

| Corpo | Topografia (numérica) | Espectroscopia | Imagem |
|---|---|---|---|
| Lua | LRO LOLA RDR (ODE GDS) | Chandrayaan-1 M3 L2 (leitura parcial por HTTP Range) | Trek WMTS |
| Marte | MGS MOLA PEDR (ODE GDS) | MRO CRISM MTRDR (parâmetros-sumário + I/F) | Trek WMTS |
| Terra | Copernicus DEM GLO-30 (Earth Engine) | EMIT L2A (Earth Engine) | — |

## Endpoints
* `POST /v1/earth/analyze`, `POST /v1/lunar/analyze`, `POST /v1/mars/analyze` — `{"latitude", "longitude", "radius_km"}`; 202 + polling, ou `?wait_s=` (0–60).
* `GET /v1/jobs/{analysis_id}` — estado/resultado.
* `GET /v1/reports/{report_id}` — JSON; `?format=pdf` — PDF.
* `GET /v1/planetary/datasets` — fontes, convenções e o que cada uma **não** pode responder.
* `GET /health`.

Documentação interativa: `/docs`. Contrato e exemplos: [docs/INTEGRACAO_FRONTEND.md](docs/INTEGRACAO_FRONTEND.md). Métodos, critérios e limitações: [docs/CIENCIA.md](docs/CIENCIA.md). Auditoria do backend antigo e verificação das APIs: [docs/DIAGNOSTICO.md](docs/DIAGNOSTICO.md).

## Rodar localmente
Requer Python 3.12.
```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

## Testes
```bash
.venv/bin/python -m pytest -q                       # offline: unitários, integração (mocks), API
GEOIA_LIVE_TESTS=1 .venv/bin/python -m pytest -m live -q   # chamadas reais à NASA/USGS
PYTHONPATH=. .venv/bin/python scripts/live_run.py moon 25.8 -15.2 10   # uma análise real, impressa
```
Os mocks (`tests/fakes.py`) existem só nos testes; um teste garante que o pacote `app` não os importa.

## Deploy no Render
1. Novo **Blueprint** apontando para este repositório (`render.yaml`): serviço Docker, plano *starter*, disco persistente em `/var/data` (SQLite de jobs e relatórios — o sistema de arquivos do container é efêmero).
2. No painel, definir `GEOIA_CORS_ORIGINS` (origens do frontend) e, para a Terra, `GEE_PROJECT` + `GEE_SERVICE_ACCOUNT_JSON`.
3. Health check: `/health`. Checklist completo: [docs/DEPLOY.md](docs/DEPLOY.md).

Uma instância (jobs em processo). Para escalar horizontalmente, trocar `services/store.py` por Postgres e os jobs por uma fila.

## Segurança e operação
Timeouts e retries com backoff; allow-list de hosts para qualquer URL (inclusive as devolvidas pelos provedores) contra SSRF; limite de bytes por download; concorrência por host e por job; cache de metadados (12 h) e de resultados (24 h, sinalizado em `cache.hit`); logs JSON; segredos nunca logados nem retornados.
