# -*- coding: utf-8 -*-
"""
md2html — 本地 Markdown → 漂亮 HTML 转换工具（零依赖，纯 Python 标准库）
用法:
    python md2html.py <xxx.md> [desktop|portrait] [--theme t1..t10]
  desktop : 生成横屏/桌面版（宽屏侧边目录，窄屏自动变抽屉）
  portrait: 生成竖屏友好版（手机优先：吸顶导航 + 抽屉目录 + 卡片式表格）
  --theme : 指定默认配色（t1 翠竹绿 / t2 海盐蓝 / t3 墨黛青 / t4 紫罗兰 / t5 珊瑚橘
            / t6 胭脂红 / t7 琥珀金 / t8 石墨岩 / t9 莓果粉 / t10 曜石黑）
            页面右下角调色板按钮可随时切换 10 套配色，选择会自动记忆
输出: 与源 md 同目录，desktop → 原名.html ；portrait → 原名-竖屏版.html
"""
import html as _html
import os
import re
import sys
import time

# ===================== 行内解析 =====================

def _escape(t):
    return _html.escape(t, quote=False)

def inline(s):
    """解析行内格式：代码段、粗体、斜体、删除线、链接、图片（先转义，后替换）"""
    out = []
    for part in re.split(r'(`[^`]+`)', s):
        if len(part) >= 2 and part[0] == '`' and part[-1] == '`':
            out.append('<code>' + _escape(part[1:-1]) + '</code>')
        else:
            out.append(_apply_inline(_escape(part)))
    return ''.join(out)

def _apply_inline(s):
    # 图片 ![alt](url)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)',
               lambda m: '<img src="%s" alt="%s">' % (_html.escape(m.group(2), quote=True), _html.escape(m.group(1), quote=True)), s)
    # 链接 [text](url)  （url 不含空格；保留 #锚点 与相对路径）
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)',
               lambda m: '<a href="%s">%s</a>' % (_html.escape(m.group(2), quote=True), m.group(1)), s)
    # 粗体 **x**
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    # 斜体 *x*（避开粗体边界）
    s = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', s)
    # 删除线 ~~x~~
    s = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', s)
    return s

# ===================== 代码高亮（轻量） =====================

KEYWORDS = {
    'python': {'def','class','if','else','elif','for','while','return','import','from','as','with',
               'try','except','finally','raise','lambda','None','True','False','and','or','not','in',
               'is','pass','yield','global','nonlocal','async','await','del','assert','break','continue'},
    'js': {'function','class','if','else','for','while','return','import','export','from','const','let',
           'var','new','try','catch','throw','switch','case','break','continue','typeof','instanceof',
           'this','null','undefined','true','false','async','await','yield','do','in','of'},
    'bash': {'if','then','else','fi','for','do','done','while','case','esac','function','return',
             'local','export','echo','exit','cd','set','true','false'},
    'text': set(),
}
DEFAULT_KW = {'if','else','for','while','return','function','class','import','from','const','let',
              'var','new','try','catch','throw','switch','case','break','continue','true','false',
              'null','None','def','as','with','and','or','not','in','is'}

