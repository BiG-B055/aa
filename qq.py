<#
.SYNOPSIS
    Загружает файл на Python upload-сервер через HTTP POST multipart/form-data.

.EXAMPLE
    .\Upload-File.ps1 -Server 192.168.1.10 -Port 8080 -Path C:\temp\report.zip
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Server,

    [int]$Port = 8080,

    [Parameter(Mandatory=$true)]
    [string]$Path,

    [string]$FieldName = "file"
)

# ---- Проверки ----
if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    Write-Error "Файл не найден: $Path"
    exit 1
}

$file = Get-Item -LiteralPath $Path
$uri  = "http://${Server}:${Port}/"
$boundary = [System.Guid]::NewGuid().ToString("N")

Write-Host "Отправка: $($file.FullName) ($($file.Length) байт) -> $uri"

# ---- Формируем multipart ----
$enc = [System.Text.Encoding]::UTF8
$LF  = "`r`n"

# Пролог
$header = "--$boundary${LF}" +
          "Content-Disposition: form-data; name=""$FieldName""; filename=""$($file.Name)""${LF}" +
          "Content-Type: application/octet-stream${LF}${LF}"

$epilog = "${LF}--$boundary--${LF}"

$headerBytes = $enc.GetBytes($header)
$epilogBytes = $enc.GetBytes($epilog)

# Открываем файловый поток — не грузим всё в память
$fileStream = [System.IO.File]::OpenRead($file.FullName)
try {
    $contentLength = $headerBytes.Length + $file.Length + $epilogBytes.Length

    # ---- HTTP запрос ----
    $request = [System.Net.HttpWebRequest]::Create($uri)
    $request.Method        = "POST"
    $request.ContentType   = "multipart/form-data; boundary=$boundary"
    $request.ContentLength = $contentLength
    $request.Timeout       = 300000       # 5 минут
    $request.ReadWriteTimeout = 300000
    $request.AllowWriteStreamBuffering = $false

    $reqStream = $request.GetRequestStream()

    # 1. header
    $reqStream.Write($headerBytes, 0, $headerBytes.Length)

    # 2. тело файла чанками
    $buf = New-Object byte[] (1024 * 1024)
    $totalSent = 0
    while (($read = $fileStream.Read($buf, 0, $buf.Length)) -gt 0) {
        $reqStream.Write($buf, 0, $read)
        $totalSent += $read
        $pct = [int](($totalSent / $file.Length) * 100)
        Write-Progress -Activity "Отправка файла" -Status "$pct %" -PercentComplete $pct
    }

    # 3. epilog
    $reqStream.Write($epilogBytes, 0, $epilogBytes.Length)
    $reqStream.Close()

    Write-Progress -Activity "Отправка файла" -Completed

    # ---- Ответ ----
    $response = $request.GetResponse()
    $reader   = New-Object System.IO.StreamReader($response.GetResponseStream())
    $body     = $reader.ReadToEnd()
    $status   = [int]$response.StatusCode
    $reader.Close()
    $response.Close()

    Write-Host "HTTP $status"
    Write-Host $body
}
finally {
    $fileStream.Close()
}
