# Limitações conhecidas

Ler antes de usar qualquer número deste relatório para decidir algo.

Cada item abaixo é uma restrição real do dado ou do método. Nenhuma
delas invalida a análise; todas mudam como ela deve ser interpretada.

---

## 1. Cobertura: 7,5% dos municípios

A ANP pesquisou **419 dos ~5.570 municípios brasileiros**. A amostra é
concentrada em capitais e cidades grandes.

**Consequência:** onde está escrito "Brasil", leia "os municípios
pesquisados pela ANP". O preço do interior pouco populoso está
sub-representado, e é justamente onde a distância da base de distribuição
mais encarece o combustível. É provável que o preço nacional real seja
**mais alto** e **mais disperso** do que o medido aqui.

---

## 2. A coleta não é ponderada por volume

Cada posto entra na mediana com peso 1, seja um posto de rodovia que
vende 500 mil litros/mês ou um posto de bairro que vende 30 mil.

**Consequência:** "preço mediano" é o preço do **posto mediano**, não o
preço que o **consumidor mediano** pagou. Para saber o segundo seria
preciso o volume vendido por posto, que não é público.

---

## 3. A coleta se concentra em segunda e terça

| Dia | Coletas |
|---|---:|
| Segunda | 420.008 |
| Terça | 257.313 |
| Quarta | 191.362 |
| Quinta | 156.204 |
| Sexta | 27.282 |
| Sábado | 1.024 |
| Domingo | 28 |

**Consequência:** uma série **diária** mediria o calendário de campo da
ANP, não o mercado. Toda a análise usa **grão semanal** (segunda-feira
da semana ISO) por esse motivo. Comparações são sempre de 7 em 7 dias.

---

## 4. Abril de 2026 não existe na fonte

A ANP não publicou os arquivos de abril/2026 — nem `gasolina-etanol`
nem `diesel-gnv`. Não é falha do pipeline; a etapa 1 reporta a lacuna
explicitamente.

**Consequência:** há um buraco de um mês na série. Medidas de variação
que atravessam abril/2026 comparam março com maio. O evento de queda
detectado em 27/04/2026 deve ser lido com essa ressalva — ele marca a
primeira semana **com dado** após a lacuna, e parte do movimento pode
ter ocorrido durante o mês ausente.

---

## 5. `Valor de Compra` está 100% vazio

A coluna existe no arquivo da ANP mas não é preenchida em nenhuma linha
do período analisado. Verificado, não presumido.

**Consequência:** **é impossível calcular a margem do revendedor** a
partir desta base. Qualquer afirmação sobre quanto o posto ganha por
litro estaria inventada. O projeto não faz essa afirmação.

---

## 6. Não há preço de refinaria nesta base

A pergunta original era "quanto de um reajuste da Petrobras chega à
bomba". Não existe fonte pública e estruturada dos preços de realização
de refinaria; o portal de preços da Petrobras é um CMS sem API de dados.

**Consequência e decisão de projeto:** em vez de digitar à mão uma lista
de comunicados — introduzindo erro não auditável — os eventos de preço
são **detectados a partir do próprio dado** (z-score robusto sobre a
variação semanal da mediana nacional).

Isso muda o que a análise mede, e a mudança é honesta: ela mede o
movimento que **efetivamente chegou à bomba**, sem pressupor que um
anúncio tenha se propagado. Mas significa que **os eventos aqui não são
reajustes da Petrobras**. São quebras estruturais na série de preço ao
consumidor, que podem ter origem em reajuste de refinaria, mudança
tributária, câmbio, safra ou sazonalidade — a base não distingue.

---

## 7. Coincidência não é causa

Um evento detectado próximo a uma decisão comercial ou regulatória **não
demonstra** relação entre os dois. Este projeto mede **o que** aconteceu
no preço ao consumidor. Não mede **por quê**.

---

## 8. Estados pequenos não são comparáveis aos grandes

