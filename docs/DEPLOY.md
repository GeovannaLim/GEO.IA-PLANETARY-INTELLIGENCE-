# Deploy no Render — checklist

Verificado localmente (2026-11-05): instalação limpa de `requirements.txt` em Python 3.12; servidor iniciado só com `app/` (layout do container), `GEOIA_ENVIRONMENT=production`, banco em diretório separado; `/health`, análise Marte real, PDF, Terra (`not_configured`), CORS e persistência após reinício. **Não verificado aqui:** `docker build` (Docker indisponível nesta máquina) — o workflow `.github/workflows/tests.yml` faz o build e o health check no GitHub Actions.

1. Publicar o repositório no GitHub (privado recomendado).
2. Render → **New → Blueprint** → selecionar o repositório. O `render.yaml` cria:
   * serviço web Docker `geoia-planetary-backend`, plano *starter*;
   * disco persistente `geoia-data` em `/var/data` (1 GB) — onde fica o SQLite de jobs e relatórios.
3. Preencher no painel (são `sync: false`, nunca ficam no repositório):
   * `GEOIA_CORS_ORIGINS` = origem(ns) exata(s) do frontend, ex. `https://app.geoia.com.br`;
   * opcional, só para a Terra: `GEE_PROJECT` e `GEE_SERVICE_ACCOUNT_JSON` (JSON completo da service account com acesso ao Earth Engine).
4. Após o deploy:
   ```bash
   curl https://<servico>.onrender.com/health
   curl -X POST "https://<servico>.onrender.com/v1/lunar/analyze?wait_s=45" -H "Content-Type: application/json" -d '{"latitude":25.8,"longitude":-15.2,"radius_km":10}'
   ```
   Esperado: `database: ok`; análise com `topography.status = available`. Primeira análise pode levar 15–60 s (servidores do PDS frios).
5. Manter **1 instância**: jobs rodam em processo e o SQLite está num disco de uma única instância.

Operação: logs JSON no painel do Render; `/health` mostra jobs em execução e estado do Earth Engine (sem segredos). Rollback: “Deploy a previous commit” no painel — o disco persiste entre deploys.
