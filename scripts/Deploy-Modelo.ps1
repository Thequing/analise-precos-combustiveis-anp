<#
.SYNOPSIS
    Publica o modelo semantico numa instancia do Power BI Desktop e
    opcionalmente roda a suite de testes DAX.

.DESCRIPTION
    O Power BI Desktop sobe uma instancia local do Analysis Services para
    cada arquivo aberto. Este script:

      1. abre o Desktop com um arquivo em branco (ou usa um ja aberto)
      2. descobre a porta da instancia local
      3. gera o TMSL do modelo (etapa 8) para o ID daquele banco
      4. envia createOrReplace por XMLA
      5. dispara um refresh completo (importa os CSVs)
      6. roda os testes, se -ComTestes

    Ao final, o modelo esta carregado no Desktop: basta  Arquivo >
    Salvar como  para gravar o .pbix e comecar a montar as paginas
    seguindo docs/guia-relatorio.md.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\Deploy-Modelo.ps1 -ComTestes
#>
[CmdletBinding()]
param(
    [switch] $ComTestes,
    [switch] $UsarInstanciaAberta
)

$ErrorActionPreference = 'Stop'
$raizScripts = Split-Path -Parent $PSCommandPath
$raiz = Split-Path -Parent $raizScripts
$ws = "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"
$exe = "$env:ProgramFiles\Microsoft Power BI Desktop\bin\PBIDesktop.exe"
$dll = "$env:ProgramFiles\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"

foreach ($p in @($exe, $dll)) {
    if (-not (Test-Path $p)) { Write-Host "Nao encontrado: $p" -ForegroundColor Red; exit 2 }
}

# --- 1. Instancia --------------------------------------------------------
$proc = Get-Process PBIDesktop -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "Abrindo o Power BI Desktop..." -ForegroundColor Cyan
    Start-Process $exe
} elseif (-not $UsarInstanciaAberta) {
    Write-Host "Ja existe um Power BI Desktop aberto." -ForegroundColor Yellow
    Write-Host "O modelo sera publicado NELE, substituindo o que estiver carregado."
    Write-Host "Use -UsarInstanciaAberta para confirmar, ou feche o Desktop antes."
    exit 2
}

Write-Host "Aguardando o Analysis Services local..." -NoNewline
$porta = $null
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 3
    $pf = Get-ChildItem "$ws\*\Data\msmdsrv.port.txt" -ErrorAction SilentlyContinue |
          Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($pf) {
        $porta = (Get-Content $pf.FullName -Encoding Unicode -Raw).Trim([char]0xFEFF, ' ', "`r", "`n")
        if ($porta) { break }
    }
    Write-Host "." -NoNewline
}
if (-not $porta) { Write-Host ""; Write-Host "A instancia nao subiu." -ForegroundColor Red; exit 2 }
Write-Host " porta $porta" -ForegroundColor Green

# --- 2. Conectar e descobrir o banco -------------------------------------
[void][Reflection.Assembly]::LoadFrom($dll)
$conn = New-Object -TypeName Microsoft.AnalysisServices.AdomdClient.AdomdConnection `
                   -ArgumentList "Data Source=localhost:$porta"
$conn.Open()
$cmd = $conn.CreateCommand()
$cmd.CommandText = "SELECT [CATALOG_NAME] FROM `$SYSTEM.DBSCHEMA_CATALOGS"
$r = $cmd.ExecuteReader()
$db = $null; if ($r.Read()) { $db = $r.GetValue(0) }
$r.Close(); $conn.Close()
if (-not $db) { Write-Host "Nenhum banco na instancia." -ForegroundColor Red; exit 2 }
Write-Host "Banco: $db"

# --- 3. Gerar o TMSL para esse banco -------------------------------------
Write-Host "Gerando TMSL..." -ForegroundColor Cyan
& python (Join-Path $raiz "src\step08_tmsl.py") $db
if ($LASTEXITCODE -ne 0) { Write-Host "Falha ao gerar o TMSL." -ForegroundColor Red; exit 1 }

# --- 4. Publicar ----------------------------------------------------------
$conn = New-Object -TypeName Microsoft.AnalysisServices.AdomdClient.AdomdConnection `
                   -ArgumentList "Data Source=localhost:$porta;Catalog=$db"
$conn.Open()

Write-Host "Publicando o modelo (createOrReplace)..." -ForegroundColor Cyan
$c = $conn.CreateCommand(); $c.CommandTimeout = 1800
$c.CommandText = Get-Content (Join-Path $raiz "outputs\modelo.tmsl") -Raw -Encoding UTF8
try { [void]$c.ExecuteNonQuery() }
catch { Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red; $conn.Close(); exit 1 }

Write-Host "Refresh completo (importando os CSVs)..." -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()
$c2 = $conn.CreateCommand(); $c2.CommandTimeout = 3600
$c2.CommandText = '{"refresh":{"type":"full","objects":[{"database":"' + $db + '"}]}}'
try { [void]$c2.ExecuteNonQuery() }
catch { Write-Host "ERRO no refresh: $($_.Exception.Message)" -ForegroundColor Red; $conn.Close(); exit 1 }

$c3 = $conn.CreateCommand()
$c3.CommandText = 'EVALUATE ROW("l", COUNTROWS(Fato_Coleta), "p", DISTINCTCOUNT(Fato_Coleta[SK_Revenda]))'
$r3 = $c3.ExecuteReader()
if ($r3.Read()) {
    Write-Host ("  {0:N0} linhas, {1:N0} postos, {2}s" -f `
                [double]$r3.GetValue(0), [double]$r3.GetValue(1), [int]$sw.Elapsed.TotalSeconds) -ForegroundColor Green
}
$r3.Close(); $conn.Close()

# --- 5. Testes ------------------------------------------------------------
if ($ComTestes) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $raizScripts "Invoke-TestesDax.ps1") -Porta $porta
    $rc = $LASTEXITCODE
} else { $rc = 0 }

Write-Host ""
Write-Host "Modelo carregado no Power BI Desktop." -ForegroundColor Green
Write-Host "Proximo passo: Arquivo > Salvar como > Precos-Combustiveis-ANP.pbix"
Write-Host "Depois monte as paginas seguindo docs\guia-relatorio.md"
exit $rc
