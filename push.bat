@echo off
chcp 65001 >nul
echo ================================================
echo  深圳办公室租赁网站 - Git 推送脚本
echo ================================================
echo.

REM 项目目录（请根据你的实际路径修改这一行）
set PROJECT_DIR=E:\Program Files (x86)\workbuddy\2026-06-08-19-11-14\office-rental-landing

cd /d "%PROJECT_DIR%" 2>nul
if errorlevel 1 (
    echo [错误] 无法进入目录: %PROJECT_DIR%
    echo 请修改脚本中的 PROJECT_DIR 为你的实际项目路径
    pause
    exit /b 1
)

echo [1/3] 当前目录: %CD%
echo.

echo [2/3] 推送到 GitHub (520office/shenzhen-office-rental)...
git push github master
if errorlevel 1 (
    echo.
    echo [警告] GitHub 推送失败，请检查网络或 credentials
    echo 如需输入 token，请访问: https://github.com/settings/tokens
) else (
    echo [成功] GitHub 推送完成！
)
echo.

echo [3/3] 推送到 Gitee (office520/shenzhen-office-rental)...
git push origin master
if errorlevel 1 (
    echo.
    echo [警告] Gitee 推送失败
) else (
    echo [成功] Gitee 推送完成！
)
echo.

echo ================================================
echo  推送完成，查看 above 结果
echo ================================================
echo.
echo 访问地址:
echo  GitHub Pages:  https://520office.github.io/shenzhen-office-rental/
echo  Gitee Pages:   https://gitee.com/office520/shenzhen-office-rental/pages
echo.
pause
