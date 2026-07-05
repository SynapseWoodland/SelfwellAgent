# Cross-platform PowerShell mirror of `scripts/check_forbidden_colors.sh`.
# Enforces `docs/plan/mvp-implementation-plan.md` §17 hard-constraint #11.
[CmdletBinding()]
param(
    [string]$Root
)

if (-not $Root) {
    $Root = (git rev-parse --show-toplevel 2>$null)
    if (-not $Root) {
        $Root = (Resolve-Path "$PSScriptRoot/../..").Path
    }
}

$pattern = '#FF4D4F|#D32F2F|#007BFF'

$excludedDirs = @('build', '.dart_tool', 'scripts', 'lint-rules', 'api-types', '.git')
$excludeArgs = $excludedDirs | ForEach-Object { "--exclude-dir=$_" }

# ripgrep if available; otherwise Select-String fallback.
$rg = (Get-Command rg -ErrorAction SilentlyContinue)
if ($rg) {
    $raw = & rg --line-number --no-heading --hidden `
        --glob '!build' --glob '!.dart_tool' --glob '!scripts' `
        --glob '!lint-rules' --glob '!api-types' --glob '!.git' `
        --glob '!*.lock' --glob '!*.png' --glob '!*.jpg' `
        -e $pattern $Root 2>$null
} else {
    # Mirror exclude dirs with Get-ChildItem -Depth bound to avoid crawling build/.
    Get-ChildItem -Path $Root -Recurse -File -Force |
        Where-Object { $excludedDirs -notcontains $_.Directory.Name } |
        ForEach-Object {
            Select-String -Path $_.FullName -Pattern $pattern -AllMatches 2>$null |
                ForEach-Object {
                    "$($_.Path):$($_.LineNumber):$($_.Line.Trim())"
                }
        }
}

$violations = $raw | Where-Object {
    $_ -notmatch 'scripts[\\/]check_forbidden_colors' -and
    $_ -notmatch 'lint-rules[\\/]'
}

if ($violations) {
    Write-Host '[forbidden-colors] FAIL — §17 #11 hit:' -ForegroundColor Red
    $violations | ForEach-Object { Write-Host $_ }
    exit 1
}

Write-Host '[forbidden-colors] OK — §17 #11 0 hits' -ForegroundColor Green