# Prepara una PC (Windows) para correr el PIA desde cero, después de clonar o hacer pull.
# Uso (desde la raíz del repo, en PowerShell):
#   & .\pc\scripts\instalar.ps1                                  entorno, datasets y config.toml
#   & .\pc\scripts\instalar.ps1 -Respaldo D:\pia_20261114.zip    además restaura usuarios, calibraciones y banco
#   & .\pc\scripts\instalar.ps1 -Probar                          además corre las pruebas (pytest)
# Es seguro correrlo varias veces: lo que ya está no se vuelve a hacer.
param(
    [string]$Respaldo = "",
    [switch]$Probar
)
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $raiz
function Paso($t) { Write-Host "`n== $t ==" -ForegroundColor Cyan }

Paso "1. Python"
$py = $null
foreach ($v in @("3.14", "3.13", "3.12")) {
    try { & py "-$v" --version *> $null; if ($LASTEXITCODE -eq 0) { $py = @("py", "-$v"); break } } catch {}
}
if (-not $py) { Write-Host "No encontré Python 3.12-3.14. Instálalo desde python.org (marca 'Add to PATH')." -ForegroundColor Red; exit 1 }
Write-Host "Usando $($py -join ' ')"

Paso "2. Entorno virtual y dependencias (.venv)"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $py[0] $py[1] -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -q -r pc\requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Falló pip install." -ForegroundColor Red; exit 1 }
Write-Host "Dependencias listas."

Paso "3. Datasets públicos (ORL y FVC2002, ~25 MB de descarga)"
& .\.venv\Scripts\python.exe pc\scripts\descargar_datasets.py
if ($LASTEXITCODE -ne 0) { Write-Host "Algún dataset no bajó: el script dice dónde dejar el ZIP a mano." -ForegroundColor Yellow }

Paso "4. Datos del proyecto (usuarios, calibraciones, banco)"
if ($Respaldo) {
    if (-not (Test-Path $Respaldo)) { Write-Host "No existe $Respaldo" -ForegroundColor Red; exit 1 }
    & .\.venv\Scripts\python.exe pc\scripts\respaldo.py restaurar $Respaldo
    Write-Host "Respaldo restaurado (incluye config.toml si esta PC no tenía uno)."
} elseif (-not (Test-Path "datos\pia.db")) {
    Write-Host "Sin respaldo: se siembra solo el modo Simular (usuarios de prueba 07 y 12)." -ForegroundColor Yellow
    & .\.venv\Scripts\python.exe pc\scripts\sembrar_simular.py
} else {
    Write-Host "Ya hay datos\pia.db: no se toca."
}

Paso "5. config.toml"
if (-not (Test-Path "config.toml")) { Copy-Item config.ejemplo.toml config.toml; Write-Host "Copiado de config.ejemplo.toml." }
else { Write-Host "Ya existe config.toml (no se pisa)." }
Write-Host "Revisa [camara].url con la IP que muestra IP Webcam en el celular:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\python.exe pc\scripts\probar_camara.py --url http://<IP>:8080/video --guardar-url"

Paso "6. Herramientas del firmware"
$pio = "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe"
if (Test-Path $pio) { Write-Host "PlatformIO encontrado." }
else { Write-Host "Falta PlatformIO: instala VS Code y la extensión 'PlatformIO IDE' (la primera compilación baja el resto)." -ForegroundColor Yellow }
$ch340 = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.FriendlyName -match "CH340|CP210" }
if ($ch340) { Write-Host "Puerto del ESP32: $($ch340.FriendlyName -join ', ')" }
else { Write-Host "No veo el ESP32 (CH340). Conéctalo; si no aparece en 'Puertos (COM y LPT)', instala el driver CH340." -ForegroundColor Yellow }

if ($Probar) {
    Paso "7. Pruebas"
    & .\.venv\Scripts\python.exe -m pytest pc\tests -q -p no:warnings
}

Paso "Listo"
Write-Host "Arranca con:  & .\pc\scripts\arrancar.ps1   (y abre http://127.0.0.1:8000)"
Write-Host "Si la placa no tiene el firmware principal:  & .\pc\scripts\arrancar.ps1 -CargarFirmware -Puerto COM4  (mantén BOOT)"
