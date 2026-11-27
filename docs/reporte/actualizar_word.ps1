# Abre el reporte con Microsoft Word, actualiza el índice, lo guarda y exporta un PDF.
#   powershell -NoProfile -ExecutionPolicy Bypass -File docs\reporte\actualizar_word.ps1
param([string]$Docx = (Join-Path $PSScriptRoot "Reporte_PIA_RDP.docx"))
$Docx = (Resolve-Path $Docx).Path
$Pdf = [IO.Path]::ChangeExtension($Docx, ".pdf")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    $doc.ExportAsFixedFormat($Pdf, 17)   # 17 = PDF
    $doc.Close($false)
    Write-Host "Índice actualizado y PDF en $Pdf"
} finally {
    $word.Quit()
    [Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
