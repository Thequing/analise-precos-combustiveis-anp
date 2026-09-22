# Dicionário de dados

Gerado automaticamente a partir de `data/processed/` por `src/step06_dictionary.py`. Não editar à mão — reexecutar.

Todos os arquivos: CSV, separador vírgula, decimal ponto, codificação UTF-8 com BOM.

### `Fato_Coleta`

**Fato** — Grao: posto x produto x dia de coleta.

1,053,221 linhas · 6 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `Data` | Data | 521 | `02/09/2024` | Data da coleta de preco pela ANP. |
| `SK_Produto` | Inteiro | 3 | `1` | Chave substituta do produto. |
| `SK_Municipio` | Inteiro | 419 | `31` | Chave substituta do municipio. |
| `SK_Bandeira` | Inteiro | 49 | `47` | Chave substituta da bandeira. |
| `SK_Revenda` | Inteiro | 11,151 | `6435` | Chave substituta do posto. |
| `Preco` | Decimal | 617 | `7.29` | Preco de venda ao consumidor, R$/litro. |

### `Fato_Evento_Preco`

**Fato** — Quebras estruturais detectadas na serie semanal nacional.

12 linhas · 10 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `SK_Evento` | Inteiro | 12 | `1` | Chave substituta do evento. |
| `Data` | Data | 8 | `09/03/2026` | Segunda-feira da semana ISO em que a quebra foi detectada. |
| `SK_Produto` | Inteiro | 3 | `1` | Chave substituta do produto. |
| `NomeProduto` | Texto | 3 | `Diesel S10` | Nome tratado para exibicao. |
| `PrecoAntes` | Decimal | 10 | `6.09` | Mediana nacional na semana anterior ao evento. |
| `PrecoDepois` | Decimal | 11 | `6.79` | Mediana nacional na semana do evento. |
| `DeltaRS` | Decimal | 9 | `0.7` | Variacao em R$/litro. |
| `DeltaPct` | Decimal | 11 | `11.49` | Variacao percentual. |
| `ZRobusto` | Decimal | 9 | `6.89` | Z-score robusto (MAD) da variacao semanal. Modulo maior ou igual a 2,5 define o evento. |
| `Direcao` | Texto | 2 | `Alta` | Alta ou Baixa. |

### `Dim_Calendario`

**Dimensao** — Tabela de datas. Marcar como Tabela de Datas no Power BI.

735 linhas · 16 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `Data` | Data | 735 | `02/09/2024` | Data do calendario. Chave da relacao com os fatos. |
| `Ano` | Inteiro | 3 | `2024` | Ano civil. |
| `Mes` | Inteiro | 12 | `9` | Numero do mes (1-12). |
| `NomeMes` | Texto | 12 | `Set` | Abreviacao do mes em portugues. |
| `AnoMes` | Inteiro | 25 | `202409` | Ano e mes como inteiro (202601). Usar para ordenar AnoMesNome. |
| `AnoMesNome` | Texto | 25 | `Set/24` | Rotulo de exibicao (Jan/26). |
| `Trimestre` | Texto | 4 | `T3` | Trimestre (T1-T4). |
| `AnoTrimestre` | Texto | 9 | `2024-T3` | Ano e trimestre (2026-T1). |
| `SemanaISO` | Inteiro | 52 | `36` | Numero da semana ISO 8601. |
| `AnoSemanaISO` | Inteiro | 105 | `202436` | Ano e semana ISO como inteiro. Usar para ordenar. |
| `InicioSemana` | Data | 105 | `02/09/2024` | Segunda-feira da semana ISO. EIXO TEMPORAL PRINCIPAL da analise. |
| `DiaSemanaNum` | Inteiro | 7 | `0` | 0 = segunda, 6 = domingo. |
| `NomeDiaSemana` | Texto | 7 | `Segunda` | Dia da semana em portugues. |
| `EhFimDeSemana` | Booleano | 2 | `False` | Verdadeiro para sabado e domingo. |
| `DiasUteisComDados` | Inteiro | 2 | `5` | Dias uteis da semana cobertos pela janela de coleta (0-5). |
| `EhSemanaCompleta` | Booleano | 2 | `True` | Falso quando a semana tem menos de 5 dias uteis com dados. FILTRAR em analises de variacao semanal. |

### `Dim_Produto`

**Dimensao** — Combustiveis analisados.

3 linhas · 5 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `SK_Produto` | Inteiro | 3 | `1` | Chave substituta do produto. |
| `Produto` | Texto | 3 | `DIESEL S10` | Nome do produto como publicado pela ANP. |
| `NomeProduto` | Texto | 3 | `Diesel S10` | Nome tratado para exibicao. |
| `Origem` | Texto | 2 | `Fossil` | Fossil ou Renovavel. |
| `Unidade` | Texto | 1 | `R$ / litro` | Unidade de medida. Homogenea por construcao (R$ / litro). |

