# Guia de construção do relatório

Passo a passo no Power BI Desktop, do arquivo vazio ao `.pbix` pronto.
Tempo estimado: **4 a 6 horas**.

Só recursos nativos. Nenhum visual do AppSource, nenhuma ferramenta
externa, nenhum script dentro do Power BI.

---

## Parte 1 — Modelo (≈90 min)

### 1.1 Tema

`Exibição > Temas > Procurar temas` → `docs/tema-anp.json`

As cores não foram escolhidas por gosto. Foram validadas contra
daltonismo (protanopia, deuteranopia, tritanopia), faixa de luminosidade
e contraste mínimo de 3:1 com o fundo.

| Slot | Cor | Uso |
|---|---|---|
| 1 | `#3B6FD6` azul | Gasolina |
| 2 | `#1A8A6B` verde | Etanol |
| 3 | `#C2611A` âmbar | Diesel S10 |
| 4–6 | roxo / teal / vinho | `GrupoBandeira` |

> Com os 3 primeiros, o pior par adjacente tem ΔE 9,7 (protanopia) —
> acima do alvo de 8. Usando os 6, cai para 6,8, o que **só é aceitável
> com codificação secundária**: rótulo direto ou eixo de categoria. Ou
> seja, em qualquer visual com mais de 3 cores, a identidade nunca pode
> depender só da cor.

### 1.2 Parâmetro e consultas

1. `Transformar dados > Gerenciar Parâmetros > Novo`
   - Nome: `pCaminhoDados`, Tipo: Texto
   - Valor: caminho absoluto de `data/processed`
2. Criar `fnCarregarCsv` e as 8 consultas de
   [`powerquery/consultas.m`](powerquery/consultas.m), nessa ordem.
3. `Aux_Paridade_UF_Semana`: clique direito → **desmarcar "Habilitar
   carga"**. Ela serve para conferência, não para o relatório.
4. `Fechar e Aplicar`.

### 1.3 Tabela de datas

Selecione `Dim_Calendario` → `Ferramentas de Tabela > Marcar como tabela
de datas` → coluna `Data`.

**Não pule.** Sem isso, `DATEADD` e `DATESINPERIOD` devolvem resultados
silenciosamente errados — e metade das medidas depende deles.

### 1.4 Relações

Na exibição de Modelo, crie 7 relações. Todas **1:N**, **direção de
filtro única**, dimensão → fato:

| De | Para |
|---|---|
| `Dim_Calendario[Data]` | `Fato_Coleta[Data]` |
| `Dim_Produto[SK_Produto]` | `Fato_Coleta[SK_Produto]` |
| `Dim_Geografia[SK_Municipio]` | `Fato_Coleta[SK_Municipio]` |
| `Dim_Bandeira[SK_Bandeira]` | `Fato_Coleta[SK_Bandeira]` |
| `Dim_Revenda[SK_Revenda]` | `Fato_Coleta[SK_Revenda]` |
| `Dim_Calendario[Data]` | `Fato_Evento_Preco[Data]` |
| `Dim_Produto[SK_Produto]` | `Fato_Evento_Preco[SK_Produto]` |

Se o Power BI sugerir alguma relação bidirecional, recuse.

### 1.5 Higiene do modelo

- **Ocultar** todas as `SK_*`, `ID_Revenda`, `DiaSemanaNum`, `AnoMes`,
  `AnoSemanaISO`, `DiasUteisComDados`
- **Ordenar por coluna**: `NomeMes`→`Mes`, `AnoMesNome`→`AnoMes`,
  `NomeDiaSemana`→`DiaSemanaNum`
- `Fato_Coleta[Preco]`: formato `R$ #.##0,000`, **Resumo = Não resumir**
- Criar tabela vazia `_Medidas` (`Inserir dados` → OK → ocultar a coluna
  `Coluna1`), mover todas as medidas para lá

### 1.6 Medidas

Cole as medidas de [`dax/medidas.dax`](dax/medidas.dax) e atribua as
pastas de exibição indicadas.

Formatos: percentuais com 1 casa, reais com 3 casas (combustível é
cotado em milésimos), `Transmissao vs Nacional %` com 0 casas.

### 1.7 Conferência — não pule

Abra [`valores-esperados.md`](valores-esperados.md), monte uma tabela
descartável e compare. Alguns que valem conferir:

| Recorte | Medida | Esperado |
|---|---|---|
| Sem filtro | `Coletas` | 1.053.221 |
| Sem filtro | `Postos Distintos` | 11.151 |
| Gasolina | `Preco Mediano` | 6,29 |
| SP, período todo | `Paridade Etanol/Gasolina` | 0,6552 |
| RR, Gasolina, 8 sem. | `Amplitude P90-P10` | **BLANK** |
| SP, Gasolina | `Transmissao vs Nacional %` | 119,0% |

**Teste decisivo da paridade:** com o slicer de produto em "Gasolina",
depois em "Etanol", depois sem seleção, `Paridade Etanol/Gasolina` deve
devolver **exatamente o mesmo número**. Se mudar, o
`REMOVEFILTERS(Dim_Produto)` não está funcionando.

