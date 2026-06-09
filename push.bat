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
    "D:\Program Files\Git\cmd"
    "D:\Program Files\Git\bin"
    "C:\Program Files\Git\cmd"
    "C:\Program Files\Git\bin"
    "C:\Program Files (x86)\Git\cmd"
    "C:\Program Files (x86)\Git\bin"
    "%LOCALAPPDATA%\Programs\Git\cmd"
    "%LOCALAPPDATA%\Programs\Git\bin"
) do (
    if exist %%~d\git.exe (
        set GIT_CMD=%%~d\git.exe
        echo [0] 找到 Git: %%~d\git.exe
        goto found_git
    )
)

REM 如果上面都没找到，尝试直接调用
where git >nul 2>&1
if %errorlevel% equ 0 (
    set GIT_CMD=git
    echo [0] 找到 Git: 系统 PATH
    goto found_git
)

echo [错误] 未找到 Git！请先安装 Git for Windows：
echo  https://git-scm.com/download/win
echo.
echo 安装时选择"Use Git from the Windows Command Prompt"
echo.
pause
exit /b 1

:found_git
echo.

REM ====== 推送到 GitHub ======
echo [1/2] 推送到 GitHub (520office/shenzhen-office-rental)...
"%GIT_CMD%" push github master 2>&1
if %errorlevel% equ 0 (
    echo [成功] GitHub 推送完成!
) else (
    echo.
    echo [提示] GitHub 推送失败，可能原因:
    echo   1. 未配置 github remote，请先运行:
    echo      "%GIT_CMD%" remote add github https://github.com/520office/shenzhen-office-rental.git
    echo   2. 当前网络无法访问 GitHub
    echo.
    echo 不用担心，Gitee 推送成功后可以手动同步到 GitHub
)
echo.

REM ====== 推送到 Gitee ======
echo [2/2] 推送到 Gitee (office520/shenzhen-office-rental)...
"%GIT_CMD%" push origin master 2>&1
if %errorlevel% equ 0 (
    echo [成功] Gitee 推送完成!
) else (
    echo.
    echo [提示] Gitee 推送失败
)
echo.

echo ================================================
echo  推送完成！查看上方结果 ^^^
echo ================================================
echo.
echo  GitHub Pages:  https://520office.github.io/shenzhen-office-rental/
echo  Gitee Pages:   https://gitee.com/office520/shenzhen-office-rental/pages
echo.
pause
