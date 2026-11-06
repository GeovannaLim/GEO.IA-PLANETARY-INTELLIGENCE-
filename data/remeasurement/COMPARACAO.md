# Remedição da biblioteca EMIT — comparação

Gerado em 2026-11-06T23:34:55+00:00 a partir de `data/remeasurement/library_emit_remeasured.json`.

Sítios: 90 · com pixels de rocha: 89 · sem pixels de rocha: 1 · sem cenas EMIT: 0 · outros: 0

## Efeito da vegetação em 2 µm

* Correlação NDVI (EMIT, composto de qualidade) × bd2000 bruto: 0.749 (n=90)
* Correlação NDVI × bd2000 só rocha: 0.460 (n=89)
* Correlação fração vegetada × (bd2000 bruto − rocha): 0.364 (n=89)
* Mediana de (bd2000 bruto − rocha): 0.078
* Reprodutibilidade: mediana |bd2000 biblioteca antiga − bruto remedido| = 0.051 (n=90; mesmo composto sem máscara, cenas possivelmente diferentes)

## Por sítio

| Sítio | Coord. | Status | bd1000 antigo | bruto | rocha | bd2000 antigo | bruto | rocha | fração rocha | fração vegetada | 1 µm detect. | 2 µm detect. | cenas |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Escondida | high | ok | 0.038 | 0.043 | 0.044 | -0.087 | -0.047 | -0.047 | 0.610 | 0.000 | True | False | 29 |
| Chuquicamata | low | ok | 0.022 | 0.028 | 0.021 | -0.017 | -0.022 | -0.031 | 0.923 | 0.000 | True | False | 24 |
| El Teniente | low | ok | 0.049 | 0.033 | 0.032 | 0.179 | 0.140 | -0.034 | 0.949 | 0.105 | True | False | 35 |
| Los Bronces | low | ok | 0.026 | -0.003 | 0.035 | 0.102 | 0.097 | -0.090 | 0.960 | 0.017 | True | False | 46 |
| Bingham Canyon | moderate | ok | -0.031 | -0.015 | 0.020 | 0.422 | 0.417 | 0.170 | 0.497 | 0.805 | True | False | 46 |
| Grasberg | moderate | ok | -0.057 | -0.063 | -0.025 | 0.670 | 0.682 | 0.681 | 0.070 | 0.310 | False | True | 6 |
| Yanacocha | high | ok | -0.041 | -0.011 | 0.078 | 0.307 | 0.337 | 0.022 | 0.012 | 0.982 | True | False | 9 |
| Pascua-Lama | high | ok | -0.001 | 0.002 | 0.015 | -0.043 | -0.016 | -0.073 | 0.888 | 0.003 | False | False | 17 |
| El Indio | high | ok | -0.018 | -0.028 | -0.011 | 0.006 | -0.036 | -0.086 | 0.994 | 0.002 | False | False | 26 |
| Pierina | low | ok | -0.049 | 0.003 | 0.075 | 0.221 | 0.165 | -0.207 | 0.147 | 0.884 | True | False | 21 |
| Hishikari | high | ok | -0.117 | 1.844 | -0.014 | 0.362 | 0.430 | 0.612 | 0.002 | 0.949 | False | True | 5 |
| Comstock Lode | moderate | ok | -0.005 | 0.004 | 0.016 | 0.100 | 0.015 | 0.019 | 0.827 | 0.608 | True | False | 45 |
| Round Mountain | high | ok | -0.008 | 0.019 | 0.011 | 0.188 | 0.076 | 0.125 | 0.954 | 0.280 | True | False | 37 |
| Olympic Dam | high | ok | 0.020 | 0.043 | 0.043 | -0.025 | -0.035 | -0.038 | 0.954 | 0.001 | True | False | 33 |
| Candelaria | high | ok | 0.034 | 0.046 | 0.048 | -0.026 | -0.051 | -0.065 | 0.974 | 0.044 | True | False | 20 |
| Ernest Henry | high | ok | -0.027 | 0.001 | 0.016 | 0.130 | 0.031 | -0.041 | 0.987 | 0.913 | True | False | 22 |
| Antamina | moderate | ok | -0.048 | -0.049 | 0.036 | 0.504 | 0.560 | 0.050 | 0.000 | 1.000 | False | False | 15 |
| Tintaya | high | ok | -0.042 | -0.017 | 0.008 | 0.338 | 0.377 | -0.015 | 0.069 | 0.897 | False | False | 11 |
| Kidd Creek | high | ok | -0.016 | -0.019 | -0.032 | 0.529 | 0.514 | 0.497 | 0.001 | 0.318 | False | True | 2 |
| Neves Corvo | high | ok | -0.027 | 0.019 | 0.035 | 0.247 | 0.188 | -0.025 | 0.245 | 0.905 | True | False | 13 |
| Bajo de la Alumbrera | high | ok | -0.004 | 0.020 | 0.029 | 0.096 | 0.037 | -0.052 | 0.997 | 0.310 | True | False | 31 |
| Cerro Verde | high | ok | 0.017 | 0.032 | 0.033 | 0.086 | 0.048 | -0.031 | 0.953 | 0.054 | True | False | 41 |
| Toquepala | low | ok | -0.042 | -0.026 | 0.019 | 0.144 | 0.075 | -0.015 | 1.000 | 0.006 | True | False | 34 |
| Morenci | moderate | ok | 0.014 | 0.028 | 0.038 | 0.022 | 0.014 | -0.024 | 0.961 | 0.373 | True | False | 34 |
| Butte | high | ok | -0.021 | 0.006 | -0.100 | 0.263 | 0.132 | 0.317 | 0.710 | 0.830 | False | True | 21 |
| Oyu Tolgoi | low | ok | 0.016 | 0.040 | 0.041 | 0.159 | 0.013 | -0.049 | 0.999 | 0.000 | True | False | 24 |
| Collahuasi | low | ok | -0.022 | -0.005 | 0.003 | 0.060 | -0.008 | -0.070 | 0.964 | 0.001 | False | False | 14 |
| Prominent Hill | low | ok | 0.099 | 0.119 | 0.122 | -0.063 | -0.038 | -0.053 | 1.000 | 0.000 | True | False | 23 |
| Carrapateena | moderate | ok | 0.029 | 0.058 | 0.057 | 0.007 | -0.018 | -0.028 | 1.000 | 0.004 | True | False | 28 |
| Salobo | low | ok | -0.049 | -0.039 | 0.050 | 0.445 | 0.491 | 0.039 | 0.063 | 0.941 | True | False | 10 |
| Sossego | high | ok | -0.047 | -0.027 | 0.054 | 0.389 | 0.405 | 0.001 | 0.069 | 0.937 | True | False | 14 |
| Mantoverde | low | ok | 0.041 | 0.063 | 0.064 | 0.053 | -0.046 | -0.095 | 1.000 | 0.000 | True | False | 22 |
| Rio Tinto | low | ok | -0.016 | 0.017 | 0.051 | 0.230 | 0.179 | 0.134 | 0.260 | 0.912 | True | False | 35 |
| Bathurst (Brunswick) | low | no_rock_pixels | -0.052 | -0.046 | — | 0.466 | 0.520 | — | 0.000 | 1.000 | — | — | 2 |
| Rouyn-Noranda (Horne) | moderate | ok | -0.005 | -0.036 | 0.006 | 0.515 | 0.541 | 0.490 | 0.026 | 0.790 | False | True | 4 |
| Bisha | moderate | ok | 0.011 | 0.040 | 0.045 | 0.009 | -0.053 | -0.089 | 0.990 | 0.225 | True | False | 21 |
| Cananea | low | ok | 0.002 | 0.026 | 0.041 | 0.090 | 0.077 | 0.023 | 0.768 | 0.556 | True | False | 26 |
| Ok Tedi | high | ok | -0.088 | -0.076 | -0.092 | 0.640 | 0.665 | 0.331 | 0.015 | 0.962 | False | True | 12 |
| Pine Creek | low | ok | 0.032 | 0.033 | 0.008 | 0.272 | 0.429 | 0.051 | 0.875 | 0.246 | True | False | 38 |
| Hedley (Nickel Plate) | moderate | ok | -0.037 | -0.034 | -0.088 | 0.408 | 0.331 | 0.508 | 0.143 | 0.994 | False | True | 27 |
| King Island (Dolphin) | high | ok | -0.072 | -0.060 | -0.017 | 0.428 | 0.380 | 0.154 | 0.018 | 0.823 | False | True | 18 |
| Empire (Mackay) | low | ok | -0.029 | 0.011 | 0.031 | 0.198 | 0.139 | -0.083 | 0.697 | 0.398 | True | False | 20 |
| Lihir (Ladolam) | high | ok | -0.248 | -0.160 | -0.051 | 0.688 | 0.758 | 0.374 | 0.047 | 0.237 | False | True | 9 |
| Waihi (Martha) | low | ok | -0.067 | -0.064 | 0.041 | 0.576 | 0.646 | 0.105 | 0.009 | 0.992 | True | True | 23 |
| El Peñón | high | ok | 0.024 | 0.032 | 0.032 | -0.107 | -0.056 | -0.064 | 1.000 | 0.000 | True | False | 30 |
| Veladero | low | ok | 0.004 | 0.011 | 0.024 | -0.073 | -0.031 | -0.084 | 0.891 | 0.001 | True | False | 17 |
| Fresnillo | high | ok | -0.017 | 0.026 | 0.033 | 0.037 | -0.024 | -0.019 | 0.851 | 0.354 | True | False | 14 |
| Cripple Creek | moderate | ok | -0.072 | -0.017 | 0.026 | 0.352 | 0.301 | 0.205 | 0.232 | 0.953 | True | True | 29 |
| Mountain Pass | high | ok | -0.016 | 0.030 | 0.041 | 0.106 | -0.008 | -0.057 | 0.983 | 0.083 | True | False | 35 |
| Bayan Obo | high | ok | -0.018 | 0.020 | 0.022 | 0.210 | 0.075 | -0.037 | 1.000 | 0.001 | True | False | 25 |
| Mount Weld | moderate | ok | 0.051 | 0.103 | 0.109 | 0.115 | -0.040 | -0.075 | 0.943 | 0.353 | True | False | 16 |
| Palabora (Phalaborwa) | high | ok | -0.020 | 0.007 | 0.035 | 0.250 | 0.166 | 0.030 | 0.136 | 0.898 | True | False | 15 |
| Oka | high | ok | -0.027 | -0.018 | -0.010 | 0.534 | 0.603 | 0.439 | 0.526 | 0.690 | False | True | 18 |
| Araxá | low | ok | -0.049 | -0.005 | 0.056 | 0.436 | 0.636 | 0.004 | 0.251 | 0.852 | True | False | 16 |
| Songwe Hill | low | ok | -0.025 | -0.018 | 0.036 | 0.327 | 0.342 | 0.019 | 0.089 | 1.000 | True | False | 19 |
| Bushveld (Rustenburg) | high | ok | -0.001 | 0.025 | 0.068 | 0.241 | 0.287 | -0.026 | 0.598 | 0.875 | True | False | 29 |
| Stillwater Complex | low | ok | -0.045 | -0.030 | -0.096 | 0.467 | 0.455 | 0.252 | 0.222 | 0.891 | False | True | 31 |
| Great Dyke | low | ok | -0.021 | 0.027 | 0.069 | 0.148 | 0.074 | -0.104 | 0.143 | 0.955 | True | False | 13 |
| Sudbury | low | ok | -0.030 | -0.019 | -0.035 | 0.623 | 0.601 | 0.229 | 0.043 | 0.979 | False | False | 16 |
| Duluth Complex | low | ok | -0.042 | -0.071 | -0.267 | 0.495 | 0.574 | 0.798 | 0.716 | 0.940 | False | True | 37 |
| Jinchuan | high | ok | -0.011 | -0.006 | -0.008 | 0.330 | 0.337 | 0.279 | 1.000 | 0.093 | False | True | 15 |
| Deccan Traps | low | ok | -0.007 | 0.021 | 0.037 | 0.221 | 0.170 | 0.044 | 0.669 | 0.830 | True | True | 33 |
| Columbia River Basalt | low | ok | -0.025 | -0.007 | 0.018 | 0.321 | 0.382 | 0.151 | 0.922 | 0.963 | True | True | 43 |
| Karoo (Drakensberg) | low | ok | -0.031 | 0.025 | 0.068 | 0.222 | 0.190 | -0.062 | 0.353 | 0.986 | True | False | 22 |
| Paraná Basalt | low | ok | -0.047 | -0.046 | 0.044 | 0.502 | 0.553 | -0.028 | 0.010 | 0.995 | True | False | 10 |
| Etendeka | low | ok | 0.058 | 0.073 | 0.073 | 0.003 | -0.023 | -0.023 | 1.000 | 0.001 | True | False | 23 |
| Emeishan | low | ok | -0.042 | -0.036 | -0.000 | 0.274 | 0.344 | -0.053 | 0.019 | 0.991 | False | False | 10 |
| Ethiopian Traps | low | ok | -0.046 | -0.006 | 0.015 | 0.189 | 0.114 | -0.013 | 0.167 | 0.995 | True | False | 27 |
| Pilbara Craton (Marble Bar) | moderate | ok | 0.026 | 0.052 | 0.061 | 0.120 | 0.003 | -0.069 | 0.997 | 0.156 | True | False | 24 |
| Kalgoorlie (Yilgarn) | moderate | ok | 0.022 | 0.053 | 0.056 | 0.041 | -0.001 | 0.088 | 0.960 | 0.618 | True | False | 38 |
| Abitibi (Timmins) | moderate | ok | -0.021 | -0.023 | -0.028 | 0.484 | 0.474 | 0.497 | 0.005 | 0.765 | False | True | 2 |
| Kolar (Dharwar) | moderate | ok | -0.011 | 0.017 | 0.007 | 0.231 | 0.184 | 0.464 | 0.346 | 0.953 | False | True | 12 |
| Las Cristinas (Guiana Shield) | low | ok | -0.038 | -0.042 | -0.014 | 0.490 | 0.502 | 0.501 | 0.005 | 0.952 | False | True | 10 |
| Geita (Tanzania Craton) | low | ok | -0.035 | -0.012 | 0.055 | 0.372 | 0.348 | -0.001 | 0.070 | 0.960 | True | False | 13 |
| Troodos Ophiolite | high | ok | -0.022 | -0.004 | 0.029 | 0.350 | 0.255 | -0.017 | 0.036 | 0.989 | True | False | 42 |
| Semail Ophiolite | low | ok | 0.023 | 0.045 | 0.046 | 0.084 | -0.056 | -0.064 | 0.988 | 0.033 | True | False | 34 |
| New Caledonia Ophiolite | low | ok | -0.043 | -0.039 | 0.013 | 0.480 | 0.570 | 0.603 | 0.051 | 0.963 | False | True | 21 |
| Kilauea (Hawaii) | high | ok | -0.033 | 0.002 | 0.044 | 0.385 | 0.329 | 0.183 | 0.380 | 0.718 | True | True | 30 |
| Yellowstone | high | ok | -0.010 | -0.029 | -0.190 | 0.515 | 0.429 | 0.633 | 0.198 | 0.860 | False | True | 30 |
| Long Valley Caldera | low | ok | 0.015 | -0.036 | 0.041 | 0.241 | 0.207 | 0.001 | 0.629 | 0.853 | True | False | 34 |
| Valles Caldera | low | ok | 0.007 | -0.031 | 0.041 | 0.331 | 0.295 | 0.103 | 0.250 | 0.999 | True | True | 38 |
| Taupo Volcanic Zone | low | ok | -0.052 | -0.023 | -0.012 | 0.439 | 0.399 | 0.227 | 0.062 | 0.749 | False | True | 31 |
| Láscar | high | ok | -0.035 | -0.012 | 0.017 | 0.011 | -0.007 | -0.052 | 1.000 | 0.003 | True | False | 25 |
| Erta Ale | low | ok | 0.028 | 0.022 | 0.029 | 0.087 | 0.014 | -0.006 | 1.000 | 0.000 | True | False | 35 |
| Hamersley (Mt Whaleback) | low | ok | 0.064 | 0.093 | 0.099 | 0.007 | -0.057 | -0.075 | 0.996 | 0.135 | True | False | 32 |
| Mesabi Range | low | ok | -0.056 | -0.059 | -0.036 | 0.483 | 0.513 | 0.523 | 0.284 | 0.910 | False | True | 33 |
| Quadrilátero Ferrífero | low | ok | -0.040 | -0.015 | 0.052 | 0.341 | 0.399 | -0.006 | 0.039 | 0.996 | True | False | 17 |
| Kryvyi Rih | low | ok | -0.042 | -0.004 | 0.013 | 0.369 | 0.355 | 0.182 | 0.238 | 0.868 | True | True | 23 |
| Cuajone | low | ok | -0.032 | -0.012 | 0.021 | 0.092 | 0.033 | -0.045 | 0.997 | 0.062 | True | False | 34 |
| Barberton Greenstone | low | ok | -0.047 | -0.018 | 0.049 | 0.277 | 0.291 | -0.042 | 0.080 | 0.969 | True | False | 14 |