def highlight(code, lang):
    lang = (lang or '').lower()
    kw = KEYWORDS.get(lang, DEFAULT_KW)
    strings = []
    def stash(m):
        strings.append(m.group(0))
        return '\x00Q%dQ\x00' % (len(strings) - 1)   # 占位含字母 Q，避开数字/关键字正则的 \b 匹配
    code = re.sub(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', stash, code)
    code = re.sub(r'(#.*$|//.*$)', lambda m: '<span class="t-c">' + _escape(m.group(0)) + '</span>', code, flags=re.M)
    code = re.sub(r'\b(\d+(?:\.\d+)?)\b', r'<span class="t-n">\1</span>', code)
    code = re.sub(r'\b([A-Za-z_]\w*)\b',
                  lambda m: ('<span class="t-k">' + m.group(1) + '</span>') if m.group(1) in kw else m.group(1), code)
    def restore(m):
        return '<span class="t-s">' + _escape(strings[int(m.group(1))]) + '</span>'
    return re.sub(r'\x00Q(\d+)Q\x00', restore, code)

# ===================== 区块解析 =====================

def parse_blocks(lines):
    blocks = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].rstrip()
        if not s.strip():
            i += 1
            continue
        # 围栏代码块
        if s.lstrip().startswith('```'):
            lang = s.lstrip()[3:].strip()
            buf, j = [], i + 1
            while j < n and not lines[j].lstrip().startswith('```'):
                buf.append(lines[j])
                j += 1
            blocks.append(('code', lang, '\n'.join(buf)))
            i = j + 1
            continue
        # 引用
        if s.lstrip().startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(lines[i].lstrip()[1:].lstrip())
                i += 1
            blocks.append(('quote', buf))
            continue
        # 标题
        m = re.match(r'^\s{0,3}(#{1,6})\s+(.*)$', s)
        if m:
            blocks.append(('h', len(m.group(1)), m.group(2).strip()))
            i += 1
            continue
        # 水平线
        if re.match(r'^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$', s):
            blocks.append(('hr',))
            i += 1
            continue
        # 表格（行首 |）
        if re.match(r'^\s{0,3}\|.*\|', s):
            buf = []
            while i < n and re.match(r'^\s{0,3}\|.*\|', lines[i]):
                buf.append(lines[i].strip())
                i += 1
            blocks.append(('table', buf))
            continue
        # 列表
        if re.match(r'^\s{0,3}([-*+]|\d+[.)])\s+', s):
            items, j = [], i
            while j < n:
                l = lines[j]
                if not l.strip():
                    if j + 1 < n and re.match(r'^\s{0,3}([-*+]|\d+[.)])\s+', lines[j + 1]):
                        j += 1
                        continue
                    break
                if re.match(r'^\s{0,3}([-*+]|\d+[.)])\s+', l):
                    items.append(l)
                    j += 1
                    continue
                break
            ordered = bool(re.match(r'^\s{0,3}\d+[.)]', items[0]))
            blocks.append(('list', ordered, items))
            i = j
            continue
        # 段落
        buf = []
        while i < n:
            l = lines[i]
            if not l.strip():
                break
            if re.match(r'^\s{0,3}(```|>|#{1,6}\s|-{3,}|\*{3,}|_{3,}|[-*+]\s+|\d+[.)]\s+|\|.*\|)', l):
                break
            buf.append(l.rstrip())
            i += 1
        blocks.append(('p', ' '.join(buf)))
    return blocks

def _render_list_items(rows):
    out = []
    i, n = 0, len(rows)
    while i < n:
        indent, content = rows[i]
        out.append('<li>' + inline(content))
        if i + 1 < n and rows[i + 1][0] > indent:
            j = i + 1
            sub = []
            while j < n and rows[j][0] > indent:
                sub.append(rows[j])
                j += 1
            out.append('<ul>' + _render_list_items(sub) + '</ul>')
        out.append('</li>')
        i = j if (i + 1 < n and rows[i + 1][0] > indent) else i + 1
    return ''.join(out)

def render_list(items, ordered):
    rows = []
    for it in items:
        m = re.match(r'^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$', it)
        rows.append((len(m.group(1)), m.group(2)))
    tag = 'ol' if ordered else 'ul'
    return '<%s>%s</%s>' % (tag, _render_list_items(rows), tag)

