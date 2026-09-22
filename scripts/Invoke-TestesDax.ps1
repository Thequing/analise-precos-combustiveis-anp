<#
.SYNOPSIS
    Executa a suite de testes DAX contra o modelo aberto no Power BI Desktop.

.DESCRIPTION
    O Power BI Desktop sobe uma instancia local do Analysis Services para
    cada arquivo aberto. Este script descobre a porta dessa instancia,
    conecta via ADOMD e executa cada consulta de docs/testes-dax.json,
    comparando com o valor calculado em pandas na etapa 5.

    Pre-requisito: ter o .pbip aberto no Power BI Desktop, com os dados
    ja carregados.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Invoke-TestesDax.ps1
#>
[CmdletBinding()]
param(
    [string] $ArquivoTestes,
    [string] $Porta,
    [switch] $Detalhado
)

$ErrorActionPreference = 'Stop'

# $PSScriptRoot nao esta disponivel no valor padrao de um parametro no
# PowerShell 5.1 - resolver aqui, ja no corpo do script.
if (-not $ArquivoTestes) {
    $raiz = Split-Path -Parent $PSCommandPath
    $ArquivoTestes = Join-Path (Split-Path -Parent $raiz) "docs\testes-dax.json"
}
if (-not (Test-Path $ArquivoTestes)) {
    Write-Host "Arquivo de testes nao encontrado: $ArquivoTestes" -ForegroundColor Red
    Write-Host "Rode antes:  python src\step05_validate.py"
    exit 2
}

# --- Localizar a instancia do Analysis Services ---------------------------
if (-not $Porta) {
    $ws = "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"
    $pf = Get-ChildItem "$ws\*\Data\msmdsrv.port.txt" -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $pf) {
        Write-Host "Nenhuma instancia do Power BI Desktop encontrada." -ForegroundColor Red
        Write-Host "Abra powerbi\PrecosCombustiveisANP.pbip antes de rodar os testes."
        exit 2
    }
    $Porta = (Get-Content $pf.FullName -Encoding Unicode -Raw).Trim([char]0xFEFF, ' ', "`r", "`n")
}

# --- Carregar ADOMD -------------------------------------------------------
# A DLL se chama Microsoft.PowerBI.AdomdClient.dll mas o namespace e
# Microsoft.AnalysisServices.AdomdClient. New-Object resolve em tempo de
# execucao, evitando o binding em tempo de parse do PowerShell 5.1.
$dll = "$env:ProgramFiles\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
if (-not (Test-Path $dll)) { Write-Host "ADOMD nao encontrado: $dll" -ForegroundColor Red; exit 2 }
[void][Reflection.Assembly]::LoadFrom($dll)

$conn = New-Object -TypeName Microsoft.AnalysisServices.AdomdClient.AdomdConnection `
                   -ArgumentList "Data Source=localhost:$Porta"
$conn.Open()

$spec   = Get-Content $ArquivoTestes -Raw -Encoding UTF8 | ConvertFrom-Json
$testes = $spec.testes

Write-Host ""
Write-Host "Suite de testes DAX" -ForegroundColor Cyan
Write-Host "  modelo   : $($conn.Database.Name)"
Write-Host "  porta    : $Porta"
Write-Host "  testes   : $($testes.Count)"
Write-Host ""

$passou = 0; $falhou = 0; $erro = 0
$falhas = @()
$grupoAtual = ""

foreach ($t in $testes) {
    if ($t.grupo -ne $grupoAtual) {
        $grupoAtual = $t.grupo
        Write-Host "  $grupoAtual" -ForegroundColor DarkCyan
    }

    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $t.dax
        $rdr = $cmd.ExecuteReader()
        $obtido = $null
        if ($rdr.Read()) { $obtido = $rdr.GetValue(0) }
        $rdr.Close()
        if ($obtido -is [System.DBNull]) { $obtido = $null }
    }
    catch {
        $erro++
        Write-Host ("    ERRO  {0}" -f $t.nome) -ForegroundColor Magenta
        Write-Host ("          {0}" -f $_.Exception.Message.Split("`n")[0]) -ForegroundColor DarkGray
        $falhas += [pscustomobject]@{ Teste = $t.nome; Esperado = $t.esperado; Obtido = "ERRO"; Detalhe = $_.Exception.Message.Split("`n")[0] }
        continue
    }

    $esperado = $t.esperado

    # BLANK esperado: a guarda de amostra minima precisa devolver vazio.
    if ($null -eq $esperado) {
        if ($null -eq $obtido) {
            $passou++
            Write-Host ("    ok    {0}  = BLANK" -f $t.nome) -ForegroundColor DarkGreen
        } else {
            $falhou++
            Write-Host ("    FALHA {0}  esperado BLANK, obtido {1}" -f $t.nome, $obtido) -ForegroundColor Red
            $falhas += [pscustomobject]@{ Teste = $t.nome; Esperado = "BLANK"; Obtido = $obtido; Detalhe = $t.nota }
        }
        continue
    }

    if ($null -eq $obtido) {
        $falhou++
        Write-Host ("    FALHA {0}  esperado {1}, obtido BLANK" -f $t.nome, $esperado) -ForegroundColor Red
        $falhas += [pscustomobject]@{ Teste = $t.nome; Esperado = $esperado; Obtido = "BLANK"; Detalhe = $t.nota }
        continue
    }

    $dif = [Math]::Abs([double]$obtido - [double]$esperado)
    if ($dif -le [double]$t.tolerancia) {
        $passou++
        if ($Detalhado) {
            Write-Host ("    ok    {0}  = {1:N4}" -f $t.nome, [double]$obtido) -ForegroundColor DarkGreen
        } else {
            Write-Host ("    ok    {0}" -f $t.nome) -ForegroundColor DarkGreen
        }
    } else {
        $falhou++
        Write-Host ("    FALHA {0}" -f $t.nome) -ForegroundColor Red
        Write-Host ("          esperado {0:N6}, obtido {1:N6}, dif {2:N6} (tol {3})" -f `
                    [double]$esperado, [double]$obtido, $dif, $t.tolerancia) -ForegroundColor DarkGray
        $falhas += [pscustomobject]@{ Teste = $t.nome; Esperado = [double]$esperado; Obtido = [double]$obtido; Detalhe = "dif $($dif.ToString('N6'))" }
    }
}

$conn.Close()

Write-Host ""
Write-Host ("  {0} passaram · {1} falharam · {2} com erro" -f $passou, $falhou, $erro) `
    -ForegroundColor $(if ($falhou -eq 0 -and $erro -eq 0) { 'Green' } else { 'Red' })
Write-Host ""

if ($falhas.Count) {
    Write-Host "Resumo das falhas:" -ForegroundColor Yellow
    $falhas | Format-Table -AutoSize | Out-String -Width 200 | Write-Host
}

if ($falhou -eq 0 -and $erro -eq 0) { exit 0 } else { exit 1 }
