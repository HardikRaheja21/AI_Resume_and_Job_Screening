param(
    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Media.Ocr, ContentType = WindowsRuntime]

function Get-AsTaskMethod {
    param(
        [bool]$Generic
    )

    return [System.WindowsRuntimeSystemExtensions].GetMethods() |
        Where-Object {
            $_.Name -eq "AsTask" -and
            $_.IsGenericMethodDefinition -eq $Generic -and
            $_.GetParameters().Count -eq 1
        } |
        Select-Object -First 1
}

function Await-Result {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Operation,

        [Parameter(Mandatory = $true)]
        [Type]$ResultType
    )

    $method = Get-AsTaskMethod -Generic $true
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    return $task.Result
}

function Await-Action {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Operation
    )

    $method = Get-AsTaskMethod -Generic $false
    $task = $method.Invoke($null, @($Operation))
    $task.Wait()
}

$resolvedPath = (Resolve-Path -LiteralPath $PdfPath).Path
$file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($resolvedPath)) ([Windows.Storage.StorageFile])
$document = Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()

if ($null -eq $engine) {
    throw "Windows OCR engine could not be initialized."
}

for ($pageIndex = 0; $pageIndex -lt $document.PageCount; $pageIndex++) {
    $page = $document.GetPage($pageIndex)
    $stream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    Await-Action ($page.RenderToStreamAsync($stream))
    $stream.Seek(0)

    $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $ocrResult = Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])

    $lineNumber = 1
    foreach ($line in $ocrResult.Lines) {
        $text = [string]$line.Text
        $clean = $text -replace "`r", " " -replace "`n", " "
        Write-Output ("{0}`t{1}`t{2}" -f ($pageIndex + 1), $lineNumber, $clean)
        $lineNumber++
    }
}
