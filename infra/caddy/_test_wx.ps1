try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/auth/wx-login' -Method POST -Headers @{'Content-Type'='application/json'} -Body '{"code":"test_test_test_test","client":"wx_mp"}' -UseBasicParsing -TimeoutSec 8
    Write-Host ('STATUS=' + $r.StatusCode)
    Write-Host ('BODY=' + $r.Content)
} catch {
    Write-Host ('ERROR=' + $_.Exception.Message)
    if ($_.Exception.Response) {
        Write-Host ('ResponseStatus=' + [int]$_.Exception.Response.StatusCode)
        $stream = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        Write-Host ('ERROR_BODY=' + $reader.ReadToEnd())
    }
}