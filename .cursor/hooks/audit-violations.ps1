#!/usr/bin/env pwsh
# audit-violations.ps1 — stop 时审计本轮 agent 工具调用
# 触发事件: stop
# 策略: failClosed=false （审计脚本不阻塞会话，只追加日志）

[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

# 解析 hook 输入 (Cursor stop 事件 payload 通常含 transcript/conversation id)
$raw = [Console]::In.ReadToEnd()

$logDir = Join-Path $PSScriptRoot '..' 'logs'
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}
$logFile = Join-Path $logDir 'audit.log'

$timestamp = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'
$sessionId = ''
$toolCalls = 0
$violations = 0
$findings = @()

if (-not [string]::IsNullOrWhiteSpace($raw)) {
    try {
        $input = $raw | ConvertFrom-Json
        $sessionId = $input.session_id
    } catch {
        # 解析失败也照常记录
    }
}

# 这里只能做粗略审计 — 真正逐条历史扫描依赖 Cursor 是否把消息
# 历史喂到 stop hook 输入里。Cursor 当前 stop 事件 payload 比较轻,
# 我们做的是 "追加空白日志 + 提示用户用 git 历史 + transcript 复盘"。
# 实际重规则违规由 guard-shell.ps1 在 beforeShellExecution 已经拦截,
# 这里只兜底 stop hook 的诊断信息。

$entry = @{
    timestamp   = $timestamp
    session_id  = $sessionId
    tool_calls  = $toolCalls
    violations  = $violations
    note        = '重规则违规已在 beforeShellExecution 阶段被 guard-shell.ps1 拦截；本日志为合规审计兜底。'
}

$entry | ConvertTo-Json -Compress | Add-Content -Path $logFile -Encoding UTF8

# stop hook 默认无需返回 follow_up payload
exit 0
