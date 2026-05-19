param(
    [Parameter(Mandatory = $true)]
    [string]$PdfPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFolder, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapEncoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapPixelFormat, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapAlphaMode, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Storage.CreationCollisionOption, Windows.Storage, ContentType = WindowsRuntime]

function Get-AsTaskMethod {
    param([bool]$Generic)

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
    param([Parameter(Mandatory = $true)][object]$Operation)

    $method = Get-AsTaskMethod -Generic $false
    $task = $method.Invoke($null, @($Operation))
    $task.Wait()
}

$resolvedPdf = (Resolve-Path -LiteralPath $PdfPath).Path
$resolvedOutput = (Resolve-Path -LiteralPath $OutputDir -ErrorAction SilentlyContinue)
if ($null -eq $resolvedOutput) {
    $null = New-Item -ItemType Directory -Path $OutputDir -Force
    $resolvedOutput = Resolve-Path -LiteralPath $OutputDir
}
$outputPath = $resolvedOutput.Path

$pdfFile = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($resolvedPdf)) ([Windows.Storage.StorageFile])
$document = Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($pdfFile)) ([Windows.Data.Pdf.PdfDocument])

for ($pageIndex = 0; $pageIndex -lt $document.PageCount; $pageIndex++) {
    $page = $document.GetPage($pageIndex)
    $memoryStream = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    Await-Action ($page.RenderToStreamAsync($memoryStream))
    $memoryStream.Seek(0)

    $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($memoryStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $pixels = Await-Result ($decoder.GetPixelDataAsync()) ([Windows.Graphics.Imaging.PixelDataProvider])
    $bytes = $pixels.DetachPixelData()

    $fileName = ("page_{0:D3}.png" -f ($pageIndex + 1))
    $targetPath = Join-Path $outputPath $fileName
    if (Test-Path -LiteralPath $targetPath) {
        Remove-Item -LiteralPath $targetPath -Force
    }

    $targetFile = Await-Result (
        [Windows.Storage.StorageFolder]::GetFolderFromPathAsync($outputPath)
    ) ([Windows.Storage.StorageFolder])
    $createdFile = Await-Result (
        $targetFile.CreateFileAsync($fileName, [Windows.Storage.CreationCollisionOption]::ReplaceExisting)
    ) ([Windows.Storage.StorageFile])
    $fileStream = Await-Result (
        $createdFile.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)
    ) ([Windows.Storage.Streams.IRandomAccessStream])

    $encoder = Await-Result (
        [Windows.Graphics.Imaging.BitmapEncoder]::CreateAsync([Windows.Graphics.Imaging.BitmapEncoder]::PngEncoderId, $fileStream)
    ) ([Windows.Graphics.Imaging.BitmapEncoder])
    $encoder.SetPixelData(
        [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
        [Windows.Graphics.Imaging.BitmapAlphaMode]::Premultiplied,
        $decoder.PixelWidth,
        $decoder.PixelHeight,
        $decoder.DpiX,
        $decoder.DpiY,
        $bytes
    )
    Await-Action ($encoder.FlushAsync())
    $fileStream.Dispose()

    Write-Output ("{0}`t{1}`t{2}" -f ($pageIndex + 1), $decoder.PixelWidth, $decoder.PixelHeight)
}
