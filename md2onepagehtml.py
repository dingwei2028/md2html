# -*- coding: utf-8 -*-
r"""
md2onepagehtml —— 把一个目录下的多份 Markdown 合并成一个单文件 HTML。

与 md2html.py 共用同一套引擎（同目录 import），零第三方依赖、完全离线。

用法:
  python md2onepagehtml.py <目录> [-o 输出.html] [--title 标题] [--theme t1..t10]
                           [--portrait] [--recursive] [--no-inline-img]
                           [--fetch-remote-img] [--base-url URL] [--exclude 关键字]

常用:
  python md2onepagehtml.py D:\docs                    # 目录下所有 md -> D:\docs\docs.html
  python md2onepagehtml.py D:\docs -o 合集.html --portrait
  python md2onepagehtml.py D:\docs --recursive --theme t10
"""
import argparse
import base64
import html as _html
import mimetypes
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from md2html import (  # noqa: E402  复用同目录引擎
    BASE_CSS, LAYOUT_DESKTOP, LAYOUT_PORTRAIT, THEMES,
    fix_internal_anchors, parse_blocks, read_md, render_blocks,
    slug_text, theme_css, theme_panel_html,
)

UA = {"User-Agent": "Mozilla/5.0 (compatible; md2onepagehtml)"}
FIRST = ("readme.md", "index.md", "_index.md", "readme.markdown")