Depois apague a tabela de conferência.

---

## Parte 2 — Páginas (≈3 h)

Três páginas. Regras válidas nas três:

- **Uma linha de filtros no topo**, nunca espalhados pela página
- **Título diz o achado, não o campo.** "Diesel subiu 24,6% em três
  semanas", não "Soma de Preço por Data"
- **Legenda sempre presente com 2+ séries**; até 4 séries, também rótulo
  direto — identidade nunca depende só de cor
- **Nunca eixo duplo.** Duas medidas de escala diferente = dois visuais
- Filtre `Dim_Calendario[EhSemanaCompleta] = Verdadeiro` no nível de
  página, ou a última semana aparecerá com variação falsa de zero

---

### Página 1 — Visão Geral

```
┌──────────────────────────────────────────────────────────┐
│  [Título Dinâmico]                                        │
│  [Base da Amostra]                            (cartão)    │
├──────────────────────────────────────────────────────────┤
│  Produto ▾    Região ▾    Período ═══════════             │
├──────────┬──────────┬──────────┬────────────────────────┤
│ Mediano  │ Var. %   │ P90-P10  │ Postos                  │
│ R$ 6,29  │ +6,9%    │ R$ 1,10  │ 11.151                  │
├──────────┴──────────┴──────────┴────────────────────────┤
│                                                           │
│   Preço mediano semanal, por produto        (linhas)     │
│                                                           │
├───────────────────────────┬──────────────────────────────┤
│  Ranking de UF     (barras)│  Dispersão por UF  (barras)  │
└───────────────────────────┴──────────────────────────────┘
```

**Filtros (segmentações)** — `Dim_Produto[NomeProduto]` (lista),
`Dim_Geografia[NomeRegiao]` (lista), `Dim_Calendario[Data]` (entre)

**Cartões** — `Preco Mediano`, `Variacao no Periodo %`,
`Amplitude P90-P10`, `Postos Distintos`

**Gráfico de linhas** — Eixo `Dim_Calendario[InicioSemana]` · Legenda
`Dim_Produto[NomeProduto]` · Valor `Preco Mediano`
→ 3 séries, cores do tema. Ative rótulo direto na última categoria.

**Barras horizontais (×2)** — Eixo `Dim_Geografia[UF]` · Valor
`Preco Mediano` / `Amplitude P90-P10`, ordenado decrescente.

> Use barras, não mapa. Mapa e Mapa Coroplético dependem do Bing Maps,
> serviço externo frequentemente bloqueado em ambiente corporativo. A
> barra ordenada também lê melhor: comparar comprimentos é mais preciso
> que comparar tons de cor num mapa.

---

### Página 2 — Transmissão de preço

A página analítica. É aqui que o projeto responde à pergunta.

```
┌──────────────────────────────────────────────────────────┐
│  Filtros: Produto ▾    Período ═══════════                │
├──────────────────────────────────────────────────────────┤
│  Preço mediano nacional                      (linhas)     │
│                                                           │
├──────────────────────────────────────────────────────────┤
│  Eventos detectados (Δ R$/litro)             (colunas)    │
│  ▏mesmo eixo de tempo, alinhado ao gráfico acima▕         │
├───────────────────────────┬──────────────────────────────┤
│  Transmissão por UF        │  Nível × movimento           │
│  (matriz, format. cond.)   │  (dispersão)                 │
└───────────────────────────┴──────────────────────────────┘
```

**Linha + colunas alinhadas.** Power BI não desenha linhas de referência
a partir de uma tabela. A solução correta **não** é gráfico de eixo
duplo — é **dois visuais empilhados compartilhando o eixo de tempo**:

- Acima: linhas, `InicioSemana` × `Preco Mediano`
- Abaixo: colunas, `Fato_Evento_Preco[Data]` × `DeltaRS`, altura ~1/3

Alinhe as bordas esquerda e direita e fixe a mesma faixa de datas nos
dois. Lê-se como um só gráfico, mas cada eixo mede uma coisa só.

**Matriz de transmissão** — Linhas `UF` · Colunas `NomeProduto` ·
Valores `Transmissao vs Nacional %`

Formatação condicional → Escala de cores divergente:
- Mínimo `#1A8A6B` · **Centro em `1` (=100%)** cinza `#EDEDE9` ·
  Máximo `#C2611A`
- Mantenha o **número visível** na célula: a cor é reforço, não o dado

Leitura: 100% = acompanhou o país. Abaixo = repassou menos. Acima =
amplificou.

**Dispersão** — X `Variacao no Periodo RS` · Y `Preco Mediano` ·
Detalhes `UF` · Tamanho `Postos Distintos`

Separa quatro mundos: caro e subindo rápido, caro e estável, barato e
subindo, barato e estável.

---

### Página 3 — Paridade do etanol

```
┌──────────────────────────────────────────────────────────┐
│  Paridade nacional: 70,4%   |   Compensa em 21,5%         │
├──────────────────────────────────────────────────────────┤
│  Paridade por UF e mês               (matriz, cond.)      │
│  centro em 0,70                                           │
├───────────────────────────┬──────────────────────────────┤
│  % semanas favoráveis (barras) │  Vantagem R$/km (barras) │
└───────────────────────────┴──────────────────────────────┘
```

