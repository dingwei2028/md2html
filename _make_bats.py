# -*- coding: utf-8 -*-
"""以 GBK(ANSI) 编码重建两个 .bat，保证中文 Windows 下显示正常。
注意: 批处理 FOR 循环变量必须写成 %%~F（文件中保留两个百分号），
因此本脚本用纯字符串拼接，避免 python % 格式化吞掉 %% 。
"""
import io
import os

# bat 一律生成在脚本所在目录（不要再写死本机路径）
HERE = os.path.dirname(os.path.abspath(__file__))


def bat_onepage():
    """多文件合并入口的 bat 内容"""
    lines = [
        '@echo off',
        'setlocal enabledelayedexpansion',
        'title md2onepagehtml - 多 Markdown 合并单页',
        '',
        'if "%~1"=="" (',
        '  echo.',
        '  echo  [md2onepagehtml] 把一个目录下的多份 Markdown 合并成一个单文件 HTML',
        '  echo  ---------------------------------------------------------------',
        '  echo   用法1: 把文件夹直接拖到本窗口上，回车',
        '  echo   用法2: 输入文件夹路径后回车',
        '  echo.',
        '  set /p D= 目录: ',
        '  if not defined D exit /b 0',
        '  python "%~dp0md2onepagehtml.py" "!D!"',
        '  if errorlevel 1 goto :fail',
        ') else (',
        '  for %%D in (%*) do (',
        '    echo.',
        '    echo  [md2onepagehtml] 正在合并: %%~nxD',
        '    python "%~dp0md2onepagehtml.py" "%%~D"',
        '    if errorlevel 1 goto :fail',
        '  )',
        ')',
        'echo.',
        'echo  [md2onepagehtml] 完成。HTML 默认输出在该目录内（目录名.html）',
        'goto :end',
        '',
        ':fail',
        'echo.',
        'echo  [md2onepagehtml] 合并失败，请检查目录是否存在、Python 是否可用。',
        '',
        ':end',
        'echo.',
        'pause',
        '',
    ]
    return '\r\n'.join(lines) + '\r\n'


def bat_content(portrait):
    mode = 'portrait' if portrait else 'desktop'
    if portrait:
        title = 'md2html - Markdown 转 HTML（竖屏版）'
        mode_label = '竖屏友好版'
        done_msg = '竖屏版 HTML 已生成在与源文件相同的目录'
    else:
        title = 'md2html - Markdown 转 HTML（横屏版）'
        mode_label = '横屏/桌面版'
        done_msg = 'HTML 已生成在与源文件相同的目录'
    lines = [
        '@echo off',
        'setlocal enabledelayedexpansion',
        'title ' + title,
        '',
        'if "%~1"=="" (',
        '  echo.',
        '  echo  [md2html] ' + mode_label + '转换',
        '  echo  ------------------------------------------------',
        '  echo   用法1: 把 .md 文件直接拖到这个窗口上（可多选）',
        '  echo   用法2: 在此输入文件路径后回车',
        '  echo.',
        '  set /p F= 路径: ',
        '  if not defined F exit /b 0',
        '  python "%~dp0md2html.py" "!F!" ' + mode,
        '  if errorlevel 1 goto :fail',
        ') else (',
        '  for %%F in (%*) do (',
        '    echo.',
        '    echo  [md2html] 正在转换: %%~nxF',
        '    python "%~dp0md2html.py" "%%~F" ' + mode,
        '    if errorlevel 1 goto :fail',
        '  )',
        ')',
        'echo.',
        'echo  [md2html] 完成。' + done_msg,
        'goto :end',
        '',
        ':fail',
        'echo.',
        'echo  [md2html] 转换失败，请检查文件是否存在、Python 是否可用。',
        '',
        ':end',
        'echo.',
        'pause',
        '',
    ]
    return '\r\n'.join(lines) + '\r\n'

bats = [
    (os.path.join(HERE, 'md2html.bat'), 'desktop'),
    (os.path.join(HERE, 'md2html-竖屏.bat'), 'portrait'),
    (os.path.join(HERE, 'md2onepagehtml.bat'), 'onepage'),
]
for path, kind in bats:
    if kind == 'onepage':
        content = bat_onepage()
    else:
        content = bat_content(kind == 'portrait')
    with io.open(path, 'w', encoding='gbk') as f:
        f.write(content)
    print('written:', path)
