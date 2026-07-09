try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/api/v1/auth/wx-login' -Method POST -Headers @{'Content-Type'='application/json'} -Body '{"code":"test_test_test_test","client":"wx_mp"}' -UseBasicParsing -TimeoutSec 8
    Write-Host ('STATUS=' + $r.StatusCode)
    Write-Host ('BODY=' + $r.Content)
    Write-Host ('HEADERS=' + ($r.Headers | Out-String))
} catch {
    Write-Host ('ERROR=' + $_.Exception.Message)
    if ($_.Exception.Response) {
        Write-Host ('ResponseStatus=' + [int]$_.Exception.Response.StatusCode)
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        Write-Host ('ERROR_BODY=' + $reader.ReadToEnd())
    }
}

Write-Host '---OPENAPI---'
try {
    $open = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/openapi.json' -UseBasicParsing -TimeoutSec 5
    $json = $open.Content | ConvertFrom-Json
    $paths = $json.paths.PSObject.Properties | ForEach-Object { "$($_.Name) $($_.Value | ConvertTo-Json -Compress)" }
    $paths | Where-Object { $_ -match 'wx-login|auth' } | ForEach-Object { Write-Host $_ }
} catch {
    Write-Host ('OPENAPI_ERROR=' + $_.Exception.Message)
}