#!/usr/bin/env pwsh
# subagent-rules-inject.ps1 — subagentStart 时强制注入规则指针
# 触发事件: subagentStart
# 策略: failClosed=true （若脚本崩溃则阻塞子 agent 启动）

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# 读取 stdin
$raw = [Console]::In.ReadToEnd()

$rulesHint = @'
[强制约束 — 子 agent 必须遵守] 在你做任何工具调用之前先 Read 这两个文件:

  1. .cursor/rules/file-operation-stability.mdc        (最高优先级铁则)
  2. AGENTS.md                                          (角色定位与必须读的 skill)

违规会被 .cursor/hooks/guard-shell.ps1 在你跑 shell 时 exit 2 硬阻塞。
文件落入路径会被 stop hook 做事后审计（.cursor/hooks/audit-violations.ps1）。
'@

# subagentStart 支持 permission / user_message
# 这里给子 agent 的初始 prompt 注入规则指针
$payload = @{
    permission    = 'allow'
    user_message  = $rulesHint
    agent_message = $rulesHint
} | ConvertTo-Json -Compress

Write-Output $payload
exit 0
