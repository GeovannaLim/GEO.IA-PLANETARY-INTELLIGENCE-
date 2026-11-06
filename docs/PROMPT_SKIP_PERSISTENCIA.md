# Prompt para o Skip — guardar análises e relatórios no PocketBase do Skip

Motivo: o backend roda no Render Free, cujo disco é temporário. A cada reinício (o servidor dorme após ~15 min sem uso) os resultados e PDFs guardados lá somem, e `GET /v1/reports/{id}` passa a responder 404. A cópia permanente fica no Skip, por usuário. O backend não muda.

Cole o texto abaixo no assistente do Skip.

---

Quero que cada análise científica concluída fique salva no banco do próprio Skip (PocketBase), por usuário, para que o resultado e o PDF continuem disponíveis mesmo quando o backend reiniciar. Não mude o visual existente além do que está pedido aqui.

## 1. Nova coleção `analyses`
| Campo | Tipo | Observação |
|---|---|---|
| `user` | relation → `users` (obrigatório, 1) | dono |
| `body` | select: `lunar`, `mars`, `earth` | |
| `latitude` | number | coordenadas **usadas** (`doc.coordinates.latitude`) |
| `longitude` | number | `doc.coordinates.longitude` (−180..180) |
| `radius_km` | number | `doc.coordinates.radius_km` |
| `label` | text | nome exibido (candidato ou "Área selecionada") |
| `analysis_id` | text | `doc.analysis_id` |
| `status` | text | `completed` ou `failed` |
| `result` | json | documento **inteiro** devolvido pela API, sem alterar nada |
| `report_pdf` | file (1 arquivo, `application/pdf`, até 5 MB, protegido) | PDF do backend |
| `created` | autodate | |

Regras de acesso (API rules): listar, ver, criar e apagar só quando `user = @request.auth.id`; ninguém atualiza (`updateRule` vazio/negado). Não deixe a coleção pública.

## 2. Ao concluir uma análise (`status === "completed"`)
1. Baixe o PDF do backend e guarde como arquivo (o CORS do backend já libera este domínio).
2. Crie o registro com `FormData`: campos acima e `result = JSON.stringify(doc)`.
```ts
const pdf = await fetch(`${GEOIA_API_BASE}/v1/reports/${doc.report_id}?format=pdf`).then(r => r.ok ? r.blob() : null);
const fd = new FormData();
fd.append("user", pb.authStore.record.id);
fd.append("body", body); fd.append("label", label); fd.append("status", doc.status);
fd.append("analysis_id", doc.analysis_id);
fd.append("latitude", String(doc.coordinates.latitude));
fd.append("longitude", String(doc.coordinates.longitude));
fd.append("radius_km", String(doc.coordinates.radius_km));
fd.append("result", JSON.stringify(doc));
if (pdf) fd.append("report_pdf", new File([pdf], `geoia_${doc.analysis_id}.pdf`, { type: "application/pdf" }));
await pb.collection("analyses").create(fd);
```
3. Se o download do PDF falhar, salve o registro mesmo assim (sem `report_pdf`) e não mostre erro ao usuário.
4. Não salve duas vezes o mesmo `analysis_id` para o mesmo usuário.
5. Análises `failed` não precisam ser salvas.

## 3. Botão "Abrir relatório PDF"
1. Se o registro salvo tiver `report_pdf`, abra o arquivo do PocketBase (`pb.files.getURL(record, record.report_pdf, {token})` com token de arquivo protegido).
2. Senão, abra `GET /v1/reports/{report_id}?format=pdf` do backend.
3. Se o backend responder 404, mostre: "O relatório original expirou no servidor. Rode a análise novamente para gerar um novo PDF."

## 4. Histórico "Minhas análises"
* Um item discreto no menu da conta (botão com o nome do usuário) abre a lista das análises salvas do usuário, mais recentes primeiro: corpo, coordenadas, raio, data, nível de confiança (`result.confidence.level`).
* Clicar num item abre o mesmo painel de resultado usando `result` salvo — **sem** chamar o backend — e o globo centraliza nas coordenadas.
* Permitir apagar um item (com confirmação).
* Mostrar no painel aberto do histórico a data em que a análise foi calculada (`result.cache.computed_at` ou `created`).

## 5. Regras
* Nunca altere valores científicos do `result` salvo; ele é exibido exatamente como veio da API.
* Não salve dados de usuários não logados.
* Mantenha a chamada ao backend como está (mesmo cliente, polling e conversão de longitude).

## Teste de aceite
1. Logado, rodar Marte em qualquer ponto; conferir que aparece em "Minhas análises" com PDF anexado.
2. Abrir o item do histórico: o painel aparece sem nenhuma requisição ao backend.
3. Clicar em "Abrir relatório PDF" no item salvo: abre o PDF guardado no Skip.
4. Outro usuário não vê esse registro.
