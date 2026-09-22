# Valores esperados para conferência do DAX

Gerado por `src/step05_validate.py`. A suíte executável equivalente está em `docs/testes-dax.json` e roda com `scripts/Invoke-TestesDax.ps1`.

Base: 1,053,221 coletas · 02/09/2024 a 31/08/2026


## 1. Contagens, sem filtro

| Medida | Recorte | Esperado |
|--------|---------|----------|
| Coletas | sem filtro | `1,053,221` |
| Postos Distintos | sem filtro | `11,151` |
| Municipios Distintos | sem filtro | `419` |

## 2. Preço mediano por produto

| Medida | Recorte | Esperado |
|--------|---------|----------|
| Preco Mediano | Produto = Diesel S10 | `6.2800` |
| Preco Mediano | Produto = Etanol | `4.4300` |
| Preco Mediano | Produto = Gasolina | `6.2900` |
| Amplitude P90-P10 | Produto = Diesel S10 | `1.4000` |
| Amplitude P90-P10 | Produto = Etanol | `1.3000` |
| Amplitude P90-P10 | Produto = Gasolina | `1.1000` |

## 3. Guarda de amostra pequena

`Amplitude P90-P10` exige 30 postos distintos. RR tem 15 — deve devolver BLANK em vez de aparecer como o mercado mais homogêneo do país.

| Medida | Recorte | Esperado |
|--------|---------|----------|
| Amplitude P90-P10 | RR, Gasolina, 8 sem. (15 postos) | `BLANK` |
| Amplitude P90-P10 | AC, Gasolina, 8 sem. (15 postos) | `BLANK` |
| Amplitude P90-P10 | SP, Gasolina, 8 sem. (1706 postos) | `0.8000` |

## 4. Paridade etanol/gasolina

Usa `REMOVEFILTERS(Dim_Produto)`: deve dar o mesmo valor com o slicer de produto em Gasolina, em Etanol ou sem seleção.

| Medida | Recorte | Esperado |
|--------|---------|----------|
| Paridade Etanol/Gasolina | UF = SP | `0.6552` |
| Paridade Etanol/Gasolina | UF = MS | `0.6423` |
| Paridade Etanol/Gasolina | UF = AP | `0.8854` |
| Paridade Etanol/Gasolina | UF = RS | `0.7837` |
| Paridade Etanol/Gasolina | Brasil | `0.7043` |

## 5. Variação no período e transmissão

Primeira semana 02/09/2024, última 31/08/2026.

| Medida | Recorte | Esperado |
|--------|---------|----------|
| Variacao no Periodo RS | Brasil, Diesel S10 | `0.9000` |
| Variacao no Periodo RS | Brasil, Etanol | `-0.1100` |
| Variacao no Periodo RS | Brasil, Gasolina | `0.4200` |
| Transmissao vs Nacional % | UF = SP, Gasolina | `119.0%` |
| Transmissao vs Nacional % | UF = RJ, Gasolina | `119.0%` |
| Transmissao vs Nacional % | UF = AM, Gasolina | `95.2%` |
| Transmissao vs Nacional % | UF = MS, Gasolina | `63.1%` |

## 6. Eventos de preço

| Medida | Recorte | Esperado |
|--------|---------|----------|
| N Eventos de Preco | sem filtro | `12` |
| N Eventos de Preco | Produto = Diesel S10 | `4` |
| N Eventos de Preco | Produto = Etanol | `2` |
| N Eventos de Preco | Produto = Gasolina | `6` |