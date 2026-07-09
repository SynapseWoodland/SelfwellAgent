$files = @(
    'D:\agent-project\SelfwellAgent\infra\caddy\start.cmd',
    'D:\agent-project\SelfwellAgent\infra\caddy\Caddyfile'
)
foreach ($f in $files) {
    $b = [System.IO.File]::ReadAllBytes($f)
    $first6 = @($b[0..5]) | ForEach-Object { '{0:X2}' -f $_ }
    Write-Host ('file=' + $f)
    Write-Host ('  size=' + $b.Length)
    Write-Host ('  first6=' + ($first6 -join ' '))
    $hasBom = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
    Write-Host ('  hasUtf8Bom=' + $hasBom)
}