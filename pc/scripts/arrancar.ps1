# Arranca el backend del PIA (http://127.0.0.1:8000). Con -CargarFirmware primero carga esp32dev.
# Uso (desde la raíz del repo):
#   & .\pc\scripts\arrancar.ps1                        solo el backend
#   & .\pc\scripts\arrancar.ps1 -CargarFirmware        firmware principal y luego el backend (mantén BOOT)
param(
    [switch]$CargarFirmware,
    [string]$Puerto = "COM4"
)
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $raiz
if ($CargarFirmware) {
    & (Join-Path $PSScriptRoot "prueba_modulo.ps1") -Entorno esp32dev -Puerto $Puerto -SinMonitor
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
Set-Location (Join-Path $raiz "pc")
& (Join-Path $raiz ".venv\Scripts\python.exe") -m pia
