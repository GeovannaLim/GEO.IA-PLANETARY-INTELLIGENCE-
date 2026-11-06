# Prompt para o Skip — sítios análogos terrestres

Cole o texto abaixo no assistente do Skip. Ele **não cria globo terrestre** e não muda o visual existente: só acrescenta um bloco ao painel de análise da Lua e de Marte.

---

O backend passou a devolver, nas análises da Lua e de Marte, um campo novo `terrestrial_analogs` com **locais reais da Terra** que servem de análogos geológicos da região selecionada. Mostre-o no painel de resultado, logo depois do bloco atual de "Análogos terrestres" (o ranking por similaridade continua igual).

## 1. Onde fica e quando aparece
* Campo: `terrestrial_analogs` (pode ser `null` em análises antigas do histórico: nesse caso não mostre o bloco).
* Título do bloco: **"Sítios análogos na Terra"**.
* Se `status` for `"unavailable"`, mostre só as frases de `notes` (ou "Sem sítio análogo documentado para esta região.") — nunca invente sítios.
* Se `basis === "global_context"` (Marte sem cobertura CRISM), mostre um aviso destacado com o texto de `notes[0]`: os sítios **não** são específicos da região.

## 2. Evidência da região
* `region_evidence[]`: cada item tem `label` (já em português com `lang=pt-BR`), `indicators` (códigos como `IBD1000`, `MIN2295_2480`) e `strength` (`"specific"` | `"broad"`).
* Mostre como chips: `label` + códigos em fonte mono. `broad` com o rótulo "evidência ampla".
* `unexplained_evidence` não vazio → a frase correspondente já está em `notes`.

## 3. Cada sítio (`sites[]`, no máximo 5, já ordenados)
Mostre um cartão por sítio com:
* `name` e `country`.
* Coordenadas `latitude`, `longitude` com 4 casas e a precisão `± coordinate_precision_km km`. Torne as coordenadas um link para `https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=11/{lat}/{lon}` (abre em nova aba). **Não crie globo nem mapa da Terra embutido.**
* `setting` (descrição geológica) e `key_minerals` como chips.
* Selo pequeno com `analog_basis`: `published_analog` → "Análogo publicado"; `simulant_source` → "Fonte de simulante"; `published_analog_general` → "Análogo regional"; `mineralogical_reference` → "Referência mineralógica"; `outreach` → "Fonte de divulgação".
* "Por que é análogo": lista `justification`.
* "Semelhanças": lista `similarities`. "Diferenças": lista `differences`. "Limitações": lista `limitations`.
* "Fontes": `references[]` — `citation` e, se houver, link `https://doi.org/{doi}`; senão `url`.
* Se `emit` existir, uma linha pequena: "Medição EMIT: {emit.scenes} cenas, {emit.first_date}–{emit.last_date}, {round(emit.rock_fraction*100)}% de pixels de rocha".
* Nunca mostre porcentagem de similaridade, nota ou probabilidade para estes sítios: a ordem é por famílias minerais explicadas, não por pontuação.

## 4. Rodapé
* Mostre `disclaimer` em texto pequeno ao fim do bloco.
* `method` pode ir num "i" de ajuda.

## 5. Persistência
Os registros novos de `analyses` já guardam o `result` completo; não precisa de campo novo. Ao reabrir do histórico, mostre o bloco a partir do `result` salvo, sem chamar o backend.

## 6. QA
Rode typecheck, lint e build e me mande a saída. Se algum não rodar, diga qual e por quê.

## Teste de aceite (eu executo depois de publicado)
1. Lua 14.64°N 24.07°W: bloco "Sítios análogos na Terra" com sítios, coordenadas, fontes com DOI.
2. Marte Jezero 18.44°N 77.45°E: evidência da região e sítios correspondentes.
3. Marte sem CRISM (ex.: 0.99°N 328.53°E): aviso de contexto global.
4. Reabrir do histórico uma análise antiga: bloco ausente, sem erro.