def render_table(rows):
    def cells(line):
        t = line.strip()
        if t.startswith('|'):
            t = t[1:]
        if t.endswith('|'):
            t = t[:-1]
        return [c.strip() for c in t.split('|')]
    body = []
    head = cells(rows[0])
    body.append('<table>')
    body.append('<thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head) + '</tr></thead>')
    body.append('<tbody>')
    for row in rows[2:]:  # 跳过表头与分隔行
        cs = cells(row)
        body.append('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in cs) + '</tr>')
    body.append('</tbody></table>')
    return ''.join(body)

# ===================== 正文渲染 =====================

def render_blocks(blocks):
    out = []
    heads = []
    hid = 0
    for b in blocks:
        kind = b[0]
        if kind == 'h':
            lv, text = b[1], b[2]
            hid += 1
            out.append('<h' + str(lv) + ' id="sec' + str(hid) + '">' + inline(text) + '</h' + str(lv) + '>')
            heads.append(('sec' + str(hid), lv, slug_text(text)))
        elif kind == 'p':
            out.append('<p>' + inline(b[1]) + '</p>')
        elif kind == 'hr':
            out.append('<hr>')
        elif kind == 'quote':
            out.append('<blockquote>' + ''.join('<p>%s</p>' % inline(x) for x in b[1] if x.strip()) + '</blockquote>')
        elif kind == 'list':
            out.append(render_list(b[2], b[1]))
        elif kind == 'table':
            out.append('<div class="tbl-wrap">' + render_table(b[1]) + '</div>')
        elif kind == 'code':
            lang = b[1]
            code = highlight(b[2], lang)
            lang = lang if lang else 'text'
            out.append('<pre data-lang="%s"><code>%s</code></pre>' % (_escape(lang), code))
    return '\n'.join(out), heads

def fix_internal_anchors(content, heads):
    """把源 md 里的内部链接 #xxx 重映射到生成标题的 sec-N 锚点"""
    def norm(s):
        s = re.sub(r'^[一二三四五六七八九十百\d]+[、.．:：\-]?', '', s.strip())
        s = re.sub(r'[^A-Za-z0-9\u4e00-\u9fff]+', '', s)
        return s.lower()
    hmap = {}
    for sid, lv, text in heads:
        hmap[norm(text)] = sid
    def rep(m):
        sid = hmap.get(norm(m.group(1)))
        return 'href="#%s"' % sid if sid else m.group(0)
    return re.sub(r'href="#([^"]+)"', rep, content)

# ===================== HTML 模板 =====================

# ---- 10 套配色（t1 为默认；面板色块即各主题的 --accent）----
VAR_ORDER = ('bg', 'card', 'ink', 'muted', 'line', 'accent', 'accent-soft', 'on-accent',
             'quote-ink', 'code-bg', 'code-ink', 'code-muted',
             'code-inline-bg', 'code-inline-ink', 'row', 'topbar')

THEMES = {
    't1': {'name': '翠竹绿', 'vars': {
        'bg': '#f6f4ef', 'card': '#fff', 'ink': '#26272e', 'muted': '#6b6d76', 'line': '#e4e0d6',
        'accent': '#1f6f5c', 'accent-soft': '#e9f3ee', 'on-accent': '#fff', 'quote-ink': '#33443e',
        'code-bg': '#22242b', 'code-ink': '#e9eaee', 'code-muted': '#8b93a1',
        'code-inline-bg': '#eef0f3', 'code-inline-ink': '#b3426b', 'row': '#faf9f6', 'topbar': 'rgba(246,244,239,.95)'}},
    't2': {'name': '海盐蓝', 'vars': {
        'bg': '#f2f6fa', 'card': '#fff', 'ink': '#232a35', 'muted': '#66707e', 'line': '#dde6ef',
        'accent': '#2563a8', 'accent-soft': '#e8f0fa', 'on-accent': '#fff', 'quote-ink': '#2c3a4a',
        'code-bg': '#1f2733', 'code-ink': '#e8ecf3', 'code-muted': '#7f8b9c',
        'code-inline-bg': '#e9eff7', 'code-inline-ink': '#a04060', 'row': '#f6f9fc', 'topbar': 'rgba(242,246,250,.95)'}},
    't3': {'name': '墨黛青', 'vars': {
        'bg': '#f1f6f5', 'card': '#fff', 'ink': '#243231', 'muted': '#62716f', 'line': '#d9e6e4',
        'accent': '#0f766e', 'accent-soft': '#e3f0ee', 'on-accent': '#fff', 'quote-ink': '#2b3f3d',
        'code-bg': '#152a28', 'code-ink': '#e6eeed', 'code-muted': '#7c8d8b',
        'code-inline-bg': '#e7f1ef', 'code-inline-ink': '#a83c5a', 'row': '#f5faf9', 'topbar': 'rgba(241,246,245,.95)'}},
    't4': {'name': '紫罗兰', 'vars': {
        'bg': '#f7f5fa', 'card': '#fff', 'ink': '#292630', 'muted': '#6f6a7c', 'line': '#e5e0ee',
        'accent': '#6d4fc4', 'accent-soft': '#f0ebfb', 'on-accent': '#fff', 'quote-ink': '#3c3650',
        'code-bg': '#221e2e', 'code-ink': '#ece9f3', 'code-muted': '#8f87a3',
        'code-inline-bg': '#f0ecf8', 'code-inline-ink': '#a43d76', 'row': '#faf8fd', 'topbar': 'rgba(247,245,250,.95)'}},
    't5': {'name': '珊瑚橘', 'vars': {
        'bg': '#faf4ef', 'card': '#fff', 'ink': '#2c2722', 'muted': '#78695d', 'line': '#ecdccf',
        'accent': '#b5531d', 'accent-soft': '#fbeeda', 'on-accent': '#fff', 'quote-ink': '#4a3a2a',
        'code-bg': '#2b2118', 'code-ink': '#f2ebe2', 'code-muted': '#97806c',
        'code-inline-bg': '#f7ecdf', 'code-inline-ink': '#b03a4e', 'row': '#fcf7f1', 'topbar': 'rgba(250,244,239,.95)'}},
    't6': {'name': '胭脂红', 'vars': {
        'bg': '#faf2f3', 'card': '#fff', 'ink': '#2e2426', 'muted': '#7c666b', 'line': '#eedfe2',
        'accent': '#b33a54', 'accent-soft': '#fbe9ec', 'on-accent': '#fff', 'quote-ink': '#4e2f36',
        'code-bg': '#2b1a1f', 'code-ink': '#f3eaec', 'code-muted': '#a07a82',
        'code-inline-bg': '#f9e9eb', 'code-inline-ink': '#b3426b', 'row': '#fdf7f8', 'topbar': 'rgba(250,242,243,.95)'}},
    't7': {'name': '琥珀金', 'vars': {
        'bg': '#faf5ec', 'card': '#fff', 'ink': '#2e2a21', 'muted': '#7a6f5c', 'line': '#ecdfca',
        'accent': '#a06a1e', 'accent-soft': '#f7ead3', 'on-accent': '#fff', 'quote-ink': '#504228',
        'code-bg': '#2b2418', 'code-ink': '#f1ecdf', 'code-muted': '#9a8b70',
        'code-inline-bg': '#f6ecdb', 'code-inline-ink': '#9c3d47', 'row': '#fdf9f1', 'topbar': 'rgba(250,245,236,.95)'}},
    't8': {'name': '石墨岩', 'vars': {
        'bg': '#f3f4f6', 'card': '#fff', 'ink': '#272a31', 'muted': '#666b74', 'line': '#dcdde2',
        'accent': '#3f5468', 'accent-soft': '#e8ecf1', 'on-accent': '#fff', 'quote-ink': '#33424f',
        'code-bg': '#1f232a', 'code-ink': '#e8eaee', 'code-muted': '#7e848d',
        'code-inline-bg': '#eaecef', 'code-inline-ink': '#9c3f5c', 'row': '#f7f8fa', 'topbar': 'rgba(243,244,246,.95)'}},
    't9': {'name': '莓果粉', 'vars': {
        'bg': '#faf3f6', 'card': '#fff', 'ink': '#2d242a', 'muted': '#79636d', 'line': '#eedfe6',
        'accent': '#a34f86', 'accent-soft': '#f9eaf2', 'on-accent': '#fff', 'quote-ink': '#4e2f42',
        'code-bg': '#291b24', 'code-ink': '#f1e7ec', 'code-muted': '#a0798b',
        'code-inline-bg': '#f8eaf1', 'code-inline-ink': '#a03a5c', 'row': '#fdf7fa', 'topbar': 'rgba(250,243,246,.95)'}},
    't10': {'name': '曜石黑', 'vars': {
        'bg': '#16181d', 'card': '#1d2026', 'ink': '#e6e8ee', 'muted': '#9aa0ab', 'line': '#2c3038',
        'accent': '#5ec9a7', 'accent-soft': '#1d2a26', 'on-accent': '#12211c', 'quote-ink': '#a7d6c4',
        'code-bg': '#0e1013', 'code-ink': '#e6e9ef', 'code-muted': '#6b7280',
        'code-inline-bg': '#262b33', 'code-inline-ink': '#e58aae', 'row': '#1a1d23', 'topbar': 'rgba(22,24,29,.92)'}},
}

def theme_css():
    out = []
    for tid, t in THEMES.items():
        sel = ':root' if tid == 't1' else 'html[data-theme="%s"]' % tid
        out.append(sel + '{' + ''.join('--%s:%s;' % (k, t['vars'][k]) for k in VAR_ORDER) + '}')
    return '\n'.join(out)

def theme_panel_html():
    items = ''.join(
        '<button class="tp-item" data-t="%s" aria-label="%s">'
        '<i style="background:%s"></i><span>%s</span></button>' % (tid, t['name'], t['vars']['accent'], t['name'])
        for tid, t in THEMES.items())
    return ('<button class="theme-btn" id="theme-btn" aria-label="切换配色">'
            '<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">'
            '<path d="M12 3a9 9 0 1 0 0 18c.83 0 1.5-.67 1.5-1.5 0-.39-.15-.74-.39-1.01-.23-.26-.38-.61-.38-1.01 0-.83.67-1.5 1.5-1.5H16a5 5 0 0 0 5-5c0-4.42-4.03-8-9-8z'
            'm-5.5 9a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3-4.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm4.5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zM17 11a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"/></svg></button>\n'
            '<div class="theme-panel" id="theme-panel" role="dialog" aria-label="选择配色">\n'
            '<div class="tp-title">选择配色</div>\n<div class="tp-grid">' + items + '</div>\n</div>\n')

BASE_CSS = """
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.8 "Microsoft YaHei","PingFang SC","Segoe UI",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent;overflow-wrap:anywhere}
a:hover{border-bottom-color:var(--accent)}
img{max-width:100%;height:auto;border-radius:8px}
h1{font-size:29px;line-height:1.35;margin:1.6em 0 .7em}
h2{font-size:23px;line-height:1.4;margin:2.2em 0 .7em;padding-bottom:.32em;border-bottom:2px solid var(--line);position:relative}
h2::after{content:"";position:absolute;left:0;bottom:-2px;width:58px;height:2px;background:var(--accent)}
h3{font-size:18.5px;line-height:1.45;margin:1.7em 0 .55em;color:var(--accent)}
p{margin:.65em 0;max-width:72ch;overflow-wrap:anywhere}
hr{border:0;border-top:1px solid var(--line);margin:2.4em 0}
blockquote{margin:1.1em 0;padding:.7em 1.1em;background:var(--accent-soft);border-left:4px solid var(--accent);border-radius:0 10px 10px 0;color:var(--quote-ink)}
blockquote p{margin:.3em 0}
ul,ol{margin:.6em 0;padding-left:1.5em}
li{margin:.28em 0;overflow-wrap:anywhere}
li>ul{margin:.2em 0}
code{font-family:"Cascadia Code","Consolas","JetBrains Mono",monospace;font-size:.88em;background:var(--code-inline-bg);color:var(--code-inline-ink);padding:.14em .4em;border-radius:5px;overflow-wrap:anywhere;word-break:break-all}
pre{position:relative;background:var(--code-bg);color:var(--code-ink);border-radius:12px;padding:1.1em 1.2em 1.1em 1.2em;overflow-x:auto;margin:1.2em 0;font-family:"Cascadia Code","Consolas","JetBrains Mono",monospace;font-size:13.5px;line-height:1.65}
pre code{background:none;color:inherit;padding:0;font-size:inherit}
pre::before{content:attr(data-lang);position:absolute;top:10px;right:14px;font-size:11px;color:var(--code-muted);letter-spacing:.05em}
.t-k{color:#7ec699}
.t-s{color:#e5c07b}
.t-n{color:#61afef}
.t-c{color:#7f848e;font-style:italic}
.tbl-wrap{overflow-x:auto;margin:1.2em 0;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:14.5px}
th{background:var(--accent);color:var(--on-accent);font-weight:600;text-align:left;padding:10px 14px;white-space:nowrap}
td{padding:9px 14px;border-top:1px solid var(--line);vertical-align:top}
tbody tr:nth-child(even){background:var(--row)}
td .mono,th .mono{font-family:"Cascadia Code","Consolas",monospace;white-space:normal;overflow-wrap:break-word;word-break:break-all}
/* ---- 配色选择器（横屏/竖屏共用）---- */
.theme-btn{position:fixed;right:22px;bottom:78px;z-index:135;width:46px;height:46px;border:0;border-radius:50%;background:var(--accent);color:var(--on-accent);cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 14px rgba(0,0,0,.14)}
.theme-btn:hover{filter:brightness(1.08)}
.theme-panel{position:fixed;right:22px;bottom:134px;z-index:136;width:218px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;box-shadow:0 10px 30px rgba(0,0,0,.16);opacity:0;pointer-events:none;transform:translateY(8px);transition:.22s}
.theme-panel.open{opacity:1;pointer-events:auto;transform:none}
.tp-title{font-size:12.5px;color:var(--muted);margin:0 2px 8px;letter-spacing:.05em}
.tp-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.tp-item{display:flex;align-items:center;gap:8px;min-height:44px;padding:6px 8px;border:1px solid transparent;border-radius:9px;background:none;color:var(--ink);font:inherit;font-size:13.5px;cursor:pointer;text-align:left;line-height:1.3}
.tp-item:hover{background:var(--accent-soft)}
.tp-item.sel{border-color:var(--accent);background:var(--accent-soft);font-weight:600}
.tp-item i{width:17px;height:17px;border-radius:50%;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.12)}
"""

LAYOUT_DESKTOP = """
.topbar{position:sticky;top:0;z-index:120;display:none;align-items:center;gap:10px;height:52px;padding:0 14px;background:var(--topbar);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.topbar .tb-title{font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.menu-btn{width:44px;height:44px;flex:none;border:1px solid var(--line);border-radius:9px;background:var(--card);color:var(--ink);cursor:pointer;display:flex;align-items:center;justify-content:center}
.side{position:fixed;left:0;top:0;bottom:0;width:284px;background:var(--card);border-right:1px solid var(--line);padding:20px 14px 40px;overflow-y:auto;z-index:110}
.side-head{padding:4px 8px 14px;border-bottom:1px solid var(--line);margin-bottom:10px}
.side-title{font-size:16.5px;font-weight:700;line-height:1.45;color:var(--accent)}
.side-sub{font-size:12px;color:var(--muted);margin-top:5px}
#toc{display:flex;flex-direction:column;gap:2px}
#toc a{display:block;padding:6px 8px;border-radius:7px;color:var(--ink);font-size:14px;line-height:1.45;border-left:2px solid transparent}
#toc a:hover{background:var(--accent-soft);border-bottom-color:transparent}
#toc a.active{background:var(--accent);color:var(--on-accent);font-weight:600}
#toc .toc-l3{padding-left:26px;font-size:13px;color:var(--muted)}
.main{margin-left:300px;padding:26px 40px 60px;max-width:960px}
.main>h1:first-child{font-size:33px;margin-top:.4em}
.mask{position:fixed;inset:0;background:rgba(35,33,28,.4);z-index:105;opacity:0;pointer-events:none;transition:opacity .22s}
.totop{position:fixed;right:22px;bottom:24px;z-index:130;width:46px;height:46px;border:0;border-radius:12px;background:var(--accent);color:var(--on-accent);font-size:19px;cursor:pointer;opacity:0;pointer-events:none;transform:translateY(8px);transition:.25s}
.totop.show{opacity:1;pointer-events:auto;transform:none}
@media (max-width:960px){
  .side{transform:translateX(-102%);transition:transform .26s;box-shadow:none}
  .side.open{transform:none;box-shadow:2px 0 18px rgba(0,0,0,.12)}
  .mask.show{opacity:1;pointer-events:auto}
  .main{margin-left:0;padding:18px 16px 60px}
  .topbar{display:flex}
}
@media (max-width:719px){
  body{font-size:16px}
  .main{padding:14px 14px 60px}
  #toc a{min-height:44px;display:flex;align-items:center}
  h1{font-size:26px}
  h2{font-size:21px}
  h3{font-size:17px}
  td,th{font-size:13.8px;padding:8px 10px}
  .tbl-wrap{overflow:visible;border:none;background:none}
  table{min-width:0}
  thead{display:none}
  tbody tr{display:block;border:1px solid var(--line);border-radius:10px;margin:10px 0;background:var(--card);padding:4px 0}
  tbody td{display:block;width:100%;border:none;padding:7px 14px;font-size:14.5px;overflow-wrap:anywhere;word-break:break-word}
  tbody td::before{content:attr(data-label);display:block;font-size:11.5px;color:var(--muted);margin-bottom:2px;letter-spacing:.04em}
  tbody td:first-child{font-weight:600}
  pre{padding:1em .9em;font-size:12.5px}
}
"""

LAYOUT_PORTRAIT = """
.topbar{position:sticky;top:0;z-index:120;display:flex;align-items:center;gap:10px;height:52px;padding:0 14px;background:var(--topbar);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.topbar .tb-title{font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.menu-btn{width:44px;height:44px;flex:none;border:1px solid var(--line);border-radius:9px;background:var(--card);color:var(--ink);cursor:pointer;display:flex;align-items:center;justify-content:center}
.side{position:fixed;left:0;top:0;bottom:0;width:min(300px,84vw);background:var(--card);border-right:1px solid var(--line);padding:18px 14px 40px;overflow-y:auto;z-index:110;transform:translateX(-102%);transition:transform .26s}
.side.open{transform:none;box-shadow:2px 0 18px rgba(0,0,0,.12)}
.side-head{padding:4px 8px 14px;border-bottom:1px solid var(--line);margin-bottom:10px}
.side-title{font-size:16.5px;font-weight:700;line-height:1.45;color:var(--accent)}
.side-sub{font-size:12px;color:var(--muted);margin-top:5px}
#toc{display:flex;flex-direction:column;gap:2px}
#toc a{display:block;padding:7px 8px;border-radius:7px;color:var(--ink);font-size:14.5px;line-height:1.5;min-height:44px;display:flex;align-items:center;border-left:2px solid transparent}
#toc a:hover{background:var(--accent-soft);border-bottom-color:transparent}
#toc a.active{background:var(--accent);color:var(--on-accent);font-weight:600}
#toc .toc-l3{padding-left:26px;font-size:13px;color:var(--muted)}
.main{max-width:680px;margin:0 auto;padding:20px 16px 70px}
.main>h1:first-child{font-size:30px;margin-top:.3em}
.mask{position:fixed;inset:0;background:rgba(35,33,28,.4);z-index:105;opacity:0;pointer-events:none;transition:opacity .22s}
.mask.show{opacity:1;pointer-events:auto}
.totop{position:fixed;right:16px;bottom:22px;z-index:130;width:46px;height:46px;border:0;border-radius:12px;background:var(--accent);color:var(--on-accent);font-size:19px;cursor:pointer;opacity:0;pointer-events:none;transform:translateY(8px);transition:.25s}
.totop.show{opacity:1;pointer-events:auto;transform:none}
.theme-btn{right:16px}
.theme-panel{right:16px}
@media (max-width:719px){
  body{font-size:16px}
  .main{padding:14px 14px 70px}
  h1{font-size:26px}
  h2{font-size:21px}
  h3{font-size:17px}
  td,th{font-size:13.8px;padding:8px 10px}
  .tbl-wrap{overflow:visible;border:none;background:none;margin:1em 0}
  table{min-width:0}
  thead{display:none}
  tbody tr{display:block;border:1px solid var(--line);border-radius:10px;margin:10px 0;background:var(--card);padding:4px 0}
  tbody td{display:block;width:100%;border:none;padding:7px 14px;font-size:14.5px;overflow-wrap:anywhere;word-break:break-word}
  tbody td::before{content:attr(data-label);display:block;font-size:11.5px;color:var(--muted);margin-bottom:2px;letter-spacing:.04em}
  tbody td:first-child{font-weight:600}
  pre{padding:1em .9em;font-size:12.5px}
}
"""

JS = """
(function(){
  var side=document.getElementById('side'),mask=document.getElementById('mask'),
      menu=document.getElementById('menu-btn'),totop=document.getElementById('totop');
  var heads=Array.prototype.slice.call(document.querySelectorAll('.main h1,.main h2,.main h3'));
  var toc=document.getElementById('toc');
  heads.forEach(function(h){
    var a=document.createElement('a');
    a.href='#'+h.id;
    a.className='toc-l'+parseInt(h.tagName[1],10);
    a.textContent=h.textContent;
    a.addEventListener('click',closeSide);
    toc.appendChild(a);
  });
  function closeSide(){side.classList.remove('open');mask.classList.remove('show');}
  function openSide(){side.classList.add('open');mask.classList.add('show');}
  menu.addEventListener('click',function(){ if(side.classList.contains('open'))closeSide();else openSide(); });
  mask.addEventListener('click',closeSide);
  document.addEventListener('keydown',function(e){ if(e.key==='Escape')closeSide(); });
  function onScroll(){
    var st=window.pageYOffset||document.documentElement.scrollTop,cur=-1;
    for(var i=0;i<heads.length;i++){ if(heads[i].getBoundingClientRect().top<=130) cur=i; }
    var links=toc.children;
    for(var j=0;j<links.length;j++){ links[j].classList.toggle('active',j===cur); }
    totop.classList.toggle('show',st>600);
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  totop.addEventListener('click',function(){ window.scrollTo({top:0,behavior:'smooth'}); });
  document.querySelectorAll('.main table').forEach(function(t){
    var ths=Array.prototype.slice.call(t.querySelectorAll('thead th'));
    if(!ths.length)return;
    Array.prototype.slice.call(t.querySelectorAll('tbody tr')).forEach(function(tr){
      Array.prototype.slice.call(tr.children).forEach(function(td,i){
        if(ths[i])td.setAttribute('data-label',ths[i].textContent.trim());
      });
    });
  });
  onScroll();
  /* ---- 配色切换 ---- */
  var themeBtn=document.getElementById('theme-btn'),
      themePanel=document.getElementById('theme-panel');
  var themeIds=['t1','t2','t3','t4','t5','t6','t7','t8','t9','t10'];
  var savedTheme=null;
  try{ savedTheme=localStorage.getItem('md2html-theme'); }catch(e){}
  function applyTheme(t){
    document.documentElement.setAttribute('data-theme',t);
    var items=themePanel.querySelectorAll('.tp-item');
    for(var i=0;i<items.length;i++){ items[i].classList.toggle('sel',items[i].getAttribute('data-t')===t); }
    try{ localStorage.setItem('md2html-theme',t); }catch(e){}
  }
  themeBtn.addEventListener('click',function(e){ e.stopPropagation(); themePanel.classList.toggle('open'); });
  themePanel.addEventListener('click',function(e){
    var b=e.target.closest?e.target.closest('.tp-item'):null;
    if(b){ applyTheme(b.getAttribute('data-t')); themePanel.classList.remove('open'); }
  });
  document.addEventListener('click',function(e){
    if(themePanel.classList.contains('open')&&!themePanel.contains(e.target)&&e.target!==themeBtn&&!themeBtn.contains(e.target)){
      themePanel.classList.remove('open');
    }
  });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape')themePanel.classList.remove('open'); });
  if(savedTheme&&themeIds.indexOf(savedTheme)>=0){ applyTheme(savedTheme); }
})();
"""

# ===================== 主流程 =====================

def read_md(path):
    """自动识别编码：UTF-8 → GBK"""
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('utf-8', 'gbk', 'utf-16'):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode('utf-8', errors='replace')

def slug_text(s):
    """取纯文本（去掉行内 markdown 符号）"""
    return re.sub(r'[`*_~\[\]\(\)#!|]', '', s).strip()

THEME_CONF = '_theme.conf'


def default_theme():
    """默认配色：优先读工具目录下的 _theme.conf（由「设置默认配色.bat」写入），否则 t1。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), THEME_CONF)
        if os.path.isfile(p):
            v = open(p, encoding='utf-8').read().strip()
            if v in THEMES:
                return v
    except Exception:
        pass
    return 't1'


def gen_html(md_path, mode, default_theme='t1'):
    if default_theme not in THEMES:
        default_theme = 't1'
    text = read_md(md_path)
    blocks = parse_blocks(text.splitlines())
    title = ''
    for b in blocks:
        if b[0] == 'h' and b[1] == 1:
            title = slug_text(b[2])
            break
    if not title:
        title = os.path.splitext(os.path.basename(md_path))[0]

    content, heads = render_blocks(blocks)
    content = fix_internal_anchors(content, heads)
    layout = LAYOUT_DESKTOP if mode == 'desktop' else LAYOUT_PORTRAIT
    if mode == 'desktop':
        out_path = os.path.splitext(md_path)[0] + '.html'
    else:
        out_path = os.path.splitext(md_path)[0] + '-竖屏版.html'

    date_s = time.strftime('%Y-%m-%d')
    esc = _html.escape
    favicon = ('<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' '
               'viewBox=\'0 0 64 64\'%3E%3Crect width=\'64\' height=\'64\' rx=\'14\' fill=\'%231F6F5C\'/%3E'
               '%3Ctext x=\'32\' y=\'45\' font-size=\'34\' text-anchor=\'middle\' fill=\'white\'%3E%E6%96%87%3C/text%3E%3C/svg%3E">\n')
    menu_btn = ('<button class="menu-btn" id="menu-btn" aria-label="打开目录">'
                '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
                'stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg></button>\n')
    html_doc = (
        '<!DOCTYPE html>\n<html lang="zh-CN" data-theme="' + default_theme + '">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n' + favicon +
        '<title>' + esc(title) + '</title>\n<style>' + theme_css() + '\n' + BASE_CSS + '\n' + layout + '</style>\n</head>\n<body>\n'
        '<header class="topbar">\n' + menu_btn +
        '<span class="tb-title">' + esc(title) + '</span>\n</header>\n'
        '<aside class="side" id="side">\n<div class="side-head">\n<div class="side-title">' + esc(title) + '</div>\n'
        '<div class="side-sub">目录 · 由 md2html 本地工具生成</div>\n</div>\n<nav id="toc"></nav>\n</aside>\n'
        '<div class="mask" id="mask"></div>\n' + theme_panel_html() +
        '<main class="main">\n' + content + '\n'
        '<hr>\n<footer style="color:var(--muted);font-size:13px;padding:1em 0 2em">'
        '由 md2html 本地工具生成 · ' + date_s + ' · 与源文件同目录打开，相对路径图片可正常显示</footer>\n</main>\n'
        '<button class="totop" id="totop" aria-label="回到顶部">&#8593;</button>\n'
        '<script>' + JS + '</script>\n</body>\n</html>'
    )
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_doc)
    return out_path, title

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python md2html.py <xxx.md> [desktop|portrait] [--theme t1..t10]')
        sys.exit(1)
    src = sys.argv[1]
    mode = 'desktop'
    theme = default_theme()
    rest = sys.argv[2:]
    for i, a in enumerate(rest):
        if a == '--theme' and i + 1 < len(rest):
            theme = rest[i + 1]
        elif a in ('desktop', 'portrait'):
            mode = a
    if not os.path.exists(src):
        print('文件不存在: %s' % src)
        sys.exit(1)
    try:
        out, title = gen_html(src, mode, default_theme=theme)
        print('OK  → %s  （模式: %s，配色: %s）' % (out, mode, THEMES.get(theme, {}).get('name', theme)))
    except Exception as e:
        print('转换失败: %s' % e)
        sys.exit(1)
