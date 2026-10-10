@echo off
setlocal enabledelayedexpansion
title md2onepagehtml - 多 Markdown 合并单页

if "%~1"=="" (
  echo.
  echo  [md2onepagehtml] 把多份 Markdown 合并成一个单文件 HTML
  echo  ---------------------------------------------------------------
  echo   用法1: 拖入文件夹        = 合并整个目录
  echo   用法2: 拖入多个 .md 文件 = 只合并这几篇
  echo   用法3: 输入文件夹路径后回车（文件夹与文件可混搭）
  echo.
  set /p D= 目录: 
  if not defined D exit /b 0
  python "%~dp0md2onepagehtml.py" "!D!"
  if errorlevel 1 goto :fail
) else (
  for %%D in (%*) do (
    echo.
    echo  [md2onepagehtml] 正在合并: %%~nxD
    python "%~dp0md2onepagehtml.py" "%%~D"
    if errorlevel 1 goto :fail
  )
)
echo.
echo  [md2onepagehtml] 完成。HTML 默认输出在该目录内（目录名.html）
goto :end

:fail
echo.
echo  [md2onepagehtml] 合并失败，请检查目录是否存在、Python 是否可用。

:end
echo.
pause