**Matriz** — Linhas `UF` · Colunas `AnoMesNome` · Valores
`Paridade Etanol/Gasolina`

Formatação condicional divergente com **centro exatamente em `0,7`**:
`#1A8A6B` (etanol compensa) → `#EDEDE9` → `#C2611A` (não compensa).

O centro em 0,70 é o que transforma a matriz em resposta. Numa escala
contínua comum, a distinção que importa desapareceria.

**Barras** — `% Semanas Etanol Compensa` e `Vantagem Etanol RS por km`
por UF, ordenadas.

Adicione um cartão com `Alerta Amostra` ao lado da matriz.

> **Dois números de paridade nacional, ambos certos.**
> `outputs/achados.md` informa **73,7%**; a medida DAX devolve **70,4%**.
> Não é divergência — são agregações diferentes:
>
> | Valor | O que é |
> |---|---|
> | 73,7% | Média simples das razões UF-semana. Cada estado pesa igual, então o Amapá (89,1%) puxa tanto quanto São Paulo. |
> | 70,4% | Mediana nacional do etanol ÷ mediana nacional da gasolina. Reflete o peso real de cada estado na amostra. |
>
> O relatório exibe **70,4%**, porque é o valor que responde "qual a
> paridade no país". O 73,7% responde "qual a paridade do estado médio" —
> outra pergunta. Se perguntarem, esta é a resposta.

---

## Parte 3 — Acabamento (≈45 min)

- [ ] Todo visual tem título que afirma algo
- [ ] Nenhum título automático do tipo "Soma de Preco por Data"
- [ ] Ordem de tabulação definida (`Exibição > Ordem de tabulação`)
- [ ] Texto alternativo nos visuais principais
- [ ] Dicas de ferramenta úteis, não repetindo o eixo
- [ ] Rodapé: fonte, período, data de extração
- [ ] Botão de limpar filtros (marcador com todos os filtros abertos)
- [ ] Nenhuma informação transmitida só por cor
- [ ] `Amplitude P90-P10` em branco para RR e AC — e isso é o correto
- [ ] Salvar como `Precos-Combustiveis-ANP.pbix`

---

## Apresentação de 5 minutos

| Tempo | Conteúdo |
|---|---|
| 0:00 | **Pergunta.** Quando o preço se move no país, quanto chega a cada estado? |
| 0:30 | **Dados.** 1,05 milhão de coletas da ANP, 24 meses, 27 UFs. Públicos. |
| 1:00 | **Método.** Python para ETL e detecção de evento; DAX para o cálculo de negócio. Por que a divisão. |
| 1:45 | **Achado 1.** SP repassa 119% do movimento nacional; MS, 63%. |
| 2:30 | **Achado 2.** O mapa do etanol é o mapa da cana. MS 100%, AP nunca. |
| 3:15 | **Achado 3.** Amazonas: R$ 2,21 de faixa de preço; SP, R$ 0,80. Logística. |
| 4:00 | **Limitações.** 7,5% dos municípios. Não ponderado por volume. Não mede causa. |
| 4:30 | **Próximo passo.** Com volume por posto e preço de refinaria, viraria margem real. |

### Perguntas que virão

**"Por que mediana e não média?"**
Preço de bomba tem cauda longa à direita — posto de rodovia e de
aeroporto. A média sobe atrás deles e deixa de representar o que o
consumidor típico paga. A medida `Assimetria Media-Mediana` mostra o
tamanho desse efeito.

**"Roraima tem a menor dispersão do Brasil?"**
Não. Roraima tem 15 postos, todos em Boa Vista, e 107 de 132 coletas
recentes no mesmo preço. Por isso a medida exige 30 postos e devolve
vazio abaixo disso. Preço uniforme é uma observação; ela admite várias
explicações e esta base não distingue entre elas.

**"Esses eventos são reajustes da Petrobras?"**
Não. São quebras estatísticas na série ao consumidor. Não existe fonte
pública estruturada do preço de realização de refinaria, e eu preferi
detectar o que chegou à bomba a transcrever comunicados à mão. Podem ter
origem em reajuste, tributo, câmbio ou safra — a base não separa.

**"Por que Python se a vaga é de Power BI?"**
Porque cada ferramenta faz o que faz bem. Detecção de quebra estrutural
com z-score robusto é ruim em DAX e trivial em pandas. Já mediana por
estado e semana respeitando o filtro do usuário é exatamente o que o
VertiPaq existe para fazer — e precalcular isso mataria a interatividade.
É a mesma divisão de uma arquitetura corporativa: pipeline governado a
montante, modelo semântico a jusante.

**"Como você colocaria isso em produção?"**
Pipeline agendado gravando em área governada; `.pbix` publicado em
workspace com gateway apontando para lá; atualização incremental por mês;
RLS por região se houver recorte por unidade. Nada disso exige biblioteca
fora do padrão.
