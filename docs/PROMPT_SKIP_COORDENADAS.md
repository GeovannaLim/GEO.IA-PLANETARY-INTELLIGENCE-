# Prompt para o Skip — digitar latitude e longitude

Cole o texto abaixo no assistente do Skip. Ele não muda o visual existente: só torna editáveis os campos LAT e LON da barra inferior.

---

Hoje a barra inferior dos globos da Lua e de Marte só mostra LAT e LON do ponto clicado. Quero que o usuário também possa **digitar** as coordenadas, porque acertar um ponto exato no globo com o mouse é difícil.

## 1. Campos
* Transforme os valores de LAT e LON da barra inferior em campos editáveis, nos dois globos (Lua e Marte), mantendo o estilo atual.
* Latitude: número decimal de 0 a 90 com seletor N/S (ou −90 a 90, negativo = S).
* Longitude: mantenha a convenção que cada globo já exibe hoje (Marte em 0–360 °E; Lua em E/W). Aceite também valores de −180 a 180 (negativo = W) e converta para a convenção do globo na exibição.
* Aceite vírgula ou ponto como separador decimal (ex.: "18,44" e "18.44").
* Até 4 casas decimais.

## 2. Comportamento
* Ao confirmar (Enter, sair do campo ou um botão "Ir"), o marcador da área selecionada vai para a coordenada digitada e o globo gira até centralizá-la, com o mesmo raio já escolhido.
* Clicar no globo continua funcionando e atualiza os campos, como hoje.
* Valor inválido ou fora do intervalo: borda vermelha e mensagem curta ("Latitude entre −90 e 90"), sem mover o marcador e sem habilitar "Analisar área".
* A análise enviada ao backend usa exatamente a coordenada digitada (mesma conversão de longitude que já é feita para o clique), e o painel continua mostrando "COORDENADAS USADAS".
* Não crie globo nem mapa da Terra.

## 3. Atalhos opcionais
Uma lista pequena "Locais de exemplo" ao lado dos campos, que só preenche os campos:
* Marte: Jezero 18.44°N 77.45°E; Gale 5.40°S 137.80°E; Meridiani 1.95°S 354.47°E.
* Lua: Mare Imbrium 32.80°N 15.60°W; Apollo 17 20.19°N 30.77°E.

## 4. QA
Rode typecheck, lint e build e me mande a saída. Se algum não rodar, diga qual e por quê.

## Teste de aceite (eu executo depois de publicado)
1. Digitar 18,44 N e 77,45 E em Marte → marcador em Jezero, análise com "COORDENADAS USADAS" 18.4400 / 77.4500.
2. Digitar −72,55 de longitude → exibido como 287,45 °E.
3. Latitude 95 → erro, botão desabilitado.
4. Clicar no globo depois de digitar → campos atualizados.

---

## Correção após o 1º teste (2026-11-09)

Cole no Skip:

```text
A barra de coordenadas quebrou o app. Ao clicar em "Ir" (ou confirmar o campo), a página inteira fica preta com "Uncaught ReferenceError: checkErrorMessage is not defined" no componente da barra de coordenadas (aquele com aria-label "Barra de coordenadas e análise de área"). A função checkErrorMessage é chamada mas nunca foi definida.

1. Defina a função no mesmo arquivo do componente, antes de usá-la:
   const checkErrorMessage = (result) => (result.ok ? null : result.message);
   (result é o retorno da validação de latitude/longitude: {ok:true, value} ou {ok:false, message}.)
2. Envolva o painel do globo num error boundary, para que um erro nesse componente mostre uma mensagem em vez de apagar a página toda.
3. Layout: a barra inferior virou uma forma oval grande sobre o globo. Volte ao formato de barra horizontal compacta de antes (pílula baixa), com LAT, LON, "Ir", "Locais de exemplo" e "ANALISAR ÁREA" na mesma linha no desktop; no celular pode quebrar em duas linhas, sem cobrir o centro do globo.
4. Ao escolher um item de "Locais de exemplo", além de preencher os campos, aplique a coordenada como se o usuário tivesse clicado em "Ir" (marcador posicionado e "ANALISAR ÁREA" habilitado).

Rode typecheck, lint e build e me mande a saída. O typecheck deveria ter acusado a função não definida: se ele passou, diga por quê.
```

---

## Ajustes após o 2º teste (2026-11-10)

Coordenadas digitadas, validação, conversão de longitude, clique no globo e atalhos funcionam (Jezero digitado → "COORDENADAS USADAS" 18.4400 / 77.4500, sítios Samail, Dresser, Twin Sisters, Kaʻū, Puʻu Nēnē). Restam dois ajustes. Cole no Skip:

