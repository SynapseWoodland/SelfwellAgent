@echo off
REM guard-shell.cmd — Windows 垫片，探测 Python 解释器并调用 guard-shell.py
REM
REM 关键：每条退出路径都必须让 Python 至少输出一次 stdout JSON。
REM 原因：Cursor Hooks 协议把 "no output" 视为 fail-closed 阻塞错误。
REM
REM 探测顺序（覆盖 Windows 默认安装场景）：
REM   1. python        （python.org 安装 / Microsoft Store 别名）
REM   2. py            （Python Launcher for Windows，推荐）
REM   3. python3       （某些 Linux 子系统）
REM
REM 全部失败 → 输出 fail-open JSON + exit 0（绝不让垫片 bug 阻塞所有 shell）
REM
REM 用法（hooks.json 中）：
REM   "command": "D:\\agent-project\\SelfwellAgent\\.cursor\\hooks\\guard-shell.cmd"
REM
REM 详见：.cursor/hooks/README.md

setlocal

set "HOOK_DIR=%~dp0"
set "PY_SCRIPT=%HOOK_DIR%guard-shell.py"

REM --- 1. 探测 python ---
where python >nul 2>&1
if %ERRORLEVEL% == 0 (
    python "%PY_SCRIPT%"
    REM 注意：Python 退出码就是我们的退出码，stdout 已由 Python 输出
    exit /b %ERRORLEVEL%
)

REM --- 2. 探测 py (Python Launcher) ---
where py >nul 2>&1
if %ERRORLEVEL% == 0 (
    py -3 "%PY_SCRIPT%"
    exit /b %ERRORLEVEL%
)

REM --- 3. 探测 python3 ---
where python3 >nul 2>&1
if %ERRORLEVEL% == 0 (
    python3 "%PY_SCRIPT%"
    exit /b %ERRORLEVEL%
)

REM --- 4. 全部失败 → fail-open JSON（绝不让垫片 bug 阻塞 agent） ---
echo {"permission":"allow","user_message":"[guard-shell.cmd] No Python interpreter found; fail-open"}
exit /b 0