Roraima tem **15 postos pesquisados, todos em Boa Vista**. São Paulo tem
1.706 só nas últimas 8 semanas.

Em RR, 107 de 132 coletas recentes de gasolina registraram exatamente
**R$ 7,57**. A dispersão P90−P10 resultante é de R$ 0,02 — o que faria
Roraima parecer o mercado mais eficiente do país num ranking ingênuo.

**Tratamento:** as medidas de dispersão exigem **no mínimo 30 postos
distintos** e retornam BLANK abaixo disso. A medida `Alerta Amostra`
sinaliza as células afetadas.

**Sobre a uniformidade em si:** preço praticamente idêntico entre postos
é uma observação factual e é tudo o que se pode afirmar. Ela admite
várias explicações — mercado pequeno e isolado, distribuidor único,
custo logístico dominando o preço final, acompanhamento mútuo de preços.
**Esta base não distingue entre elas**, e concluir qualquer uma seria
ir além do dado.

---

## 9. Vibra não é Petrobras

`VIBRA` é a segunda maior bandeira da amostra (215.919 coletas) e é a
antiga **BR Distribuidora**, desligada do grupo Petrobras em 2021. Ela
compra da Petrobras, mas é empresa independente.

**Consequência:** tratar a bandeira Vibra como "postos Petrobras" seria
erro material. A Petrobras atua no início da cadeia (refino e
distribuição primária); a bandeira do posto é uma relação comercial da
distribuidora, não da Petrobras.

Do mesmo modo, `BRANCA` (36% das coletas) não significa "sem
fornecedor" — significa posto **sem contrato de exclusividade** de
bandeira. Ele compra de quem oferecer melhor preço.

---

## 10. Carga tributária não foi isolada

O preço na bomba embute tributos que variam entre estados. Parte das
diferenças regionais observadas é tributária, não margem nem logística.

**Atenção:** o regime de tributação de combustíveis no Brasil mudou nos
últimos anos, com adoção de alíquota monofásica em R$/litro. **Confirme
o regime vigente no período analisado antes de atribuir qualquer
diferença regional a margem comercial.** Este projeto não faz essa
decomposição e não deve ser citado como se fizesse.

---

## 11. Produtos fora de escopo

Excluídos por decisão de projeto, não por falta de dado:

| Produto | Motivo |
|---|---|
| GNV | Vendido em m³ — não soma com R$/litro |
| GLP | Vendido em botijão de 13 kg — mesma incompatibilidade |
| Gasolina Aditivada | Variante premium, patamar de preço distinto |
| Diesel S500 | Em substituição pelo S10; mistura as séries |

Isso responde por 33,4% das linhas lidas.

---

## 12. A última semana está incompleta

A janela termina em 31/08/2026, uma segunda-feira. A última semana ISO
tem **1 dia útil de dados** contra 5 das demais.

**Tratamento:** `Dim_Calendario[EhSemanaCompleta]` marca essa semana
como incompleta. Filtre por ela em análises de variação semanal, ou a
última semana aparecerá com variação artificialmente próxima de zero.

---

## 13. O limiar de 70% é regra de bolso

A paridade etanol/gasolina de 70% vem da diferença média de rendimento
energético entre os dois combustíveis. O rendimento real varia por
veículo, motor, calibragem e estilo de condução — na prática, algo entre
65% e 75%.

**Consequência:** `% Semanas Etanol Compensa` é um indicador de
tendência, não um conselho de abastecimento. Um estado com paridade
média de 69,4% (Goiás) está perto demais do limiar para que a
classificação seja robusta.

---

## O que seria preciso para resolver

| Limitação | O que resolveria |
|---|---|
| Cobertura e ponderação | Volume de vendas por posto (não público) |
| Margem do revendedor | Preço de compra do posto |
| Repasse real de reajuste | Série de preço de realização de refinaria |
| Decomposição tributária | Alíquota vigente por UF e período |
| Causalidade | Desenho quase-experimental e variáveis de controle |
