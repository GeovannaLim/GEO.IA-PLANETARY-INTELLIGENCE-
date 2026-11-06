# Prompt para o Skip — estabilização, QA e apresentação (missão de demonstração)

Cole o texto abaixo no assistente do Skip.

---

Esta rodada é de **estabilização**, não de novas funcionalidades. Não mude o visual, não reconstrua Lua ou Marte e **não crie tela da Terra**. Faça só os itens abaixo e, no fim, rode o QA e me mande a saída.

## 1. Textos científicos em português (backend já suporta)
* Acrescente `lang=pt-BR` em **todas** as chamadas ao backend:
  * `POST /v1/{corpo}/analyze?wait_s=20&lang=pt-BR`
  * o polling já vem certo: `links.self` passa a incluir `?lang=pt-BR`. Use `links.self` como está.
* Não traduza no frontend: interpretações, limitações, avisos e métodos já chegam em português. Nomes de instrumentos, códigos de produto (`M3G...`, `frt...`), códigos de parâmetros (`IBD1000`, `BD2210_2`, `legacy_bd2000`) e unidades continuam como vêm.
* O relatório PDF continua em inglês (forma canônica) por enquanto.
* Análises antigas do histórico foram salvas em inglês; mostre-as como estão (não traduza nem reprocesse).

## 2. Título da aba do navegador
* `/` → `GEØ.IA — Planetary Intelligence`
* `/moon` → `Lua · GEØ.IA`
* `/mars` → `Marte · GEØ.IA`
* Atualize ao trocar de rota (sem recarregar a página). Defina também `<html lang="pt-BR">` (hoje está `en`).

## 3. Rótulo "CANDIDATO 3D" no histórico
Ao reabrir uma análise salva, o painel mostra o selo genérico "CANDIDATO 3D". Use os metadados gravados no registro:
* seleção manual (`target_name` = "Área selecionada") → selo "SELEÇÃO MANUAL";
* candidato/região de referência → o nome salvo (`target_name`) e o tipo original.
Se o tipo não estiver salvo, grave-o ao criar o registro (campo novo `target_kind`: `area` | `candidate` | `reference`) e, para registros antigos sem o campo, use "ANÁLISE SALVA".

## 4. Análogos terrestres — exibir o que o backend já informa
Novos campos opcionais em `earth_analogs` (podem não existir em análises antigas):
* `discrimination`: `"low"` | `"moderate"` | `"adequate"` → mostre um selo junto do título: "Discriminação baixa" / "moderada" / "adequada".
* `discrimination_note`: frase curta explicando o selo; mostre logo abaixo.
* `indistinguishable_sites`: quantos sítios não se distinguem do primeiro dentro da incerteza de medida.
* `query_values` (valores da região analisada) e, em cada item de `matches`, `earth_values` e `differences` (região − sítio, por atributo).
* Em cada análogo, mostre os **atributos usados** (`attributes_used`) com os dois valores e a diferença, em linha pequena: `legacy_bd1000: 0,048 vs 0,058 (−0,010)`.
* Quando `discrimination === "low"`, mostre a similaridade com **uma casa decimal a menos** e o texto "ordem pouco significativa" ao lado do ranking. Nunca rotule como probabilidade.
* Mantenha o texto de `disclaimer`.

## 5. Indicador `legacy_bd1000` / `legacy_bd2000`
O backend passou a mostrar a profundidade **sem corte** por pixel (valores negativos significam contínuo convexo = **sem absorção**). Não esconda nem converta valores negativos; mostre-os com o sinal e a `interpretation` que vem da API. Não use esses valores para nenhum cálculo no frontend.

## 6. Espera do servidor (cold start)
* Hoje a mensagem "Preparando o servidor científico…" já aparece. Acrescente, se a espera passar de 15 s: "O servidor gratuito estava em repouso e está iniciando; isso pode levar até 1 minuto." e um contador de segundos.
* Não crie chamadas periódicas para manter o servidor acordado.

## 7. Acessibilidade básica
* O `<canvas>` do globo: `role="img"` e `aria-label="Globo 3D da Lua"` / `"Globo 3D de Marte"`.
* Botões só com ícone precisam de `aria-label` (ex.: item da lista "Minhas análises": "Abrir análise de <nome> de <data>").
* O painel de análise deve receber foco ao abrir e devolver o foco ao botão de origem ao fechar; `Esc` fecha.
* No celular, o texto "Scroll para aproximar" deve ser "Pinça para aproximar".

## 8. Segurança do PocketBase (coleção `analyses`)
Ajuste as regras para que o dono só possa **anexar o PDF**, nunca alterar o resultado científico nem transferir o registro:
* `listRule` / `viewRule`: `owner = @request.auth.id`
* `createRule`: `@request.auth.id != "" && @request.body.owner = @request.auth.id`
* `updateRule`: `owner = @request.auth.id && @request.body.owner:isset = false && @request.body.result:isset = false && @request.body.report_id:isset = false && @request.body.body:isset = false && @request.body.latitude:isset = false && @request.body.longitude:isset = false`
* `deleteRule`: `owner = @request.auth.id`
* `pdf_file` continua **Protected**.

## 9. QA — rode e me mande a saída completa
1. `typecheck` (tsc) — sem erros.
2. `lint` — sem erros (avisos listados).
3. Build de produção.
4. Se houver testes, rode-os.
Se algum não puder rodar, diga qual e por quê; não marque como aprovado.

## Teste de aceite (eu executo depois de publicado)
1. Lua 14.64°N 24.07°W: textos científicos em português, gráfico do espectro, análogos com selo de discriminação e atributos.
2. Marte (qualquer ponto com CRISM): parâmetros com `sensitive_to` em português; códigos inalterados.
3. Marte sem cobertura: mensagem de ausência, sem números.
4. Reabrir do histórico: selo correto (não "CANDIDATO 3D"), sem chamada ao backend.
5. Título da aba correto em `/`, `/moon`, `/mars`.
