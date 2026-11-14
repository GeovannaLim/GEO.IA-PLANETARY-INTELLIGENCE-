# Validação — mineralogia lunar em sombra permanente (2026-11-14)

**Base:** código local = `46f3a88` + integração de iluminação NASA/PGDA (etapa 1) + esta correção. **Nada foi commitado nem publicado.**

## 1. Causa-raiz do falso positivo (80°S, 30,5°E)
Três fatores se somaram:
1. **A sombra do relevo não era considerada.** O filtro de iluminação do M³ usa a incidência solar **geométrica** do backplane OBS: 82,5°, abaixo do corte de 85°. Essa medida ignora a sombra do relevo, e a janela fica inteira numa **sombra permanente** (mapa LPSR). A refletância medida, de ~0,008 em 1,5 µm, é luz espalhada e ruído, não luz solar direta.
2. **Sem banda detectável, a ausência virava composição.** Com sinal tão baixo, nem IBD1000 nem IBD2000 passam na detecção. Em `analog_sites.region_evidence`, a ausência das **duas** bandas virava a família `lunar_no_mafic_band`, ou seja, inferência **por exclusão**.
3. **Essa família levava a sítios.** `lunar_no_mafic_band` estava ligada aos sítios de anortosito (`sites={"anorthosite"}`), daí Shawmere, Sittampundi e Stillwater.

## 2. Arquivos e funções modificados
| Arquivo | Mudança |
|---|---|
| `app/providers/m3.py` | `M3Extraction` passa a guardar `pixel_lat`/`pixel_lon` de cada pixel válido (já eram lidos do LOC e eram descartados) |
| `app/providers/lola_illumination.py` | Novo `permanent_shadow_at(lats, lons)`: indicador de sombra permanente por pixel (LPSR); `NaN` fora da grade; erro do provedor sem nada presumido |
| `app/pipelines/lunar.py` | `mineralogy_step`: controle de sombra permanente antes dos indicadores (seção 3) |
| `app/science/analog_sites.py` | `region_evidence`: ausência das duas bandas **não** gera mais família; `match`: `inconclusive_evidence` + nota explicativa; motivo `insufficient_data` (não `no_coverage`) quando há dado mas ele é inconclusivo |
| `app/schemas/analysis.py` | Campo opcional `terrestrial_analogs.inconclusive_evidence` |
| `app/i18n.py` | Traduções para português das mensagens novas |
| Testes | `tests/integration/test_lunar_shadow_mineralogy.py` (novo), `test_lunar_illumination.py` (separação ambiente × ranking), `test_analog_sites.py` (regra do anortosito reescrita) |

Não houve mudança em Marte, nos limiares, no catálogo nem na infraestrutura.

## 3. Regras científicas implementadas
1. **Sombra permanente invalida pixels do M³** (Lua, latitude ≤ −65°). Cada pixel válido do M³ é localizado no mapa LPSR (Mazarico et al. 2011):
   * pixel em sombra permanente é **excluído**, com a limitação "N de M pixels… excluídos: a refletância ali não é luz solar direta";
   * se sobram menos de 4 pixels, a mineralogia fica **indisponível** (`insufficient_data`), com o problema "a mineralogia não é inferida".
2. **Sombra parcial:** só os pixels **fora** da sombra permanente são usados. Sombra temporária no momento da observação não é detectável com mapas de média de longo prazo (ver limitações).
3. **Sem mapa de iluminação** (falha do arquivo): **nada é presumido**. Nenhum pixel é excluído, a limitação diz que a sombra "não pôde ser verificada", e o problema fica registrado. Não se declara sombra nem iluminação.
4. **Pixel fora da grade:** estado desconhecido, declarado como tal.
5. **Ausência de bandas máficas não é anortosito.** Nenhuma família é criada; `inconclusive_evidence = ["lunar_no_mafic_band"]`; a nota explica que superfícies escuras, sombreadas, imaturas ou ruidosas também não mostram bandas; **nenhum sítio** é escolhido. Não existe critério positivo de plagioclásio implementado (por exemplo, a banda de 1,25 µm), então o resultado correto é **inconclusivo**.
6. **A seção `environment` continua sendo só contexto.** O mapa de sombra atua **apenas** como controle de validade dos pixels do M³, nunca como evidência a favor de um análogo.

## 4. Testes automatizados
**198/198 aprovados** (eram 182 em `46f3a88`; 192 após a etapa 1). Os novos cobrem:
* sombra permanente com refletância ~0 → nenhuma mineralogia e nenhum análogo;
* sombra parcial → só pixels iluminados (menos pixels válidos, limitação explícita);
* mapa ausente (503) → não presume sombra nem iluminação; limitação e problema registrados;
* nenhuma banda → inconclusivo, sem anortosito (com tradução);
* regiões não polares → detecções preservadas, sem controle de sombra;
* em ponto iluminado, os análogos são idênticos com e sem o arquivo de iluminação (o ambiente não ordena análogos);
* mensagens traduzidas para português.