```text
Dois ajustes, sem mexer no que já funciona na barra de coordenadas:

1. Layout da barra inferior: ela continua como uma forma oval grande (borda arredondada enorme) sobre a parte de baixo do globo. Deixe-a como uma barra horizontal compacta, baixa, com cantos arredondados normais, encostada no rodapé: LAT, LON, "Ir", "Locais de exemplo" e o botão de análise na mesma linha no desktop; no celular (largura < 640 px) pode quebrar em duas linhas. Ela não pode cobrir o centro do globo.

2. Bloco "Sítios análogos na Terra": quando `terrestrial_analogs.notes` tiver itens e `status` for "available" e `basis` não for "global_context", mostre essas notas logo abaixo de "Evidência da região", em texto pequeno com ícone de informação. Exemplo real (Jezero): "Nenhum sítio do catálogo documenta esta família: gelo de CO2 ou H2O (BD1435/BD1500_2)." Hoje essa frase não aparece. Para "unavailable" e "global_context" mantenha o comportamento atual.

Rode typecheck, lint e build e me mande a saída.
```

---

## Ajuste após o 3º teste (2026-11-10) — só celular

Desktop aprovado (barra compacta; nota do gelo visível em Jezero). Cole no Skip:

```text
Só no celular (largura < 640 px), na barra de coordenadas:
1. O texto de ajuda "Arraste para girar · Scroll para aproximar" fica por cima dos campos LAT/LON. No celular, esconda esse texto ou coloque-o acima da barra, sem sobrepor nada.
2. Os rótulos "LAT" (à esquerda) e "E" (à direita) ficam cortados na borda da barra. Deixe os rótulos inteiros dentro da barra (pode reduzir a largura dos campos).
Não mude o layout do desktop.

Rode typecheck, lint e build e me mande a saída.
```

---

## Ajuste após o 4º teste (2026-11-10) — texto de ajuda no celular

Rótulos LAT/E corrigidos; desktop sem regressão. Falta só o texto de ajuda. Cole no Skip:

```text
No celular o texto de ajuda ainda fica por cima dos campos LAT/LON. O elemento é o <div class="interaction-hint"> (position: absolute; bottom: 66px). Como a barra de coordenadas no celular tem cerca de 75 px de altura e fica a ~14 px do rodapé, o texto cai dentro dela.

Corrija só para largura < 640 px, com uma destas opções:
  @media (max-width: 639px) { .interaction-hint { display: none; } }
ou, se preferir manter o texto:
  @media (max-width: 639px) { .interaction-hint { bottom: 104px; } }
Não altere o desktop.
```

---

## Ajuste após o 5º teste (2026-11-10) — regra de CSS sobrescrita

A regra nova chegou ao site, mas não vale: no CSS publicado ela aparece ANTES de duas regras antigas com a mesma especificidade, que vencem por virem depois. Cole no Skip:

```text
A regra "@media (max-width: 639px) { .interaction-hint { bottom: 104px } }" está no CSS, mas é sobrescrita por regras que vêm depois no mesmo arquivo:
  @media (width <= 700px)  { .interaction-hint { bottom: 66px; ... } }
  @media (height <= 650px) { .interaction-hint { bottom: 14px; } }
No celular o computed style continua "bottom: 66px" e o texto fica dentro da barra de coordenadas.

Corrija assim:
1. Na regra existente "@media (width <= 700px) .interaction-hint", troque "bottom: 66px" por "bottom: 104px".
2. Na regra "@media (height <= 650px) .interaction-hint { bottom: 14px }", restrinja a telas largas: "@media (min-width: 701px) and (height <= 650px)". Em telas estreitas e baixas, esconda o texto: "@media (width <= 700px) and (height <= 650px) { .interaction-hint { display: none; } }".
3. Remova a regra de 639px que ficou duplicada.
Confira no navegador, em 375×812, que o computed "bottom" de .interaction-hint é 104px e que o texto não sobrepõe a barra. Não altere o desktop.
```

---

## Ajuste após o 6º teste (2026-11-10) — CSS não foi alterado

O build novo saiu, mas o CSS publicado é idêntico ao anterior: as regras `(width <= 700px) bottom: 66px` e `(height <= 650px) bottom: 14px` continuam. Cole no Skip:

```text
A correção anterior não chegou ao CSS publicado: as regras ".interaction-hint { bottom: 66px }" (width <= 700px) e ".interaction-hint { bottom: 14px }" (height <= 650px) continuam iguais no build.

Faça a correção de forma que não dependa da ordem das regras. No FINAL do arquivo CSS global (o último a ser carregado), adicione exatamente:

@media (max-width: 700px) {
  html body .interaction-hint { bottom: 104px; }
}
@media (max-width: 700px) and (max-height: 650px) {
  html body .interaction-hint { display: none; }
}

O seletor "html body .interaction-hint" tem especificidade maior e vence as regras antigas independentemente da ordem. Não altere o desktop.

Antes de publicar, abra o app em 375×812 e confirme no DevTools que .interaction-hint tem computed "bottom: 104px". Me diga o resultado dessa conferência.
```
