@echo off
chcp 936 >nul 2>&1
title 设置 md2html 默认配色
setlocal enabledelayedexpansion
set "CONF=%~dp0_theme.conf"
set CUR=t1
if exist "%CONF%" set /p CUR=<"%CONF%"
if "!CUR!"=="" set CUR=t1

rem 带参数时直接设置，不进菜单:  设置默认配色.bat 3
if not "%~1"=="" (
  set C=%~1
  goto :apply
)

echo.
echo  ================================================================
echo    设置默认配色
echo    选好后所有转换都用这一套；临时想换可加 --theme tN 参数
echo  ================================================================
echo.
echo      当前默认: !CUR!
echo.
echo      [1]  t1   翠竹绿    纸米底 + 墨绿（出厂默认）
echo      [2]  t2   海盐蓝    清爽蓝调
echo      [3]  t3   墨黛青    青碧沉稳
echo      [4]  t4   紫罗兰    淡紫 + 罗兰紫
echo      [5]  t5   珊瑚橘    暖橙活力
echo      [6]  t6   胭脂红    玫红优雅
echo      [7]  t7   琥珀金    暖金复古
echo      [8]  t8   石墨岩    中性灰蓝
echo      [9]  t9   莓果粉    粉紫温柔
echo      [10] t10  曜石黑    深色模式，亮绿点缀
echo.
echo      直接回车 = 保持当前不变
echo  ----------------------------------------------------------------
set /p C= 请输入编号 1-10: 
if not defined C goto :end

:apply
set V=
if "!C!"=="1"  set V=t1
if "!C!"=="2"  set V=t2
if "!C!"=="3"  set V=t3
if "!C!"=="4"  set V=t4
if "!C!"=="5"  set V=t5
if "!C!"=="6"  set V=t6
if "!C!"=="7"  set V=t7
if "!C!"=="8"  set V=t8
if "!C!"=="9"  set V=t9
if "!C!"=="10" set V=t10
if not defined V goto :bad
> "%CONF%" echo !V!
echo.
echo  已保存默认配色: !V!
echo  配置文件: %CONF%
echo.
set /p P= 立即生成示例预览看看效果? (Y/N): 
if /i "!P!"=="y" (
  python "%~dp0md2html.py" "%~dp0examples\sample.md" desktop
  if exist "%~dp0examples\sample.html" start "" "%~dp0examples\sample.html"
)
goto :end

:bad
echo.
echo  输入无效: !C!   请输入 1 到 10 之间的数字。

:end
echo.
pause

