$ErrorActionPreference = "Stop"

function Assert-Python313 {
  param(
    [Parameter(Mandatory=$true)][string]$Cmd,
    [Parameter(Mandatory=$false)][string[]]$Args = @()
  )
  $ver = & $Cmd @Args -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
  if ($ver -ne "3.13") {
    $cmdShown = ($Cmd + " " + ($Args -join " ")).Trim()
    throw "Se requiere Python 3.13, pero '$cmdShown' devolvió $ver. Instala Python 3.13 o usa 'py -3.13'."
  }
}

Write-Host "==> Activando entorno Python 3.13 (.venv)"

# Preferir el launcher de Windows (py) para fijar la versión
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
  $pythonCmd = "py"
  $pythonArgs = @("-3.13")
} else {
  $pythonCmd = "python"
  $pythonArgs = @()
}

if (-not (Test-Path ".venv")) {
  Write-Host "==> Creando .venv con Python 3.13..."
  Assert-Python313 -Cmd $pythonCmd -Args $pythonArgs
  & $pythonCmd @pythonArgs -m venv .venv
}

Write-Host "==> Activando .venv..."
& .\.venv\Scripts\Activate.ps1

Write-Host "==> Actualizando pip..."
python -m pip install --upgrade pip

Write-Host "==> OK. Python:" (python --version)

