@echo off
chcp 65001 >nul
echo ================================================
echo  深圳办公室租赁网站 - Git 推送脚本
echo ================================================
echo.

REM 自动获取脚本所在目录（把 push.bat 放在项目根目录即可）
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/3] 当前目录: %CD%
echo.

echo [2/3] 推送到 GitHub (520office/shenzhen-office-rental)...
git push github master
if errorlevel 1 (
    echo.
    echo [提示] GitHub 推送失败，可能原因：
    echo   1. 网络不通（公司网络可能限制 GitHub）
    echo   2. 未配置 github remote，请先运行：
    echo      git remote add github https://github.com/520office/shenzhen-office-rental.git
    echo   3. 需要输入 Token，请按提示操作
    echo.
) else (
    echo [成功] GitHub 推送完成！
)
echo.

echo [3/3] 推送到 Gitee (office520/shenzhen-office-rental)...
git push origin master
if errorlevel 1 (
    echo.
    echo [提示] Gitee 推送失败，请检查网络或 credentials
    echo.
) else (
    echo [成功] Gitee 推送完成！
)
echo.

echo ================================================
echo  推送完成，请查看上方结果
echo ================================================
echo.
echo 访问地址:
echo  GitHub Pages:  https://520office.github.io/shenzhen-office-rental/
echo  Gitee Pages:   https://gitee.com/office520/shenzhen-office-rental/pages
echo.
pause
