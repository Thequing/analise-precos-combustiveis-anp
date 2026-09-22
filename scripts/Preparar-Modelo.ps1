<#
.SYNOPSIS
    Prepara o modelo no Power BI Desktop depois que os CSVs ja foram
    importados pela interface: corrige tipos, remove as tabelas de data
    automaticas, cria relacoes e publica as 43 medidas.

.DESCRIPTION
    Este e o caminho que FUNCIONA de ponta a ponta.

    O Desktop so consegue salvar um .pbix de um modelo que ele mesmo
    criou. Injetar o modelo inteiro por XMLA carrega e ate passa nos
    testes, mas o "Salvar como" trava para sempre. Entao:

      1. VOCE importa os 7 CSVs pela interface (Obter dados > Texto/CSV)
      2. este script ajusta o modelo por TOM, que e edicao granular -
         o Desktop continua dono do modelo e salva normalmente
      3. os 35 testes rodam
      4. voce salva com Ctrl+S

    O que ele corrige, e por que:

      - Preco vem como Int64 e a cultura do Power Query fica em pt-BR,
        entao "6.29" e lido como 629 (ponto tratado como separador de
        milhar). Corrige o tipo da coluna E fixa a cultura em en-US.
      - AnoMesNome ("Set/24") e detectado como data. Forca texto.
      - A Data/hora automatica cria 6 tabelas ocultas e 5 relacoes
        inuteis. Remove, junto das Variations que as referenciam - sem
        remover as Variations antes, o SaveChanges falha.
      - O Desktop acerta 5 das 7 relacoes; cria as 2 de data que faltam.
      - Marca Dim_Calendario como tabela de datas.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Preparar-Modelo.ps1 -ComTestes
#>
[CmdletBinding()]
param([switch] $ComTestes)

$ErrorActionPreference = 'Stop'
$raizScripts = Split-Path -Parent $PSCommandPath
$raiz = Split-Path -Parent $raizScripts
$bin = "$env:ProgramFiles\Microsoft Power BI Desktop\bin"

# --- localizar a instancia local ------------------------------------------
$ws = "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"
$pf = Get-ChildItem "$ws\*\Data\msmdsrv.port.txt" -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $pf) {
    Write-Host "Power BI Desktop nao esta aberto com um arquivo." -ForegroundColor Red
    Write-Host "Importe antes os 7 CSVs de data\processed via Obter dados > Texto/CSV."
    exit 2
}
$porta = (Get-Content $pf.FullName -Encoding Unicode -Raw).Trim([char]0xFEFF,' ',"`r","`n")

$tomAsm = [Reflection.Assembly]::LoadFrom("$bin\Microsoft.AnalysisServices.Server.Tabular.dll")
[void][Reflection.Assembly]::LoadFrom("$bin\Microsoft.AnalysisServices.Server.Core.dll")
$srv = New-Object -TypeName Microsoft.AnalysisServices.Tabular.Server
$srv.Connect("localhost:$porta")
$mdl = $srv.Databases[0].Model

Write-Host ""
Write-Host "Preparando o modelo (porta $porta)" -ForegroundColor Cyan
Write-Host "  inicial: $($mdl.Tables.Count) tabelas, $($mdl.Relationships.Count) relacoes, " -NoNewline
Write-Host "$(($mdl.Tables | ForEach-Object { $_.Measures.Count } | Measure-Object -Sum).Sum) medidas"

$esperadas = @("Dim_Calendario","Dim_Produto","Dim_Geografia","Dim_Bandeira",
               "Dim_Revenda","Fato_Coleta","Fato_Evento_Preco")
$faltando = $esperadas | Where-Object { -not $mdl.Tables.Contains($_) }
if ($faltando) {
    Write-Host "  Faltam tabelas: $($faltando -join ', ')" -ForegroundColor Red
    Write-Host "  Importe os 7 CSVs antes de rodar este script."
    $srv.Disconnect(); exit 2
}

$dtType  = $tomAsm.GetType("Microsoft.AnalysisServices.Tabular.DataType")
$aggType = $tomAsm.GetType("Microsoft.AnalysisServices.Tabular.AggregateFunction")
$cardType= $tomAsm.GetType("Microsoft.AnalysisServices.Tabular.RelationshipEndCardinality")
$cfbType = $tomAsm.GetType("Microsoft.AnalysisServices.Tabular.CrossFilteringBehavior")
$rtType  = $tomAsm.GetType("Microsoft.AnalysisServices.Tabular.RefreshType")
$dbl     = [Enum]::Parse($dtType,"Double")
$nenhum  = [Enum]::Parse($aggType,"None")

