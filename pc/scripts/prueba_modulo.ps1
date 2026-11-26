# P4: carga un entorno de prueba del firmware y abre el monitor serie.
# Uso (desde la raíz del repo):  & .\pc\scripts\prueba_modulo.ps1 -Entorno test_oled -Puerto COM4
# Con esta placa hay que mantener BOOT cuando aparece "Connecting...". Ctrl+C cierra el monitor.
param(
    [Parameter(Mandatory = $true)][ValidateSet("test_teclado", "test_teclado_crudo", "test_oled", "test_leds", "test_servos", "test_huella_imagen", "esp32dev")]
    [string]$Entorno,
    [string]$Puerto = "COM4",
    [switch]$SinCargar,
    [switch]$SinMonitor  # deja el puerto libre (por ejemplo, para app/herramientas/servos.html)
)
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$pio = "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe"
if (-not $SinCargar) {
    Write-Host "== Cargando $Entorno en $Puerto (mantén BOOT al ver Connecting...) ==" -ForegroundColor Cyan
    & $pio run -d firmware -e $Entorno -t upload --upload-port $Puerto
    if ($LASTEXITCODE -ne 0) { Write-Host "No se pudo cargar." -ForegroundColor Red; exit 1 }
}
if ($SinMonitor) { Write-Host "Cargado. Puerto libre." -ForegroundColor Green; exit 0 }
Write-Host ""
Write-Host "== Monitor serie de $Entorno (Ctrl+C para salir) ==" -ForegroundColor Cyan
& $pio device monitor -d firmware -e $Entorno -p $Puerto --filter direct
