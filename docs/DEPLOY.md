# Deploy — GitHub + Render

## Produção (2026-11-05)
| Item | Valor |
|---|---|
| GitHub | https://github.com/GeovannaLim/GEO.IA-PLANETARY-INTELLIGENCE- (branch `main`) |
| Render | https://geoia-planetary-backend.onrender.com (plano Free, Docker) |
| Health | 200, `environment: production`, `database: ok`, Earth Engine `initialized: true` (service account) |
| CORS | `https://geoai-interplanetary.goskip.app` |
| Validação real A–F | **27/27** (`examples/production_validation_render.json`) |


## Estado da verificação (2026-11-05, nesta máquina)
| Item | Resultado |
|---|---|
| Testes offline | 72 aprovados, 3 live pulados (rodam só com `GEOIA_LIVE_TESTS=1`) |
| Testes live (NASA/USGS reais) | 3/3 aprovados |
| Instalação limpa de `requirements.txt` (Python 3.12) | OK |
| Servidor com layout do container, `production`, banco separado | `/health`, Marte real, PDF, Terra `not_configured`, CORS, persistência após reinício: OK |
| `docker build` | **Não executado** (Docker indisponível aqui). O workflow `.github/workflows/tests.yml` faz build + health check no GitHub Actions |
| Inspeção de segredos | 0 ocorrências em arquivos versionados e no histórico |

## 1. GitHub (repositório privado)
Sem GitHub CLI nesta máquina. Duas formas:

**a) Com `gh`** (instalar de https://cli.github.com):
```bash
gh auth login
```
```bash
cd ~/Downloads/geoia-planetary-backend && gh repo create geoia-planetary-backend --private --source . --remote origin --push
```
`gh repo create` falha se o nome já existir na conta — nesse caso, não force; inspecione o repositório existente.

**b) Pelo site:** criar `geoia-planetary-backend` **privado e vazio** (sem README/licença) em github.com/new, depois:
```bash
cd ~/Downloads/geoia-planetary-backend && git remote add origin https://github.com/<conta>/geoia-planetary-backend.git && git push -u origin main
```

## 2. Render
Não há CLI/API do Render autenticada nesta máquina — o deploy é feito pelo painel.

1. https://dashboard.render.com → **New → Blueprint** → conectar o GitHub → escolher `geoia-planetary-backend`.
2. O `render.yaml` cria o serviço web Docker no plano **free** (sem custo).
3. Preencher no painel: `GEOIA_CORS_ORIGINS` = `https://geoai-interplanetary.goskip.app` (plataforma Skip); opcional `GEE_PROJECT` = `<id do projeto Google Cloud>` + `GEE_SERVICE_ACCOUNT_JSON` (conteúdo da chave JSON de uma service account com acesso ao Earth Engine).
4. Após “Live”: verificar
   ```bash
   curl -i https://<servico>.onrender.com/health
   ```

### Persistência — decisão: **plano Free (demonstração)**, escolhido em 2026-11-05
Jobs e relatórios ficam em SQLite efêmero: baixe/abra o PDF logo após cada análise da demonstração. Antes da demo, chame `/health` para acordar a instância.

Opções avaliadas:
| Opção | Custo | Jobs/relatórios sobrevivem a redeploy/reinício | Observação |
|---|---|---|---|
| **Free (padrão)** | 0 | **Não** — SQLite no disco efêmero; instância dorme após ~15 min sem tráfego (primeira requisição leva ~1 min) | Aceitável para demonstração; relatórios devem ser baixados logo após a análise |
| **Starter + disco 1 GB** | pago (ver preço atual no Render) | Sim; jobs interrompidos são retomados automaticamente | Descomentar o bloco `disk:` e trocar `plan: free` → `plan: starter` |
| Postgres externo | depende do provedor | Sim | Exige implementar um store Postgres (não feito) |

Manter **1 instância**: os jobs rodam no processo e o SQLite pertence a uma instância.

## 3. Validação em produção (após o deploy)
```bash
B=https://<servico>.onrender.com
curl -s $B/health
curl -s -X POST "$B/v1/lunar/analyze?wait_s=50" -H "Content-Type: application/json" -d '{"latitude":25.8,"longitude":-15.2,"radius_km":10}'
curl -s -X POST "$B/v1/mars/analyze?wait_s=50" -H "Content-Type: application/json" -d '{"latitude":18.44,"longitude":77.45,"radius_km":5}'
curl -s -X POST "$B/v1/mars/analyze?wait_s=50" -H "Content-Type: application/json" -d '{"latitude":-85.0,"longitude":150.0,"radius_km":10}'
```
Ou: `PYTHONPATH=. .venv/bin/python scripts/validate_production.py https://<servico>.onrender.com` (executa todos os testes A–F e grava `var/production_validation.json`).