### `Dim_Geografia`

**Dimensao** — Hierarquia Regiao > UF > Municipio.

419 linhas · 6 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `SK_Municipio` | Inteiro | 419 | `1` | Chave substituta do municipio. |
| `Regiao` | Texto | 5 | `CO` | Sigla da regiao (N, NE, CO, SE, S). |
| `UF` | Texto | 27 | `DF` | Sigla da unidade da federacao. |
| `Municipio` | Texto | 418 | `BRASILIA` | Nome do municipio em caixa alta, como publicado. |
| `NomeRegiao` | Texto | 5 | `Centro-Oeste` | Nome da regiao por extenso. |
| `UF_Municipio` | Texto | 419 | `BRASILIA / DF` | Rotulo composto para desambiguar municipios homonimos. |

### `Dim_Bandeira`

**Dimensao** — Bandeira do posto (distribuidora contratada).

49 linhas · 4 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `SK_Bandeira` | Inteiro | 49 | `1` | Chave substituta da bandeira. |
| `Bandeira` | Texto | 49 | `ALE` | Bandeira como publicada pela ANP. |
| `GrupoBandeira` | Texto | 6 | `Ale` | Agrupamento das 5 maiores; demais viram Outras. |
| `EhBandeiraBranca` | Booleano | 2 | `False` | Verdadeiro para posto sem contrato de exclusividade. |

### `Dim_Revenda`

**Dimensao** — Posto revendedor, pseudonimizado.

11,151 linhas · 3 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `SK_Revenda` | Inteiro | 11,151 | `1` | Chave substituta do posto. |
| `ID_Revenda` | Texto | 11,151 | `00105ce1b419` | Hash SHA-256 truncado do CNPJ. Pseudonimo estavel; o CNPJ nao e armazenado. |
| `NomeRevenda` | Texto | 9,657 | `POSTO ABASTECIMENTO SAO J...` | Razao social do posto, conforme publicado pela ANP. |

### `Aux_Paridade_UF_Semana`

**Auxiliar** — Conferencia do DAX. Nao carregar no modelo final.

2,715 linhas · 6 colunas

| Coluna | Tipo | Distintos | Exemplo | Descrição |
|--------|------|----------:|---------|-----------|
| `UF` | Texto | 27 | `AC` | Sigla da unidade da federacao. |
| `InicioSemana` | Data | 102 | `02/09/2024` | Segunda-feira da semana ISO. |
| `Etanol` | Decimal | 293 | `4.98` | Mediana semanal do etanol na UF. |
| `Gasolina` | Decimal | 271 | `7.19` | Mediana semanal da gasolina na UF. |
| `Paridade` | Decimal | 1,415 | `0.6926286509040334` | Razao etanol / gasolina. |
| `EtanolCompensa` | Booleano | 2 | `True` | Verdadeiro quando a paridade fica abaixo de 0,70. |

---

## Relações do modelo

| De | Para | Cardinalidade | Direção |
|----|------|---------------|---------|
| `Dim_Calendario[Data]` | `Fato_Coleta[Data]` | 1:N | Única |
| `Dim_Produto[SK_Produto]` | `Fato_Coleta[SK_Produto]` | 1:N | Única |
| `Dim_Geografia[SK_Municipio]` | `Fato_Coleta[SK_Municipio]` | 1:N | Única |
| `Dim_Bandeira[SK_Bandeira]` | `Fato_Coleta[SK_Bandeira]` | 1:N | Única |
| `Dim_Revenda[SK_Revenda]` | `Fato_Coleta[SK_Revenda]` | 1:N | Única |
| `Dim_Calendario[Data]` | `Fato_Evento_Preco[Data]` | 1:N | Única |
| `Dim_Produto[SK_Produto]` | `Fato_Evento_Preco[SK_Produto]` | 1:N | Única |

Nenhuma relação bidirecional. Nenhuma relação inativa.

## Colunas a ocultar no modelo

Todas as `SK_*` no fato e nas dimensões, `ID_Revenda`, `DiaSemanaNum`, `AnoMes`, `AnoSemanaISO` e `DiasUteisComDados`. São chaves e auxiliares de ordenação: úteis ao modelo, ruído no painel de campos.

## Ordenação por coluna

| Coluna exibida | Ordenar por |
|----------------|-------------|
| `NomeMes` | `Mes` |
| `AnoMesNome` | `AnoMes` |
| `NomeDiaSemana` | `DiaSemanaNum` |
