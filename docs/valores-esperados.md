# Valores esperados para conferencia do DAX

Reproduza cada recorte no Power BI e compare. Divergencia indica erro de contexto de filtro, nao de dados.

Base: 1,053,221 coletas | 02/09/2024 a 31/08/2026

## 1. Sem nenhum filtro (total geral)

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Coletas | todos | `1,053,221` |
| Postos Distintos | todos | `11,151` |
| Municipios Distintos | todos | `419` |
| Preco Mediano | todos os produtos juntos | `5.9900` |
| Preco Medio | todos os produtos juntos | `5.7158` |

## 2. Filtro: um produto, periodo completo

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Preco Mediano | Produto = Diesel S10 | `6.2800` |
| Preco Mediano | Produto = Etanol | `4.4300` |
| Preco Mediano | Produto = Gasolina | `6.2900` |
| Amplitude P90-P10 | Produto = Diesel S10 | `1.4000` |
| Amplitude P90-P10 | Produto = Etanol | `1.3000` |
| Amplitude P90-P10 | Produto = Gasolina | `1.1000` |

## 3. Guarda de amostra pequena (deve devolver BLANK)

A medida `Amplitude P90-P10` exige 30 postos distintos. Roraima tem 15, entao deve ficar em branco - e nao aparecer como o mercado mais homogeneo do pais.

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Amplitude P90-P10 | UF = RR, Gasolina, ultimas 8 semanas (15 postos) | `BLANK` |
| Amplitude P90-P10 | UF = AC, Gasolina, ultimas 8 semanas (15 postos) | `BLANK` |
| Amplitude P90-P10 | UF = SP, Gasolina, ultimas 8 semanas (1706 postos) | `0.8000` |

## 4. Paridade Etanol/Gasolina

Estas medidas usam `REMOVEFILTERS(Dim_Produto)`. Devem devolver o MESMO valor com o slicer de produto em 'Gasolina', em 'Etanol' ou sem selecao. Se mudarem, o REMOVEFILTERS nao foi aplicado.

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Paridade Etanol/Gasolina | UF = SP, periodo completo | `0.6552` |
| Paridade Etanol/Gasolina | UF = MS, periodo completo | `0.6423` |
| Paridade Etanol/Gasolina | UF = AP, periodo completo | `0.8854` |
| Paridade Etanol/Gasolina | UF = RS, periodo completo | `0.7837` |
| Paridade Etanol/Gasolina | Brasil, periodo completo | `0.7043` |

## 5. Variacao no periodo e transmissao

Primeira e ultima semana ISO da janela completa.

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Variacao no Periodo RS | Brasil, Diesel S10 | `0.9000` |
| Variacao no Periodo RS | Brasil, Etanol | `-0.1100` |
| Variacao no Periodo RS | Brasil, Gasolina | `0.4200` |

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Variacao no Periodo RS | UF = SP, Gasolina | `0.5000` |
| Transmissao vs Nacional % | UF = SP, Gasolina | `119.0%` |
| Variacao no Periodo RS | UF = RJ, Gasolina | `0.5000` |
| Transmissao vs Nacional % | UF = RJ, Gasolina | `119.0%` |
| Variacao no Periodo RS | UF = AM, Gasolina | `0.4000` |
| Transmissao vs Nacional % | UF = AM, Gasolina | `95.2%` |
| Variacao no Periodo RS | UF = MS, Gasolina | `0.2650` |
| Transmissao vs Nacional % | UF = MS, Gasolina | `63.1%` |

## 6. Variacao semanal (ultima semana com dados)

| Medida | Recorte | Valor esperado |
|--------|---------|----------------|
| Variacao Semanal RS | Diesel S10, semana de 31/08/2026 | `0.0000` |
| Variacao Semanal RS | Etanol, semana de 31/08/2026 | `-0.0100` |
| Variacao Semanal RS | Gasolina, semana de 31/08/2026 | `0.0000` |