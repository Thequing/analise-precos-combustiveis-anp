# Transmissão de preços de combustíveis no Brasil

Análise de **1.053.221 coletas de preço** da ANP em 11.151 postos,
419 municípios e 27 unidades da federação, entre **02/09/2024 e 31/08/2026**.

**Pergunta:** quando o preço de um combustível se move no país, quanto
desse movimento chega a cada estado — e onde ele não chega?

---

## Resposta resumida

**1. O movimento nacional não chega igual a lugar nenhum.**
Na gasolina, o país subiu R$ 0,42/litro no período. São Paulo e Rio de
Janeiro subiram R$ 0,50 (**119% do movimento nacional**), enquanto Mato
Grosso do Sul subiu R$ 0,27 (**63%**). Dois estados, o mesmo produto, a
mesma janela — e quase o dobro de repasse entre um e outro.

**2. O diesel teve um choque concentrado, não uma deriva.**
De 09/03 a 23/03/2026, em três semanas consecutivas, o diesel S10 saltou
R$ 6,09 → R$ 7,59 (**+24,6%**). Foram três dos doze eventos estatísticos
detectados no período inteiro. No acumulado de 24 meses o diesel subiu
15,0%, a gasolina 6,9% e o etanol **caiu** 2,6%.

**3. A vantagem do etanol é geográfica, não conjuntural.**
A razão etanol/gasolina ficou abaixo dos 70% de equilíbrio em apenas
**21,5%** das combinações estado-semana. Mas o mapa não é aleatório: ele
reproduz o cinturão canavieiro. Em Mato Grosso do Sul o etanol compensou
em **100%** das semanas; em São Paulo, 88%; no Amapá, **nunca** — lá a
razão média é 89,1%.

**4. Dispersão é um problema logístico.**
Nas últimas 8 semanas, a faixa de preço da gasolina (P90−P10) foi de
**R$ 2,21 no Amazonas** contra **R$ 0,80 em São Paulo**. Quanto mais
longe da malha de distribuição, mais o consumidor paga pelo azar de
escolher o posto errado.

Números completos em [`outputs/achados.md`](outputs/achados.md).

---

## Arquitetura

```
ANP (CSV público)
      |
      v
  [Python]  step01  download + descoberta de URL
            step02  limpeza, minimização de dados, auditoria
            step03  esquema estrela + integridade referencial
            step04  detecção de eventos (z-score robusto)
            step05  suíte de testes DAX (consulta + esperado)
            step06  dicionário de dados gerado
            step07  projeto .pbip em TMDL
            step08  modelo em TMSL (publicação por XMLA)
      |
      v
  data/processed/*.csv   <- 8 tabelas, esquema estrela
      |
      v
  [PowerShell]  Deploy-Modelo.ps1     publica + refresh
                Invoke-TestesDax.ps1  35 testes via ADOMD
      |
      v
  [Power BI]  Modelo    (relações 1:N, direção única)
              DAX       (todo cálculo de negócio)
              Relatório (3 páginas, montadas no Desktop)
```

### Por que essa divisão

**Python faz o ETL e a estatística. DAX faz o cálculo de negócio.**

Detecção de quebra estrutural com z-score robusto é péssima em DAX e
trivial em pandas. Já mediana por estado e semana, respeitando o que o
usuário selecionou num slicer, é exatamente o que o motor VertiPaq
existe para fazer — e precalcular isso em Python produziria um relatório
morto, que só responde às perguntas previstas de antemão.

É a mesma divisão de uma arquitetura corporativa real: pipeline
governado a montante, modelo semântico interativo a jusante.

---

## Restrições de ferramenta

O projeto foi construído para rodar no ambiente mais restrito que se
pode esperar de uma empresa regulada. **Nada aqui depende de permissão
de administrador.**

