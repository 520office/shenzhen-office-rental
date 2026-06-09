@echo off
chcp 65001 >nul
echo ================================================
echo  深圳办公室租赁网站 - Git 推送脚本
echo ================================================
echo.

REM 自动获取脚本所在目录
cd /d "%~dp0"
echo [0] 项目目录: %CD%
echo.

REM ====== 自动查找 git.exe ======
set GIT_CMD=
for %%d in (
    "D:/Program Files/Git/cmd"
    "D:/Program Files/Git/bin"
    "C:/Program Files/Git/cmd"
    "C:/Program Files/Git/bin"
    "C:/Program Files (x86)/Git/cmd"
    "C:/Program Files (x86)/Git/bin"
    "%LOCALAPPDATA%\Programs\Git\cmd"
    "%LOCALAPPDATA%\Programs\Git\bin"
) do (
    if exist %%~d\git.exe (
        set GIT_CMD=%%~d\git.exe
        echo [0] Found Git: %%~d\git.exe
        goto found_git
    )
)

where git >nul 2>&1
if %errorlevel% equ 0 (
    set GIT_CMD=git
    echo [0] Found Git: system PATH
    goto found_git
)

echo [ERROR] Git not found! Install from https://git-scm.com/download/win
echo.
pause
exit /b 1

:found_git
echo.

echo [1/2] Pushing to GitHub...
"%GIT_CMD%" push github master 2>&1
echo [2/2] Pushing to Gitee...
"%GIT_CMD%" push origin master 2>&1
echo.
echo Done! https://520office.github.io/shenzhen-office-rental/
pause
