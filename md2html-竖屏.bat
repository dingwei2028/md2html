@echo off
setlocal enabledelayedexpansion
title md2html - Markdown 转 HTML（竖屏版）

if "%~1"=="" (
  echo.
  echo  [md2html] 竖屏友好版转换
  echo  ------------------------------------------------
  echo   用法1: 把 .md 文件直接拖到这个窗口上（可多选）
  echo   用法2: 在此输入文件路径后回车
  echo.
  set /p F= 路径: 
  if not defined F exit /b 0
  python "%~dp0md2html.py" "!F!" portrait
  if errorlevel 1 goto :fail
) else (
  for %%F in (%*) do (
    echo.
    echo  [md2html] 正在转换: %%~nxF
    python "%~dp0md2html.py" "%%~F" portrait
    if errorlevel 1 goto :fail
  )
)
echo.
echo  [md2html] 完成。竖屏版 HTML 已生成在与源文件相同的目录
goto :end

:fail
echo.
echo  [md2html] 转换失败，请检查文件是否存在、Python 是否可用。

:end
echo.
pause