| Usado | Evitado | Motivo |
|---|---|---|
| Power Query (M) | Scripts Python/R *dentro* do Power BI | Desabilitados na maioria dos tenants corporativos |
| DAX | Ferramentas externas (Tabular Editor, DAX Studio) | Executáveis de terceiros sem assinatura |
| Visuais nativos | Visuais personalizados do AppSource | Exigem aprovação do administrador, mesmo os certificados |
| Conector Pasta, arquivo local | Conector Web | Saída HTTP costuma ser bloqueada; também quebra o gateway |
| `.pbix` único | Dataflows, itens do Fabric | Não pressupõe licença além do Desktop |

O Python roda **fora** do Power BI, como etapa de preparação, com três
bibliotecas de uso corrente (`pandas`, `numpy`, `requests`). O `.pbix`
lê apenas CSV do disco.

> **Mapa e Mapa Coroplético usam o Bing Maps**, um serviço externo
> frequentemente desativado em tenants restritos. O relatório usa barras
> ordenadas por UF como visual geográfico principal, e trata o mapa como
> extra opcional. Isso é decisão de projeto, não limitação técnica.

---

## Modelo de dados

Esquema estrela. Grão do fato: **posto × produto × dia de coleta**.

```
      Dim_Calendario  (735)
             |
Dim_Produto  |  Dim_Geografia
    (3)      |      (419)
       \     |     /
        \    |    /
        Fato_Coleta  (1.053.221)
        /         \
Dim_Bandeira    Dim_Revenda
     (49)         (11.151)

Fato_Evento_Preco (12)  -> Dim_Calendario, Dim_Produto
```

O grão de posto é necessário, não opcional: as medidas de dispersão
(P90−P10, coeficiente de variação) dependem da variância **entre**
postos. Agregar por município destruiria a análise.

Todas as relações são 1:N com **direção de filtro única**. Nenhuma
relação bidirecional — se fosse preciso uma, seria sintoma de erro de
modelagem.

---

## Reproduzir

```bash
pip install -r requirements.txt

python src/step01_download.py      # ~270 MB, alguns minutos
python src/step02_clean.py
python src/step03_build_model.py
python src/step04_analysis.py
python src/step05_validate.py      # gera a suite de testes DAX
python src/step06_dictionary.py
python src/step07_build_pbip.py    # projeto .pbip (TMDL)
```

Cada etapa é idempotente. O download usa cache: rodar de novo não
rebaixa nada.

Depois, um comando carrega o modelo no Power BI Desktop e roda os testes:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\Deploy-Modelo.ps1 -ComTestes
```

O script abre o Desktop, descobre a porta da instância local do Analysis
Services, publica o modelo por XMLA, dispara o refresh e executa a suíte.
Ao final, `Arquivo > Salvar como` grava o `.pbix` e as páginas são
montadas seguindo [`docs/guia-relatorio.md`](docs/guia-relatorio.md).

O caminho manual continua documentado — parâmetro, consultas M, relações
e medidas coladas à mão — em [`docs/guia-relatorio.md`](docs/guia-relatorio.md),
para quem não puder rodar scripts no ambiente.

> **O caminho scriptado não é o caminho corporativo.** Ele usa o cliente
> ADOMD que acompanha o Desktop para falar XMLA com a instância local do
> Analysis Services. Funciona nesta máquina e economiza horas, mas um
> tenant restrito pode bloquear execução de PowerShell ou o acesso ao
> workspace local. **O `.pbix` entregue não depende de nada disso** — uma
> vez salvo, é um arquivo comum. O caminho manual do guia é o que se
> assume disponível em qualquer ambiente.

### Limitação conhecida: o `.pbip` não abre

`step07_build_pbip.py` gera um projeto `.pbip` com o modelo em TMDL.
Nesta máquina, o Power BI Desktop 2.157 **abre em branco ao receber esse
arquivo**, sem mensagem de erro — provavelmente uma opção de recurso de
prévia desativada, que não consegui confirmar sem acesso à interface.

O TMDL gerado não está validado. O TMSL da etapa 8, que descreve o mesmo
modelo, **está**: é o que os 35 testes exercitam. Use
`Deploy-Modelo.ps1` até que a abertura do `.pbip` seja confirmada.

---

## Testes

O modelo semântico é testado, não conferido no olho.

`step05_validate.py` calcula em pandas o valor esperado de cada medida
**e** a consulta DAX que deve produzi-lo, gravando os dois juntos em
`docs/testes-dax.json`. `Invoke-TestesDax.ps1` executa as consultas
contra o modelo carregado e compara.

```
  35 passaram · 0 falharam · 0 com erro
