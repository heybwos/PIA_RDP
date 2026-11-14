# Compuerta G1 en un paso: carga test_huella_imagen y baja 3 huellas.
# Uso (desde la raíz del repo):  & .\pc\scripts\prueba_g1.ps1 -Puerto COM4
param(
    [string]$Puerto = "COM4",
    [int]$Veces = 3,
    [switch]$SinCargar
)
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $raiz

if (-not $SinCargar) {
    Write-Host "== Cargando el firmware test_huella_imagen en $Puerto ==" -ForegroundColor Cyan
    & "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware -e test_huella_imagen -t upload --upload-port $Puerto
    if ($LASTEXITCODE -ne 0) { Write-Host "No se pudo cargar. Cierra cualquier monitor serie y revisa el cable." -ForegroundColor Red; exit 1 }
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "== Captura: pon el dedo cuando diga 'Coloca el dedo' y no lo muevas ~7 s ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe pc\scripts\bajar_huella.py --puerto $Puerto --veces $Veces