Os dados sintéticos estão **só** nos testes (`tests/fakes.py`).

## 5. Resultados reais, antes (`46f3a88`, produção) e depois (código local)
| Região | Antes | Depois | Esperado | OK |
|---|---|---|---|---|
| Interior de Shackleton | mineralogia indisponível (sem sol); 0 sítios | igual + ambiente: **100% sombra permanente**, 0% sol | sombra; mineralogia inconclusiva | ✅ |
| **80°S, 30,5°E** | mineralogia "disponível"; `lunar_no_mafic_band`; **Shawmere, Sittampundi, Stillwater** | **73 de 73 pixels em sombra permanente excluídos**; indisponível; **0 sítios** | eliminar os 3 falsos | ✅ |
| Haworth | indisponível (0 pixels válidos) | igual + ambiente: 2,7% sol, 5% sombra permanente | preservar ambiente; mineralogia só com evidência | ✅ |
| Mons Malapert | indisponível (sem observação compatível) | igual + ambiente: 39% sol, <1% sombra permanente | preservar iluminação; não assumir composição | ✅ |
| Copernicus (pico) | olivina/vidro; Craters of the Moon, Merriam | **idêntico** (334 pixels) | preservar | ✅ |
| Mare Imbrium | piroxênio; 5 sítios | **idêntico** (1.681 pixels) | preservar | ✅ |

Dados: `var/shadow_regression.json`.

## 6. Regressões verificadas
* **Bateria de 21 cenários**, local, com dados reais e sem cache: 20 PASS + Olympus Mons inconclusivo. **Os 21 casos são idênticos aos de `46f3a88`** em mineralogia, produto, famílias, sítios e posições e altitude. **Marte não mudou.** (`var/science_tests_shadow.json` comparado a `var/prod_46f3a88/science_tests.json`.)
* **Ataques adversariais ao ranking:** os mesmos resultados de antes.
* **Seção `environment`:** independente do ranking (teste dedicado).

## 7. Limitações que permanecem
1. **Sombra temporária não é detectada.** O mapa LPSR é uma média de longo prazo: um pixel iluminado em média, mas na sombra no instante da observação do M³, ainda pode passar. Pegaria isso um teste de refletância mínima ou de geometria de sombra no instante, que **não foi implementado** porque não há limiar justificado nos dados.
2. **Os sítios de anortosito deixam de ser oferecidos para a Lua:** não há critério positivo de plagioclásio. É a escolha conservadora; a contrapartida é que terras altas com dado bom passam a sair como "inconclusivas".
3. **Só o polo sul** (a orientação do norte não foi validada).
4. **Resolução do mapa:** 60–240 m, contra ~140–280 m do M³, com um pixel de incerteza no posicionamento.
5. **Mais tráfego** ao arquivo do MIT em análises polares: a seção de ambiente e o controle de sombra leem o LPSR separadamente; os rótulos ficam em cache.
6. **Registros antigos** salvos no PocketBase com `lunar_no_mafic_band` continuam como foram salvos (os registros são imutáveis).

## 8. Prontidão para deploy
**Pronto para deploy, sujeito à sua autorização**, considerando a etapa 1 (iluminação) e esta correção juntas. Todos os critérios de aceitação foram verificados com dados reais, exceto o limite 1 acima, que fica **declarado**:

| Critério | Situação |
|---|---|
| Nenhum análogo lunar sustentado só por ausência de bandas | ✅ (regra + teste + 80°S real) |
| Sombra permanente comprovada impede inferência mineralógica | ✅ |
| Falta de iluminação não é confundida com falta de minerais | ✅ |
| Dados insuficientes → indisponível ou inconclusivo explícito | ✅ |
| Nenhuma regressão nas detecções lunares positivas documentadas | ✅ (Copernicus, Imbrium, Chang'e-3) |
| Nenhuma alteração no ranking marciano | ✅ (21 cenários idênticos) |
| `environment` independente do ranking | ✅ |
| Português e inglês | ✅ |
| Proveniência preservada | ✅ (`data_sources`, DOI, produtos) |
| Sombra temporária | ⚠ **não coberta** (limitação 1) |

**Antes do deploy:** registrar `46f3a88` como rollback. Depois do deploy: repetir a bateria e as 6 regiões em produção.

Diff acumulado (etapa 1 + esta correção): `var/shadow_mineralogy.diff`.
