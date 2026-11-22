@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "GIT=toolkit\Git\mingw64\bin\git.exe"
set "PY=toolkit\python.exe"
set "BRANCH=buy-purple-coins"
set "MODE=%~1"
if "%MODE%"=="" set "MODE=manual"
set "LOG=%~dp0sync-upstream.log"

rem git bundled cygwin ssh may fail with "couldn't create signal pipe, Win32 error 5"
if exist "%SystemRoot%\System32\OpenSSH\ssh.exe" set "GIT_SSH=%SystemRoot%\System32\OpenSSH\ssh.exe"

for /f "delims=" %%i in ('%GIT% rev-parse HEAD') do set "SAVED=%%i"

echo. >> "%LOG%"
echo [%date% %time%] === start mode=%MODE% head=!SAVED! === >> "%LOG%"

echo [1/7] check worktree ...
%GIT% diff --quiet
if errorlevel 1 goto :busy
%GIT% diff --cached --quiet
if errorlevel 1 goto :busy
echo   clean

echo [2/7] fetch upstream ...
%GIT% fetch upstream master >> "%LOG%" 2>&1
if errorlevel 1 goto :rollback

set "BEHIND=0"
set "AHEAD=0"
for /f "tokens=1,2" %%a in ('%GIT% rev-list --left-right --count upstream/master...%BRANCH%') do (
    set "BEHIND=%%a"
    set "AHEAD=%%b"
)
echo   upstream new commits: !BEHIND!   my commits: !AHEAD!
if "!BEHIND!"=="0" if /i not "%MODE%"=="force" goto :uptodate

echo [3/7] drop generated commit (if HEAD is it) ...
%GIT% log -1 --format=%%s > "%TEMP%\alas_head.txt" 2>nul
findstr /c:"chore(config)" "%TEMP%\alas_head.txt" >nul
if errorlevel 1 (
    echo   HEAD is not the generated commit, skip
) else (
    %GIT% reset --hard HEAD~1 >> "%LOG%" 2>&1
    if errorlevel 1 goto :rollback
    echo   back to hand-written commit
)

echo [4/7] replay my patch onto upstream/master ...
%GIT% rebase upstream/master >> "%LOG%" 2>&1
if errorlevel 1 goto :conflict
echo   done

echo [5/7] regenerate config and i18n ...
%PY% -m module.config.config_updater >> "%LOG%" 2>&1
if errorlevel 1 goto :rollback
echo   done

echo [6/7] verify patch still present ...
findstr /c:"BuyPurpleCoins" module\config\argument\argument.yaml >nul || goto :verify_fail
findstr /c:"BuyPurpleCoins" module\config\config_generated.py >nul || goto :verify_fail
findstr /c:"BuyPurpleCoins" module\os_shop\selector.py >nul || goto :verify_fail
findstr /c:"OpsiAkashiShop" module\config\argument\task.yaml >nul || goto :verify_fail
findstr /c:"OpsiAkashiShop" module\config\config_generated.py >nul || goto :verify_fail
findstr /c:"OpsiMeowfficerShop" module\config\config_generated.py >nul || goto :verify_fail
findstr /c:"CoalitionDaily_Mode" module\config\config_generated.py >nul || goto :verify_fail
findstr /c:"> CoalitionDaily >" module\config\config_manual.py >nul || goto :verify_fail
findstr /c:"DAILY_START" module\coalition\daily_assets.py >nul || goto :verify_fail
findstr /c:"coalition_20261124" module\coalition\ui.py >nul || goto :verify_fail
findstr /c:"is_akashi_shop_enabled" module\os\tasks\stronghold.py >nul || goto :verify_fail
findstr /c:"OpsiAkashiShop.BuyPurpleCoins.name" module\config\i18n\en-US.json >nul && goto :verify_fail
findstr /c:"OpsiAkashiShop.BuyPurpleCoins.name" module\config\i18n\zh-TW.json >nul && goto :verify_fail
findstr /c:"OpsiAkashiShop.BuyPurpleCoins.name" module\config\i18n\ja-JP.json >nul && goto :verify_fail
echo   OK

echo [7/7] commit and push ...
%GIT% add -- module/config/argument/args.json module/config/argument/menu.json module/config/config_generated.py module/config/i18n/zh-CN.json module/config/i18n/zh-TW.json module/config/i18n/en-US.json module/config/i18n/ja-JP.json config/template.json
%GIT% diff --cached --quiet
if errorlevel 1 (
    %GIT% commit -m "chore(config): regenerate config and i18n" >> "%LOG%" 2>&1
    if errorlevel 1 goto :rollback
)
%GIT% push --force-with-lease origin %BRANCH% >> "%LOG%" 2>&1
if errorlevel 1 (
    echo   warning: push failed, local code is still fine
) else (
    echo   pushed
)

echo [%date% %time%] === success === >> "%LOG%"
echo.
echo SYNC OK
if /i not "%MODE%"=="auto" pause
exit /b 0

:uptodate
echo   already up to date, nothing to sync
echo [%date% %time%] === up to date === >> "%LOG%"
if /i not "%MODE%"=="auto" pause
exit /b 0

:busy
echo   worktree is dirty, skip sync
echo [%date% %time%] === skipped, dirty worktree === >> "%LOG%"
if /i not "%MODE%"=="auto" (
    echo   commit or discard your changes first, then run again
    pause
)
exit /b 0

:conflict
echo   ^!^! rebase conflict, rolling back
%GIT% rebase --abort >> "%LOG%" 2>&1
goto :rollback

:verify_fail
echo   ^!^! verify failed, rolling back
goto :rollback

:rollback
if exist ".git\rebase-merge" %GIT% rebase --abort >> "%LOG%" 2>&1
if exist ".git\rebase-apply" %GIT% rebase --abort >> "%LOG%" 2>&1
%GIT% reset --hard !SAVED! >> "%LOG%" 2>&1
echo   rolled back to !SAVED!
echo [%date% %time%] === failed, rolled back to !SAVED! === >> "%LOG%"
if /i not "%MODE%"=="auto" pause
exit /b 1
