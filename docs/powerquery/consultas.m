// =====================================================================
//  POWER QUERY (M) - Carga do modelo no Power BI Desktop
// =====================================================================
//
//  Cole cada bloco em  Pagina Inicial > Transformar dados > Nova Consulta
//  > Consulta em Branco > Editor Avancado.
//
//  Crie na ordem: o parametro, depois a funcao, depois as tabelas.
//
//  NOTA SOBRE SEPARADOR DECIMAL
//  Os CSVs originais da ANP usam virgula decimal e exigem
//  Culture="pt-BR". Os arquivos em data/processed sao gravados pelo
//  pipeline Python com ponto decimal, entao exigem Culture="en-US".
//  Trocar as duas e o erro classico: os precos viram valores 100x
//  maiores ou nulos, em silencio. Por isso a cultura e sempre
//  declarada de forma explicita, nunca deixada para inferencia.
// =====================================================================


// ---------------------------------------------------------------------
//  1. PARAMETRO   ->  nome: pCaminhoDados   (tipo Texto)
// ---------------------------------------------------------------------
//  Gerenciar Parametros > Novo. Valor atual, por exemplo:
//      C:\Users\Luvas\petrobras-anp-powerbi\data\processed
//
//  Motivo: o caminho absoluto fica num unico lugar. Quem abrir o .pbix
//  em outra maquina troca um campo, nao oito consultas.
// ---------------------------------------------------------------------


// ---------------------------------------------------------------------
//  2. FUNCAO   ->  nome: fnCarregarCsv
// ---------------------------------------------------------------------
let
    fnCarregarCsv = (nomeArquivo as text) as table =>
        let
            Caminho = pCaminhoDados & "\" & nomeArquivo & ".csv",

            Conteudo = Csv.Document(
                File.Contents(Caminho),
                [
                    Delimiter  = ",",
                    Encoding   = 65001,          // UTF-8 com BOM
                    QuoteStyle = QuoteStyle.Csv
                ]
            ),

            Promovido = Table.PromoteHeaders(Conteudo, [PromoteAllScalars = true])
        in
            Promovido
in
    fnCarregarCsv


// ---------------------------------------------------------------------
//  3. Dim_Calendario
// ---------------------------------------------------------------------
//  Apos carregar: Modelagem > Marcar como Tabela de Datas > coluna Data.
//  Sem esse passo, DATEADD e DATESINPERIOD ficam nao confiaveis.
let
    Origem = fnCarregarCsv("Dim_Calendario"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"Data",               type date},
            {"Ano",                Int64.Type},
            {"Mes",                Int64.Type},
            {"NomeMes",            type text},
            {"AnoMes",             Int64.Type},
            {"AnoMesNome",         type text},
            {"Trimestre",          type text},
            {"AnoTrimestre",       type text},
            {"SemanaISO",          Int64.Type},
            {"AnoSemanaISO",       Int64.Type},
            {"InicioSemana",       type date},
            {"DiaSemanaNum",       Int64.Type},
            {"NomeDiaSemana",      type text},
            {"EhFimDeSemana",      type logical},
            {"DiasUteisComDados",  Int64.Type},
            {"EhSemanaCompleta",   type logical}
        },
        "en-US"
    )
in
    Tipos


// ---------------------------------------------------------------------
//  4. Dim_Produto
// ---------------------------------------------------------------------
let
    Origem = fnCarregarCsv("Dim_Produto"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"SK_Produto",  Int64.Type},
            {"Produto",     type text},
            {"NomeProduto", type text},
            {"Origem",      type text},
            {"Unidade",     type text}
        },
        "en-US"
    )
in
    Tipos


// ---------------------------------------------------------------------
//  5. Dim_Geografia
// ---------------------------------------------------------------------
let
    Origem = fnCarregarCsv("Dim_Geografia"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"SK_Municipio",  Int64.Type},
            {"Regiao",        type text},
            {"UF",            type text},
            {"Municipio",     type text},
            {"NomeRegiao",    type text},
            {"UF_Municipio",  type text}
        },
        "en-US"
    )
in
    Tipos


// ---------------------------------------------------------------------
//  6. Dim_Bandeira
// ---------------------------------------------------------------------
let
    Origem = fnCarregarCsv("Dim_Bandeira"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"SK_Bandeira",      Int64.Type},
            {"Bandeira",         type text},
            {"GrupoBandeira",    type text},
            {"EhBandeiraBranca", type logical}
        },
        "en-US"
    )
in
    Tipos


// ---------------------------------------------------------------------
//  7. Dim_Revenda
// ---------------------------------------------------------------------
let
    Origem = fnCarregarCsv("Dim_Revenda"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"SK_Revenda",  Int64.Type},
            {"ID_Revenda",  type text},
            {"NomeRevenda", type text}
        },
        "en-US"
    )
in
    Tipos


// ---------------------------------------------------------------------
//  8. Fato_Coleta   (~1,05 milhao de linhas)
// ---------------------------------------------------------------------
//  Os tipos sao definidos coluna a coluna, nunca por deteccao
//  automatica: a deteccao le apenas as primeiras 200 linhas e pode
//  classificar Preco como inteiro se o inicio do arquivo nao tiver
//  centavos.
let
    Origem = fnCarregarCsv("Fato_Coleta"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"Data",         type date},
            {"SK_Produto",   Int64.Type},
            {"SK_Municipio", Int64.Type},
            {"SK_Bandeira",  Int64.Type},
            {"SK_Revenda",   Int64.Type},
            {"Preco",        type number}
        },
        "en-US"
    ),

    // Rede de seguranca: o pipeline Python ja garante isso, mas a carga
    // falha alto se algum dia deixar de garantir.
    SemNulos = Table.SelectRows(Tipos, each [Preco] <> null and [Data] <> null)
in
    SemNulos


// ---------------------------------------------------------------------
//  9. Fato_Evento_Preco
// ---------------------------------------------------------------------
let
    Origem = fnCarregarCsv("Fato_Evento_Preco"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"SK_Evento",   Int64.Type},
            {"Data",        type date},
            {"SK_Produto",  Int64.Type},
            {"NomeProduto", type text},
            {"PrecoAntes",  type number},
            {"PrecoDepois", type number},
            {"DeltaRS",     type number},
            {"DeltaPct",    type number},
            {"ZRobusto",    type number},
            {"Direcao",     type text}
        },
        "en-US"
    ),
    // NomeProduto ja existe em Dim_Produto. Manter as duas criaria
    // ambiguidade no modelo; a relacao e por SK_Produto.
    Final = Table.RemoveColumns(Tipos, {"NomeProduto"})
in
    Final


// ---------------------------------------------------------------------
//  10. Aux_Paridade_UF_Semana   -  OPCIONAL
// ---------------------------------------------------------------------
//  Tabela auxiliar com a paridade ja calculada em Python. Serve para
//  conferir o resultado do DAX, nao para alimentar o relatorio.
//  Mantenha "Habilitar carga" DESMARCADO no .pbix final: o relatorio
//  deve calcular a paridade em DAX, no contexto do filtro do usuario.
let
    Origem = fnCarregarCsv("Aux_Paridade_UF_Semana"),
    Tipos = Table.TransformColumnTypes(
        Origem,
        {
            {"UF",             type text},
            {"InicioSemana",   type date},
            {"Etanol",         type number},
            {"Gasolina",       type number},
            {"Paridade",       type number},
            {"EtanolCompensa", type logical}
        },
        "en-US"
    )
in
    Tipos
