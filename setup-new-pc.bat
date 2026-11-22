@echo off
chcp 936 >nul
setlocal enabledelayedexpansion
title Alas 一键迁移

set "FORK=ManTianFengXue/AzurLaneAutoScript"
set "BRANCH=buy-purple-coins"
set "UPSTREAM=LmeSzinc/AzurLaneAutoScript"

echo ============================================
echo   Alas 一键迁移（把仓库切到自己的分支）
echo ============================================
echo.

rem ---------- 1. 找安装目录 ----------
echo [1/6] 查找 Alas 安装目录 ...
set "ROOT="
if exist "%~dp0toolkit\python.exe" if exist "%~dp0Alas.exe" set "ROOT=%~dp0"
if not defined ROOT if exist "%~dp0..\toolkit\python.exe" if exist "%~dp0..\Alas.exe" set "ROOT=%~dp0..\"

if not defined ROOT if not "%~1"=="" (
    if exist "%~1\toolkit\python.exe" set "ROOT=%~1\"
    if not defined ROOT if exist "%~1\AzurLaneAutoScript\toolkit\python.exe" set "ROOT=%~1\AzurLaneAutoScript\"
)

if not defined ROOT (
    echo   未直接命中，正在扫描各磁盘 ...
    for /f "usebackq delims=" %%i in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$roots=(Get-PSDrive -PSProvider FileSystem).Root; foreach($r in $roots){ Get-ChildItem $r -Directory -Filter AzurLaneAutoScript -Recurse -Depth 3 -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName 'Alas.exe') } | Select-Object -First 1 -ExpandProperty FullName } | Select-Object -First 1"`) do set "ROOT=%%i"
)

if not defined ROOT (
    echo.
    echo   没找到 Alas 安装目录（需要包含 Alas.exe 与 toolkit\python.exe）。
    echo   请把本脚本放进 Alas 目录再运行，或把安装目录拖到本脚本图标上。
    goto :fail
)
if not "%ROOT:~-1%"=="\" set "ROOT=%ROOT%\"
if not exist "%ROOT%Alas.exe" goto :fail

echo   找到: %ROOT%
cd /d "%ROOT%"

set "GIT=%ROOT%toolkit\Git\mingw64\bin\git.exe"
set "PY=%ROOT%toolkit\python.exe"
if not exist "%GIT%" set "GIT=git"
if not exist "%PY%" (
    echo   缺少 toolkit\python.exe，这不是完整的 Alas 安装目录。
    goto :fail
)

rem ---------- 2. SSH 密钥 ----------
echo.
echo [2/6] 检查 SSH 密钥 ...
set "SSHDIR=%USERPROFILE%\.ssh"
if not exist "%SSHDIR%" mkdir "%SSHDIR%"

if not exist "%SSHDIR%\id_ed25519" (
    echo   本机没有密钥，正在生成 ...
    ssh-keygen -t ed25519 -C "alas-%COMPUTERNAME%" -f "%SSHDIR%\id_ed25519" -N "" -q
    if errorlevel 1 (
        echo   生成失败。请确认系统带有 OpenSSH 客户端。
        goto :fail
    )
)

if not exist "%SSHDIR%\config" (
    > "%SSHDIR%\config" echo Host github.com
    >>"%SSHDIR%\config" echo     HostName ssh.github.com
    >>"%SSHDIR%\config" echo     Port 443
    >>"%SSHDIR%\config" echo     User git
    >>"%SSHDIR%\config" echo     StrictHostKeyChecking no
) else (
    findstr /c:"ssh.github.com" "%SSHDIR%\config" >nul || (
        >>"%SSHDIR%\config" echo.
        >>"%SSHDIR%\config" echo Host github.com
        >>"%SSHDIR%\config" echo     HostName ssh.github.com
        >>"%SSHDIR%\config" echo     Port 443
        >>"%SSHDIR%\config" echo     User git
        >>"%SSHDIR%\config" echo     StrictHostKeyChecking no
    )
)
if exist "%SystemRoot%\System32\OpenSSH\ssh.exe" set "GIT_SSH=%SystemRoot%\System32\OpenSSH\ssh.exe"