# ---------------------------------------------------------------- 素材定位
def detect_git_base(root):
    """从 git remote 推断 raw / blob 前缀，用于补全相对图片与相对链接。"""
    try:
        out = subprocess.run(["git", "-C", root, "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10)
        url = (out.stdout or "").strip()
        if not url:
            return None, None
        m = re.match(r"(?:https?://|git@)([^/:]+)[/:](.+?)(?:\.git)?$", url)
        if not m:
            return None, None
        host, path = m.group(1), m.group(2)
        br = subprocess.run(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, timeout=10)
        branch = (br.stdout or "").strip() or "master"
        if "github" in host:
            return (f"https://raw.githubusercontent.com/{path}/{branch}/",
                    f"https://github.com/{path}/blob/{branch}/")
        return None, None
    except Exception:
        return None, None


def _default_branch(path, cache):
    """查 GitHub 仓库默认分支（带缓存）。"""
    if path in cache:
        return cache[path]
    br = "master"
    try:
        req = urllib.request.Request("https://api.github.com/repos/" + path, headers=UA)
        data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        m = re.search(r'"default_branch"\s*:\s*"([^"]+)"', data)
        if m:
            br = m.group(1)
    except Exception:
        pass
    cache[path] = br
    return br


def parse_index_map(root):
    """目录里有 _index.md 时，解析出「文件名 -> 仓库 URL」，用于逐篇补全图片/链接。

    _index.md 里形如  | `nanoGPT.README.md` | [nanoGPT](https://github.com/karpathy/nanoGPT) |  的表格行。
    """
    m = {}
    p = os.path.join(root, "_index.md")
    if not os.path.isfile(p):
        return m
    pat = re.compile(r"\|\s*`([^`]+)`\s*\|\s*\[([^\]]+)\]\((https?://github\.com/[^)\s]+)\)")
    for line in read_md(p).splitlines():
        mm = pat.search(line)
        if mm:
            m[mm.group(1).strip()] = mm.group(3).rstrip("/")
    return m


def repo_bases(url, cache):
    """github.com/u/r -> (raw 前缀, blob 前缀)"""
    mm = re.match(r"https?://github\.com/([^/]+/[^/]+)", url)
    if not mm:
        return None, None
    path = mm.group(1)
    br = _default_branch(path, cache)
    return (f"https://raw.githubusercontent.com/{path}/{br}/",
            f"https://github.com/{path}/blob/{br}/")


def collect_mds(root, recursive=False, exclude=()):
    files = []
    if recursive:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if not d.startswith(".")]
            for fn in fns:
                if fn.lower().endswith((".md", ".markdown")):
                    files.append(os.path.join(dp, fn))
    else:
        for fn in os.listdir(root):
            if fn.lower().endswith((".md", ".markdown")):
                files.append(os.path.join(root, fn))
    if exclude:
        files = [f for f in files
                 if not any(x.lower() in os.path.basename(f).lower() for x in exclude)]
    files.sort(key=lambda f: (0 if os.path.basename(f).lower() in FIRST else 1,
                              os.path.basename(f).lower()))
    return files


# ---------------------------------------------------------------- 图片 / 链接
_img_cache = {}


def _b64(data, path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    if path.lower().endswith(".svg"):
        mime = "image/svg+xml"
    return "data:" + mime + ";base64," + base64.b64encode(data).decode("ascii")


def _fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def inline_images(content, md_dir, raw_base, fetch_remote, log):
    """把图片内联成 data URI，让产物真正是单文件。"""
    def repl(m):
        src = _html.unescape(m.group(1))
        if src.startswith("data:"):
            return m.group(0)
        key = (src, md_dir)
        if key in _img_cache:
            return '<img src="' + _img_cache[key] + '"'
        new = None
        try:
            if src.startswith(("http://", "https://")):
                if fetch_remote:
                    new = _b64(_fetch(src), src)
            else:
                fp = os.path.normpath(os.path.join(md_dir, src.split("?")[0]))
                if os.path.isfile(fp):
                    with open(fp, "rb") as f:
                        new = _b64(f.read(), fp)
                elif raw_base:
                    new = _b64(_fetch(raw_base + src.lstrip("/")), src)
        except Exception as e:
            log.append("  图片失败 %s (%s)" % (src, e))
        if new is None:
            _img_cache[key] = src
            return m.group(0)
        _img_cache[key] = new
        return '<img src="' + new + '"'
    return re.sub(r'<img src="([^"]+)"', repl, content)


def fix_links(content, blob_base):
    """相对链接改写成远端 blob 地址，避免合并后点击失效。"""
    if not blob_base:
        return content

    def repl(m):
        href = _html.unescape(m.group(1))
        if href.startswith(("#", "http", "mailto:", "data:")):
            return m.group(0)
        return '<a href="' + blob_base + href.lstrip("./") + '" target="_blank" rel="noopener"'
    return re.sub(r'<a href="([^"]+)"', repl, content)


# ---------------------------------------------------------------- 单篇渲染
def render_one(path, idx, raw_base, blob_base, fetch_remote, do_inline, log):
    text = read_md(path)
    blocks = parse_blocks(text.splitlines())

    title = None
    for i, b in enumerate(blocks):
        if b[0] == "h" and b[1] == 1:
            title = slug_text(b[2])
            del blocks[i]
            break
    if not title:
        title = os.path.splitext(os.path.basename(path))[0]

    content, heads = render_blocks(blocks)

    # 锚点加篇前缀，避免多篇之间 sec-N 撞车
    pfx = "d%d-" % idx
    content = re.sub(r'id="(sec\d+)"', lambda m: 'id="' + pfx + m.group(1) + '"', content)
    heads = [(pfx + sid, lv, t) for sid, lv, t in heads]
    content = fix_internal_anchors(content, heads)

    md_dir = os.path.dirname(os.path.abspath(path))
    if do_inline:
        content = inline_images(content, md_dir, raw_base, fetch_remote, log)
    content = fix_links(content, blob_base)
    return title, content, heads


# ---------------------------------------------------------------- 页面组装
EXTRA_CSS = """
/* ---- 多篇合并专用 ---- */
.doc{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:6px 26px 26px;margin:0 0 26px;scroll-margin-top:16px}
.doc-title{font-size:27px;margin:.7em 0 .35em}
.doc-title::before{content:"";display:block;width:46px;height:3px;background:var(--accent);
  border-radius:2px;margin-bottom:.5em}
.doc-meta{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 1.1em;padding-bottom:.9em;
  border-bottom:1px dashed var(--line)}
.chip{font-size:12px;line-height:1.6;padding:2px 9px;border-radius:20px;
  background:var(--accent-soft);color:var(--muted);border:1px solid var(--line)}
.chip.src{font-family:Consolas,monospace;font-size:11px}
.doc-body>h1:first-child,.doc-body>h2:first-child{margin-top:.6em}
.doc-body h1{font-size:24px}
/* ---- 侧栏 ---- */
#q{width:100%;padding:7px 10px;margin:10px 0 8px;border:1px solid var(--line);
  border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;font-size:13px}
#q:focus{outline:2px solid var(--accent);outline-offset:-1px}
#toc a{display:block;padding:6px 8px;border-radius:7px;color:var(--ink);font-size:14px;
  line-height:1.45;border-left:2px solid transparent;overflow-wrap:anywhere}
#toc a:hover{background:var(--accent-soft);border-bottom-color:transparent}
#toc a.active{background:var(--accent);color:var(--on-accent);font-weight:600;border-left-color:var(--accent)}
#toc .toc-doc{font-weight:600;color:var(--accent);margin-top:9px;font-size:14.5px}
#toc .toc-doc.active{color:var(--on-accent)}
#toc .toc-l1,#toc .toc-l2{padding-left:18px;font-size:13.5px}
#toc .toc-l3{padding-left:32px;font-size:12.5px;color:var(--muted)}
#toc .toc-l3.active{color:var(--on-accent)}
.side-foot{margin:16px 8px;font-size:11.5px;color:var(--muted);line-height:1.7}
a.dead{color:var(--muted);border-bottom:1px dashed var(--line);cursor:help}
.doc-foot{color:var(--muted);font-size:13px;padding:.4em 0 1em}
@media (max-width:719px){.doc{padding:2px 15px 18px;border-radius:12px}.doc-title{font-size:23px}}
"""

JS = """
(function(){
  var side=document.getElementById('side'),mask=document.getElementById('mask'),
      menu=document.getElementById('menu-btn'),totop=document.getElementById('totop'),
      toc=document.getElementById('toc'),q=document.getElementById('q');
  var heads=Array.prototype.slice.call(document.querySelectorAll('.main h1,.main h2,.main h3'));
  var links=Array.prototype.slice.call(toc.children);
  function closeSide(){side.classList.remove('open');mask.classList.remove('show');}
  menu.addEventListener('click',function(){
    if(side.classList.contains('open'))closeSide();
    else{side.classList.add('open');mask.classList.add('show');}
  });
  mask.addEventListener('click',closeSide);
  links.forEach(function(a){a.addEventListener('click',closeSide);});

  /* 目录过滤 */
  q.addEventListener('input',function(){
    var v=q.value.trim().toLowerCase();
    links.forEach(function(a){
      var t=a.getAttribute('data-t')||a.textContent;
      a.style.display=(!v||t.toLowerCase().indexOf(v)>=0)?'':'none';
    });
  });

  function onScroll(){
    var cur=-1;
    for(var i=0;i<heads.length;i++){if(heads[i].getBoundingClientRect().top<=130)cur=i;}
    for(var j=0;j<links.length;j++){links[j].classList.toggle('active',j===cur);}
    totop.classList.toggle('show',(window.pageYOffset||document.documentElement.scrollTop)>600);
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  totop.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeSide();});

  /* 窄屏表格转卡片 */
  document.querySelectorAll('.main table').forEach(function(t){
    var ths=Array.prototype.slice.call(t.querySelectorAll('thead th'));
    if(!ths.length)return;
    Array.prototype.slice.call(t.querySelectorAll('tbody tr')).forEach(function(tr){
      Array.prototype.slice.call(tr.children).forEach(function(td,i){
        if(ths[i])td.setAttribute('data-label',ths[i].textContent.trim());
      });
    });
  });
  /* 加载不出来的图片直接隐藏 */
  Array.prototype.slice.call(document.querySelectorAll('img')).forEach(function(i){
    i.addEventListener('error',function(){i.style.display='none';});
    if(i.complete&&i.naturalWidth===0)i.style.display='none';
  });
  onScroll();

  /* ---- 配色切换（与 md2html 一致，记忆在 localStorage）---- */
  var themeBtn=document.getElementById('theme-btn'),themePanel=document.getElementById('theme-panel');
  var themeIds=['t1','t2','t3','t4','t5','t6','t7','t8','t9','t10'],saved=null;
  try{saved=localStorage.getItem('md2html-theme');}catch(e){}
  function applyTheme(t){
    document.documentElement.setAttribute('data-theme',t);
    var items=themePanel.querySelectorAll('.tp-item');
    for(var i=0;i<items.length;i++){items[i].classList.toggle('sel',items[i].getAttribute('data-t')===t);}
    try{localStorage.setItem('md2html-theme',t);}catch(e){}
  }
  themeBtn.addEventListener('click',function(e){e.stopPropagation();themePanel.classList.toggle('open');});
  themePanel.addEventListener('click',function(e){
    var b=e.target.closest?e.target.closest('.tp-item'):null;
    if(b){applyTheme(b.getAttribute('data-t'));themePanel.classList.remove('open');}
  });
  document.addEventListener('click',function(e){
    if(themePanel.classList.contains('open')&&!themePanel.contains(e.target)
       &&e.target!==themeBtn&&!themeBtn.contains(e.target))themePanel.classList.remove('open');
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&themePanel.classList.contains('open'))themePanel.classList.remove('open');
  });
  if(saved&&themeIds.indexOf(saved)>=0)applyTheme(saved);
})();
"""

MENU_BTN = ('<button class="menu-btn" id="menu-btn" aria-label="打开目录">'
            '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>'
            '</button>')
FAVICON = ("<link rel=\"icon\" type=\"image/svg+xml\" href=\"data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='14' fill='%231F6F5C'/%3E"
           "%3Ctext x='32' y='45' font-size='30' text-anchor='middle' fill='white'%3E"
           "%E5%90%88%3C/text%3E%3C/svg%3E\">")


def build(root, out_path, title, theme, portrait, recursive,
          do_inline, fetch_remote, base_url, exclude):
    files = collect_mds(root, recursive, exclude)
    if not files:
        raise SystemExit("目录下没有找到 .md 文件: " + root)

    raw_base = blob_base = None
    if base_url:
        raw_base = base_url if base_url.endswith("/") else base_url + "/"
        blob_base = re.sub(r"github\.com/([^/]+/[^/]+)/", r"github.com/\1/blob/",
                           raw_base.replace("raw.githubusercontent.com", "github.com"), count=1)
    else:
        raw_base, blob_base = detect_git_base(root)

    log, docs, toc = [], [], []
    esc = _html.escape
    t0 = time.time()
    index_map = parse_index_map(root)
    br_cache = {}
    if index_map:                       # 并行预热分支查询，省掉串行等待
        from concurrent.futures import ThreadPoolExecutor
        paths = []
        for u in index_map.values():
            mm = re.match(r"https?://github\.com/([^/]+/[^/]+)", u)
            if mm and mm.group(1) not in paths:
                paths.append(mm.group(1))
        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(lambda p: _default_branch(p, br_cache), paths))

    for idx, path in enumerate(files):
        rel = os.path.relpath(path, root)
        f_raw, f_blob = raw_base, blob_base
        if os.path.basename(path) in index_map:
            f_raw, f_blob = repo_bases(index_map[os.path.basename(path)], br_cache)
        dtitle, content, heads = render_one(
            path, idx, f_raw, f_blob, fetch_remote, do_inline, log)
        docs.append("\n".join([
            '<article class="doc" id="doc-' + str(idx) + '">',
            '<h1 class="doc-title">' + esc(dtitle) + '</h1>',
            '<div class="doc-meta"><span class="chip">' + str(idx + 1) + ' / ' + str(len(files)) +
            '</span><span class="chip src">' + esc(rel) + '</span></div>',
            '<div class="doc-body">',
            content,
            '</div></article>',
        ]))
        toc.append('<a class="toc-doc" href="#doc-' + str(idx) + '" data-t="' +
                   esc(dtitle) + '">' + esc(dtitle) + '</a>')
        for sid, lv, text in heads:
            if lv <= 3:
                toc.append('<a class="toc-l' + str(lv) + '" href="#' + sid + '" data-t="' +
                           esc(slug_text(text)) + '">' + esc(slug_text(text)) + '</a>')
        print("  + %-44s %6.1f KB" % (rel, os.path.getsize(path) / 1024))

    if theme not in THEMES:
        theme = "t1"
    layout = LAYOUT_PORTRAIT if portrait else LAYOUT_DESKTOP
    date_s = time.strftime("%Y-%m-%d")
    subtitle = str(len(files)) + " 篇 · 单文件离线 · " + date_s

    parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN" data-theme="' + theme + '">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        FAVICON,
        '<title>' + esc(title) + '</title>',
        '<style>' + theme_css() + '\n' + BASE_CSS + '\n' + layout + '\n' + EXTRA_CSS + '</style>',
        '</head>',
        '<body>',
        '<header class="topbar">' + MENU_BTN + '<span class="tb-title">' + esc(title) + '</span></header>',
        '<aside class="side" id="side">',
        '<div class="side-head">',
        '<div class="side-title">' + esc(title) + '</div>',
        '<div class="side-sub">' + esc(subtitle) + '</div>',
        '</div>',
        '<input id="q" type="search" placeholder="过滤目录…" autocomplete="off">',
        '<nav id="toc">' + "\n".join(toc) + '</nav>',
        '<div class="side-foot">由 md2onepagehtml 本地生成<br>' + date_s + '</div>',
        '</aside>',
        '<div class="mask" id="mask"></div>',
        theme_panel_html(),
        '<main class="main">',
        "\n".join(docs),
        '<p class="doc-foot">共 ' + str(len(files)) + ' 篇，由 md2onepagehtml 生成本地单文件 HTML（'
        + date_s + '）</p>',
        '</main>',
        '<button class="totop" id="totop" aria-label="回到顶部">&#8593;</button>',
        '<script>' + JS + '</script>',
        '</body>',
        '</html>',
    ]
    html_doc = "\n".join(parts)

    # 源文件里指向不存在锚点的链接（如 llama2.c 的 [OpenMP](#OpenMP)）标灰，点了不跳
    all_ids = set(re.findall(r'id="([^"]+)"', html_doc))
    def mark_dead(m):
        return m.group(0) if m.group(2) in all_ids else (
            '<a' + m.group(1) + 'href="#' + m.group(2) + '"' + m.group(3) +
            ' class="dead" title="源文件内锚点缺失">')
    html_doc = re.sub(r'<a([^>]*?)href="#([^"]+)"([^>]*?)>', mark_dead, html_doc)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    for line in log:
        print(line)
    print("\nOK  → %s" % out_path)
    print("      %d 篇 · %.0f KB · %.1fs · 配色 %s · %s" % (
        len(files), os.path.getsize(out_path) / 1024, time.time() - t0,
        THEMES[theme]["name"], "竖屏" if portrait else "横屏"))
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="把一个目录下的多份 Markdown 合并成一个单文件 HTML",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="包含 .md 文件的目录")
    ap.add_argument("-o", "--output", default=None, help="输出 HTML 路径（默认 目录名.html，放在该目录内）")
    ap.add_argument("--title", default=None, help="页面标题（默认取目录名）")
    ap.add_argument("--theme", default="t1", help="配色 t1..t10（默认 t1）")
    ap.add_argument("--portrait", action="store_true", help="竖屏/手机优先版式")
    ap.add_argument("--recursive", action="store_true", help="递归子目录")
    ap.add_argument("--no-inline-img", action="store_true", help="图片不内联（保留原路径）")
    ap.add_argument("--fetch-remote-img", action="store_true", help="连远程图片也下载内联（较慢）")
    ap.add_argument("--base-url", default=None,
                    help="相对资源的远端前缀（默认从 git remote 推断）")
    ap.add_argument("--exclude", default="", help="排除文件名含这些关键字的 md，逗号分隔")
    a = ap.parse_args()

    root = os.path.abspath(a.dir)
    if not os.path.isdir(root):
        print("目录不存在: %s" % root)
        sys.exit(1)
    title = a.title or os.path.basename(root.rstrip("\\/")) or "合集"
    out = a.output or os.path.join(root, title + ".html")
    exclude = tuple(x.strip() for x in a.exclude.split(",") if x.strip())

    print("[md2onepagehtml] 目录: %s" % root)
    try:
        build(root, out, title, a.theme, a.portrait, a.recursive,
              not a.no_inline_img, a.fetch_remote_img, a.base_url, exclude)
    except SystemExit:
        raise
    except Exception as e:
        print("转换失败: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
