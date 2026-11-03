<#
.SYNOPSIS
    Отправляет файл на сервер 149.104.76.115

.EXAMPLE
    .\Send-ToServer.ps1 -Path "C:\Windows\users\user1\2b152adf_1KB.dat"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$Server = "149.104.76.115"
$Port = 8080
$Uri = "http://${Server}:${Port}/"

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    Write-Host "Файл не найден: $Path" -ForegroundColor Red
    exit 1
}

$file = Get-Item -LiteralPath $Path
Write-Host "Отправка '$($file.Name)' ($($file.Length) байт) на сервер $Server..." -ForegroundColor Cyan

# Формируем multipart/form-data
$boundary = [System.Guid]::NewGuid().ToString("N")
$enc = [System.Text.Encoding]::UTF8
$LF = "`r`n"

$header = "--$boundary${LF}" +
          "Content-Disposition: form-data; name=""file""; filename=""$($file.Name)""${LF}" +
          "Content-Type: application/octet-stream${LF}${LF}"

$epilog = "${LF}--$boundary--${LF}"

$headerBytes = $enc.GetBytes($header)
$epilogBytes = $enc.GetBytes($epilog)

$fileStream = [System.IO.File]::OpenRead($file.FullName)

try {
    $contentLength = $headerBytes.Length + $file.Length + $epilogBytes.Length

    $request = [System.Net.HttpWebRequest]::Create($Uri)
    $request.Method = "POST"
    $request.ContentType = "multipart/form-data; boundary=$boundary"
    $request.ContentLength = $contentLength
    $request.Timeout = 600000 # 10 минут
    $request.AllowWriteStreamBuffering = $false

    $reqStream = $request.GetRequestStream()
    $reqStream.Write($headerBytes, 0, $headerBytes.Length)

    $buf = New-Object byte[] (1024 * 1024)
    $totalSent = 0
    while (($read = $fileStream.Read($buf, 0, $buf.Length)) -gt 0) {
        $reqStream.Write($buf, 0, $read)
        $totalSent += $read
        Write-Progress -Activity "Отправка $($file.Name)" -Status "$totalSent из $($file.Length) байт" -PercentComplete (($totalSent / $file.Length) * 100)
    }

    $reqStream.Write($epilogBytes, 0, $epilogBytes.Length)
    $reqStream.Close()
    Write-Progress -Activity "Отправка" -Completed

    $response = $request.GetResponse()
    $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
    $body = $reader.ReadToEnd()
    $status = [int]$response.StatusCode
    $reader.Close()
    $response.Close()

    if ($status -eq 200) {
        Write-Host "`nУСПЕШНО ОТПРАВЛЕНО!" -ForegroundColor Green
        Write-Host "Ответ сервера: $body"
    } else {
        Write-Host "`nОШИБКА! HTTP $status" -ForegroundColor Red
    }
}
catch {
    Write-Host "`nОШИБКА СОЕДИНЕНИЯ: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Проверьте, запущен ли Python-сервер на 149.104.76.115 и открыт ли порт 8080." -ForegroundColor Yellow
}
finally {
    $fileStream.Close()
}
