#!/usr/bin/env pwsh
# session-inject.ps1 — sessionStart 时向 context 注入高优先级规则摘要
# 触发事件: sessionStart
# 策略: 软提醒（failClosed=false），即使脚本失败也不阻塞会话

[CmdletBinding()]
param()

$ErrorActionPreference = 'Continue'

# 规则摘要 (硬约束五条)
$summary = @'
================================================================
[SelfwellAgent] Session Reminder — 工具优先级铁则
================================================================

每次工具调用前 0.5 秒，必须在脑中匹配以下规则:

  [读取]    只用 Read 工具。 禁止: cat/head/tail/more/less 等 shell 读文件。
  [改文件]  先完整 Read → StrReplace(<30%) 或 Write(<200 行整段重写)。
           禁止: sed/awk/perl -pi/echo / printf/tee 等 shell 改文件。
  [查目录]  只用 Glob 工具。 禁止: cmd /c "dir"、Shell 跑 find/cd/ls 跨盘。
  [创建]    Write 工具直接落地，禁止: echo > file / cat heredoc。
  [删除]    只用 rmdir 删空目录，删除非空需先向用户确认；禁止 rm -rf。

规则源文件: .cursor/rules/file-operation-stability.mdc (alwaysApply=true)
违规会被 .cursor/hooks/guard-shell.ps1 在 beforeShellExecution 阶段 exit 2 硬阻塞。

子 Agent (Task) 由 .cursor/hooks/subagent-rules-inject.ps1 在 subagentStart 阶段
强制注入本摘要。
================================================================
'@

# sessionStart 事件支持 user_message 与 agent_message
$payload = @{
    user_message  = $summary
    agent_message = $summary
} | ConvertTo-Json -Compress

Write-Output $payload
exit 0