# --- 1. data/hora automatica ----------------------------------------------
if ($mdl.Annotations.Contains("__PBI_TimeIntelligenceEnabled")) {
    $mdl.Annotations["__PBI_TimeIntelligenceEnabled"].Value = "0"
}
$nVar = 0
foreach ($tbl in $mdl.Tables) {
    foreach ($col in $tbl.Columns) {
        if ($col.Variations -and $col.Variations.Count -gt 0) {
            @($col.Variations) | ForEach-Object { [void]$col.Variations.Remove($_); $nVar++ }
        }
    }
}
$autoTbl = @($mdl.Tables | Where-Object { $_.Name -like "LocalDateTable_*" -or $_.Name -like "DateTableTemplate_*" })
$autoRel = @($mdl.Relationships | Where-Object { $autoTbl.Name -contains $_.FromTable.Name -or $autoTbl.Name -contains $_.ToTable.Name })
foreach ($rr in $autoRel) { [void]$mdl.Relationships.Remove($rr) }
foreach ($tt in $autoTbl) { [void]$mdl.Tables.Remove($tt) }
Write-Host "  [1] data/hora automatica: $nVar variations, $($autoRel.Count) relacoes, $($autoTbl.Count) tabelas removidas"

# --- 2. tipos e cultura ---------------------------------------------------
$cal = $mdl.Tables["Dim_Calendario"]
$pc = $cal.Partitions[0]
$pc.Source.Expression = $pc.Source.Expression.Replace('{"AnoMesNome", type date}', '{"AnoMesNome", type text}')

$pf2 = $mdl.Tables["Fato_Coleta"].Partitions[0]
$pf2.Source.Expression = $pf2.Source.Expression.Replace('{"Preco", Int64.Type}})', '{"Preco", type number}}, "en-US")')

$pe = $mdl.Tables["Fato_Evento_Preco"].Partitions[0]
$e2 = $pe.Source.Expression
foreach ($c in @("PrecoAntes","PrecoDepois","DeltaRS","DeltaPct","ZRobusto")) {
    $e2 = $e2.Replace("{`"$c`", Int64.Type}", "{`"$c`", type number}")
}
$pe.Source.Expression = $e2.Replace('{"Direcao", type text}})', '{"Direcao", type text}}, "en-US")')

# O tipo no M nao basta: se a coluna do modelo continuar Int64, o valor
# e truncado na carga (6,29 vira 6).
$mdl.Tables["Fato_Coleta"].Columns["Preco"].DataType = $dbl
foreach ($c in @("PrecoAntes","PrecoDepois","DeltaRS","DeltaPct","ZRobusto")) {
    $mdl.Tables["Fato_Evento_Preco"].Columns[$c].DataType = $dbl
}
Write-Host "  [2] tipos decimais e cultura en-US corrigidos"

# --- 3. tabela de datas ---------------------------------------------------
$cal.DataCategory = "Time"
$cal.Columns["Data"].IsKey = $true
Write-Host "  [3] Dim_Calendario marcada como tabela de datas"

# --- 4. relacoes de data --------------------------------------------------
$nRel = 0
foreach ($ft in @("Fato_Coleta","Fato_Evento_Preco")) {
    if ($mdl.Relationships | Where-Object { $_.FromTable.Name -eq $ft -and $_.FromColumn.Name -eq "Data" }) { continue }
    $nr = New-Object -TypeName Microsoft.AnalysisServices.Tabular.SingleColumnRelationship
    $nr.Name = "${ft}_Data_to_Dim_Calendario_Data"
    $nr.FromColumn = $mdl.Tables[$ft].Columns["Data"]
    $nr.ToColumn   = $cal.Columns["Data"]
    $nr.FromCardinality = [Enum]::Parse($cardType,"Many")
    $nr.ToCardinality   = [Enum]::Parse($cardType,"One")
    $nr.CrossFilteringBehavior = [Enum]::Parse($cfbType,"OneDirection")
    $nr.IsActive = $true
    $mdl.Relationships.Add($nr)
    $nRel++
}
Write-Host "  [4] $nRel relacoes de data criadas (total $($mdl.Relationships.Count))"

