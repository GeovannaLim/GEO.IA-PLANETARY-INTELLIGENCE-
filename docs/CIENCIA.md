# Métodos científicos, critérios e limitações

## Convenções
* Latitude **planetocêntrica**; longitude **leste-positiva**. A API aceita `[-180, 180)` (padrão, `east_180`) ou `[0, 360)` com `"longitude_convention": "east_360"`, e converte para cada provedor (`science/coordinates.py`): ODE/GDS/PDS/CRISM em 0–360; Trek/STAC em −180..180.
* Regiões são círculos de `radius_km` (limites: Lua 25 km, Marte 50 km, Terra 25 km). O bbox que envolve o círculo é aberto em todas as longitudes quando atinge um polo, e dividido em dois quando cruza 0° (o antimeridiano ±180° não cruza nada em 0–360).

## Topografia (Lua: LOLA RDR; Marte: MOLA PEDR)
Dados numéricos medidos: tiros individuais do altímetro laser via ODE GDS (somente tiros válidos, flag 0). Nunca são usados tiles WMTS.
* Datum: LOLA = raio − esfera de 1737,4 km; MOLA PEDR = raio − areoide.
* Pontos recortados ao círculo numa projeção azimutal equidistante local.
* `regional_slope_degrees`/`regional_aspect_degrees`: plano de mínimos quadrados.
* `local_slope_degrees`: grade com célula = `slope_baseline_m` (adaptada à densidade), mediana por célula, diferenças centrais.
* `roughness_m`: RMS dos resíduos em relação ao plano. `coverage_fraction`: fração de células com dados.
* Se o GDS recusar a área ou o arquivo exceder o limite, o raio amostrado é reduzido à metade (até 3 vezes) e isso aparece em `sampled_radius_km` e nas limitações.

## Mineralogia — Lua (M3 L2)
1. ODE: footprints `REFIMG` que intersectam o ponto; prioridade aos que o contêm e com centro mais próximo.
2. Backplane LOC do L1B localiza o pixel mais próximo (busca grosso-fino com leituras Range de ~5 KB). Rejeita se o pixel estiver a mais de max(1 km, 3 pixels).
3. Janela de até 41×41 px lida numa única requisição; máscara: fora do raio, −999, ≤ 0, ≥ 1,5, bandas < 540 nm e > 2600 nm.
4. Indicadores: `IBD1000`, `IBD2000` (após Mustard et al. 2011), `legacy_bd1000/2000` (definição da biblioteca terrestre), `R750`, `slope_750_1550`.
5. Se não houver pixels válidos, tenta-se a observação seguinte; senão `insufficient_data`.

## Mineralogia — Marte (CRISM MTRDR)
Parâmetros-sumário calculados pela equipe CRISM (Viviano-Beck et al. 2014) lidos do cubo `SU` mapeado (pixel calculado analiticamente pela projeção equiretangular do cabeçalho). Bandas I/F do cubo `IF` alimentam as `legacy_bd` para comparação. Índices lunares não são aplicados a Marte.
Sem MTRDR no ponto: se existirem TRDR não projetados → `no_compatible_observations`; senão `no_coverage`.

## Critério de “detecção” (triagem)
Um indicador de profundidade de banda é marcado positivo quando: média da janela > 3 × erro-padrão (n efetivo = pixels/25, para correlação espacial ~5×5 px), mediana > 0 e ≥ 60 % dos pixels positivos. Isso detecta **uma absorção positiva**; não é abundância nem identificação mineral. Valores muito pequenos mas espacialmente consistentes podem passar — por isso o texto sempre diz “screening”.

## Análogos terrestres
* **Diretamente comparáveis**: `legacy_bd1000`, `legacy_bd2000` (mesma fórmula, reflectância VSWIR nos dois lados).
* **Proxies aproximados** (listados, nunca pontuados): IBD lunares, BDI1000IR/LCP/HCP do CRISM.
* **Não comparáveis**: maturidade lunar, hidratação/filossilicatos/carbonatos/sulfatos/gelo do CRISM, índices ASTER TIR, NDVI.
* Pontuação: distância euclidiana; `similarity = 1 − d / (0,4·√n)` serve **apenas para ordenar**. Com 2 atributos a discriminação é fraca, e a biblioteca (90 sítios EMIT) é dominada por sistemas hidrotermais — isso é avisado em `disclaimer`.

## Confiança
`confidence.level` é calculado a partir dos critérios aplicáveis (lista em `confidence.criteria`):
* altimetria: ≥ 30 tiros; cobertura de células ≥ 0,3; raio pedido integralmente amostrado;
* espectroscopia: pixel dentro da tolerância; ≥ 25 pixels válidos; incidência solar ≤ 70° (quando conhecida).

Todos atendidos → `high`; ≥ 2/3 → `moderate`; abaixo → `low`; nenhum critério aplicável → `not_assessed`. Sem mineralogia disponível o nível máximo é `moderate`.

## Limitações conhecidas
* M3: correção térmica empírica (região de 2 µm em terreno quente); ~140/280 m/px; correlação espacial.
* CRISM: footprints de ~10 km; parâmetros-sumário sensíveis a ruído e CO2 residual; I/F ≠ reflectância de superfície EMIT.
* Biblioteca terrestre: datas de extração EMIT não foram arquivadas pelo pipeline antigo.
* Diviner (Lua) e DTMs USGS são **descobertos e listados**, não lidos.
* Terra depende de credencial Earth Engine; não foi testada com dados reais neste ambiente.