echo   验证 SSH 连接 ...
ssh -o BatchMode=yes -o StrictHostKeyChecking=no -T git@github.com >"%TEMP%\alas_ssh.txt" 2>&1
findstr /c:"successfully authenticated" "%TEMP%\alas_ssh.txt" >nul
if errorlevel 1 (
    echo.
    echo   ------------------------------------------------------------
    echo   这台电脑的 SSH 公钥还没有加到 GitHub。
    echo   请复制下面这一整行，打开 https://github.com/settings/ssh/new
    echo   Title 随便填，Key 粘贴进去，点 Add SSH key。
    echo   ------------------------------------------------------------
    type "%SSHDIR%\id_ed25519.pub"
    echo   ------------------------------------------------------------
    echo.
    pause
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no -T git@github.com >"%TEMP%\alas_ssh.txt" 2>&1
    findstr /c:"successfully authenticated" "%TEMP%\alas_ssh.txt" >nul
    if errorlevel 1 (
        echo   仍然无法认证，已中止。请确认公钥已保存到 GitHub。
        goto :fail
    )
)
echo   认证通过

rem ---------- 3. 仓库状态 ----------
echo.
echo [3/6] 检查仓库状态 ...
"%GIT%" rev-parse --abbrev-ref HEAD >nul 2>&1
if errorlevel 1 (
    echo   当前目录不是 git 仓库，无法继续。
    goto :fail
)
"%GIT%" diff --quiet
if errorlevel 1 (
    echo   有未提交的改动，继续会丢弃它们。
    echo   按 Ctrl+C 中止，或
    pause
)
"%GIT%" diff --cached --quiet
if errorlevel 1 (
    echo   有已暂存的改动，继续会丢弃它们。
    pause
)

rem ---------- 4. 换 remote 并切分支 ----------
echo.
echo [4/6] 设置远程仓库并切换分支 ...
"%GIT%" remote set-url origin git@github.com:%FORK%.git 2>nul || "%GIT%" remote add origin git@github.com:%FORK%.git
"%GIT%" remote set-url upstream git@github.com:%UPSTREAM%.git 2>nul || "%GIT%" remote add upstream git@github.com:%UPSTREAM%.git

"%GIT%" fetch origin %BRANCH% || goto :fail
"%GIT%" checkout -B %BRANCH% FETCH_HEAD || goto :fail
"%GIT%" reset --hard FETCH_HEAD || goto :fail
echo   已切换到 %BRANCH%

rem ---------- 5. 修正 deploy.yaml ----------
echo.
echo [5/6] 配置 deploy.yaml ...
if not exist "config\deploy.yaml" (
    if exist "config\deploy.template.yaml" copy "config\deploy.template.yaml" "config\deploy.yaml" >nul
)
"%PY%" -c "import re,io,os;p=os.path.join('config','deploy.yaml');s=io.open(p,encoding='utf-8').read();s=re.sub(r'(?m)^\s*Branch:.*$','    Branch: %BRANCH%',s);s=re.sub(r'(?m)^\s*AutoUpdate:.*$','    AutoUpdate: false',s);s=re.sub(r'(?m)^\s*CheckUpdateInterval:.*$','    CheckUpdateInterval: 0',s);io.open(p,'w',encoding='utf-8',newline='').write(s);print('deploy.yaml 已更新')"
if errorlevel 1 (
    echo   deploy.yaml 修改失败，请手动确认 Branch / AutoUpdate / CheckUpdateInterval。
)

rem ---------- 6. 跑一次同步 ----------
echo.
echo [6/6] 执行一次同步（校验补丁并拉取官方更新）...
if exist "sync-upstream.bat" (
    call "sync-upstream.bat" auto
) else (
    echo   未找到 sync-upstream.bat，跳过。
)

echo.
echo ============================================
echo   完成，可以启动 Alas 了。
echo   以后每次打开 Alas 都会自动检查官方更新并叠加补丁。
echo ============================================
pause
exit /b 0

:fail
echo.
echo 迁移未完成，请查看上面的提示。
pause
exit /b 1