# --- 5. medidas -----------------------------------------------------------
& python (Join-Path $raiz "src\step10_export_medidas.py") | Out-Null
$meds = Get-Content (Join-Path $raiz "outputs\medidas.json") -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $mdl.Tables.Contains("_Medidas")) {
    $tm = New-Object -TypeName Microsoft.AnalysisServices.Tabular.Table
    $tm.Name = "_Medidas"
    $cm = New-Object -TypeName Microsoft.AnalysisServices.Tabular.DataColumn
    $cm.Name = "Coluna1"; $cm.DataType = [Enum]::Parse($dtType,"String")
    $cm.SourceColumn = "Coluna1"; $cm.IsHidden = $true
    $tm.Columns.Add($cm)
    $pm = New-Object -TypeName Microsoft.AnalysisServices.Tabular.Partition
    $pm.Name = "_Medidas"
    $ms = New-Object -TypeName Microsoft.AnalysisServices.Tabular.MPartitionSource
    $ms.Expression = "let`n    Origem = Table.FromRows({}, type table [Coluna1 = text])`nin`n    Origem"
    $pm.Source = $ms
    $tm.Partitions.Add($pm)
    $mdl.Tables.Add($tm)
} else { $tm = $mdl.Tables["_Medidas"] }

$novas = 0
foreach ($md in $meds) {
    if ($tm.Measures.Contains($md.nome)) { $obj = $tm.Measures[$md.nome] }
    else {
        $obj = New-Object -TypeName Microsoft.AnalysisServices.Tabular.Measure
        $obj.Name = $md.nome; $tm.Measures.Add($obj); $novas++
    }
    $obj.Expression = $md.expr
    if ($md.formato) { $obj.FormatString = $md.formato }
    if ($md.pasta)   { $obj.DisplayFolder = $md.pasta }
}
Write-Host "  [5] medidas: $($meds.Count) aplicadas ($novas novas)"

# --- 6. higiene de colunas ------------------------------------------------
$ocultar = @("SK_Produto","SK_Municipio","SK_Bandeira","SK_Revenda","SK_Evento",
             "ID_Revenda","DiaSemanaNum","AnoMes","AnoSemanaISO","DiasUteisComDados","Produto")
foreach ($tbl in $mdl.Tables) {
    foreach ($col in $tbl.Columns) {
        if ($col.Name -like "RowNumber*") { continue }
        if ($ocultar -contains $col.Name) { $col.IsHidden = $true }
        if ($col.Name -like "SK_*" -or $col.Name -in @("Ano","Mes","AnoMes","SemanaISO","AnoSemanaISO","DiaSemanaNum","DiasUteisComDados")) {
            $col.SummarizeBy = $nenhum
        }
    }
}
$mdl.Tables["Fato_Evento_Preco"].Columns["NomeProduto"].IsHidden = $true
$mdl.Tables["Fato_Coleta"].Columns["Data"].IsHidden = $true
$mdl.Tables["Fato_Coleta"].Columns["Preco"].FormatString = '"R$ "#,0.000'
$mdl.Tables["Fato_Coleta"].Columns["Preco"].SummarizeBy = $nenhum
$cal.Columns["NomeMes"].SortByColumn       = $cal.Columns["Mes"]
$cal.Columns["AnoMesNome"].SortByColumn    = $cal.Columns["AnoMes"]
$cal.Columns["NomeDiaSemana"].SortByColumn = $cal.Columns["DiaSemanaNum"]
Write-Host "  [6] colunas ocultas, formatos e ordenacao aplicados"

try { $mdl.SaveChanges() | Out-Null }
catch { Write-Host "FALHA ao salvar: $($_.Exception.Message.Split([char]10)[0])" -ForegroundColor Red; $srv.Disconnect(); exit 1 }

Write-Host "  refresh completo..." -NoNewline
$sw = [Diagnostics.Stopwatch]::StartNew()
$mdl.RequestRefresh([Enum]::Parse($rtType,"Full"))
try { $mdl.SaveChanges() | Out-Null; Write-Host " $([int]$sw.Elapsed.TotalSeconds)s" -ForegroundColor Green }
catch { Write-Host ""; Write-Host "FALHA no refresh: $($_.Exception.Message.Split([char]10)[0])" -ForegroundColor Red; $srv.Disconnect(); exit 1 }
$srv.Disconnect()

if ($ComTestes) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $raizScripts "Invoke-TestesDax.ps1") -Porta $porta
    $rc = $LASTEXITCODE
} else { $rc = 0 }

Write-Host ""
Write-Host "Modelo pronto. Agora no Power BI Desktop:" -ForegroundColor Green
Write-Host "  1. Ctrl+S para salvar o .pbix"
Write-Host "  2. Exibicao > Temas > Procurar temas > docs\tema-anp.json"
Write-Host "  3. Monte as paginas seguindo docs\guia-relatorio.md"
exit $rc