```

| Grupo | Testes | O que prova |
|---|--:|---|
| Contagens | 3 | Carga completa: 1.053.221 linhas, 11.151 postos |
| Preço | 3 | Mediana por produto bate com pandas |
| Dispersão | 3 | P90−P10 bate com pandas |
| **Guarda** | 3 | RR e AC (15 postos) devolvem **BLANK**, SP devolve valor |
| **Paridade** | 8 | Inclui invariância: o mesmo resultado sob filtro de Gasolina, Etanol ou Diesel — prova que `REMOVEFILTERS(Dim_Produto)` funciona |
| Variação | 7 | `ALLSELECTED` delimita o período corretamente |
| Transmissão | 4 | SP 119%, MS 63% reproduzidos em DAX |
| Eventos | 4 | 12 eventos, distribuídos por produto |

Os dois grupos em negrito são os que pegam erro de verdade. A guarda de
amostra e a invariância da paridade dependem de contexto de filtro —
exatamente onde DAX costuma falhar em silêncio, devolvendo um número
plausível e errado.

---

## Qualidade de dados

A etapa 2 contabiliza **toda** linha descartada, por motivo. Um pipeline
que descarta dado em silêncio não é auditável.

| Motivo | Linhas | % |
|---|---:|---:|
| Lidas da fonte | 1.581.448 | 100,00% |
| Produto fora de escopo | 528.221 | 33,40% |
| Unidade incompatível | 0 | 0,00% |
| Data inválida | 0 | 0,00% |
| Preço não numérico | 0 | 0,00% |
| Preço fora da faixa | 0 | 0,00% |
| Coletas duplicadas agregadas | 6 | 0,00% |
| **Retidas** | **1.053.221** | **66,60%** |

O descarte de 33% é **escopo, não sujeira**: Gasolina Aditivada, Diesel
S500, GNV e GLP saem por decisão de projeto — GNV e GLP porque são
vendidos em m³ e por botijão de 13 kg, unidades que não se somam a
R$/litro sem corromper toda média.

A base da ANP chegou notavelmente limpa: zero datas inválidas, zero
preços não numéricos, zero valores fora de faixa plausível.

### Minimização de dados

Endereço, bairro, CEP e CNPJ são descartados **na leitura**, não depois.
O CNPJ é substituído por um hash SHA-256 estável (`ID_Revenda`), que
preserva o grão analítico — dá para contar postos distintos e seguir um
posto ao longo do tempo — sem que o projeto distribua um cadastro
identificável de estabelecimentos.

---

## Limitações

Estão em [`docs/limitacoes.md`](docs/limitacoes.md), e devem ser lidas
antes de qualquer decisão baseada neste relatório. As três que mais
pesam:

- A ANP cobre **419 de ~5.570 municípios (7,5%)**. Isto não é o preço do
  Brasil; é o preço dos municípios pesquisados.
- A coleta **não é ponderada por volume vendido**. "Preço mediano" é o
  preço do posto mediano, não o que o brasileiro mediano pagou.
- A coincidência entre um evento detectado e uma decisão comercial
  **não prova causa**. Este projeto mede o que aconteceu na bomba, não
  por quê.

---

## Fonte

ANP — Série Histórica de Preços de Combustíveis, dados abertos.
<https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos>

Dados públicos. Nenhuma informação interna ou confidencial de qualquer
empresa foi usada neste projeto.
