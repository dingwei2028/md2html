# md2html —— 本地 Markdown 转 HTML 工具集

把 Markdown 一键转换成排版漂亮的**单文件 HTML**。纯 Python 标准库实现，
**零依赖、完全离线**，双击即可运行。

同一个目录下提供两种用法，共用一套渲染引擎：

| 用法 | 入口 | 做什么 |
| --- | --- | --- |
| 单文件 | `md2html.bat` | 一份 Markdown → 一份 HTML（横屏版 / 竖屏版） |
| 多文件 | `md2onepagehtml.bat` | 一个目录下所有 Markdown → 一份合并 HTML |

## 特性

- **零依赖**：只用 Python 标准库，不装任何第三方包，系统里有 Python 就能跑。
- **真正的单文件**：HTML 自带样式与脚本，图片默认内联成 data URI，拷到断网的机器上照样能看。
- **两种版式**：桌面宽屏（左侧目录 + 滚动高亮）／竖屏手机（吸顶导航 + 抽屉目录 + 卡片式表格）。
- **10 套配色**：右下角调色板一键换肤，选择记在本机浏览器里。
- **多文件合并**：整目录 Markdown 合成一页，两级目录 + 过滤框；图片与相对链接自动补全成远端地址。

## 快速开始

1. 确保 `python` 命令可用（Python 3.8+，安装时勾选 “Add Python to PATH”）；
2. **单文件**：把 `.md` 文件拖到 `md2html.bat` 上，回车；
3. **多文件**：把**文件夹**拖到 `md2onepagehtml.bat` 上，回车。

也可以先跑仓库自带的示例：

```bash
python md2html.py examples\sample.md desktop
python md2onepagehtml.py examples
```

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `md2html.bat` | 横屏/桌面版转换入口（拖拽或输入路径） |
| `md2html-竖屏.bat` | 竖屏友好版转换入口 |
| `md2html.py` | 核心转换引擎（不直接运行也行，命令行方式见下） |
| `md2onepagehtml.bat` | **多文件合并**入口：把一个目录下所有 md 合成一个 HTML |
| `md2onepagehtml.py` | 多文件合并工具（与 md2html.py 共用引擎，参数见下） |
| `README.md` | 本说明 |

## 使用方法（二选一）

**方式一：拖拽（最简单）**
- 打开 `md2html.bat`（或 `md2html-竖屏.bat`），把 `.md` 文件直接拖到窗口上，回车即转换；
- 可一次拖入多个文件，逐个生成。

**方式二：命令行**
```
md2html.bat D:\路径\文档.md
md2html-竖屏.bat D:\路径\文档.md
```

## 生成结果

- 横屏版：`文档.md` → `文档.html`（宽屏左侧目录 + 滚动高亮，窄屏自动变抽屉）
- 竖屏版：`文档.md` → `文档-竖屏版.html`（手机优先：吸顶导航 + 抽屉目录 + 卡片式表格 + 回到顶部）

HTML 与源文件**同目录**输出，用浏览器直接打开即可；md 中引用的相对路径图片也能正常显示（图片须与 md 同目录或保持原有相对关系）。

## 支持格式

- 标题 `#` ～ `######`（自动生成目录与锚点、滚动高亮）
- 段落、换行、分隔线 `---`
- 表格 `| 列 | 列 |`（宽屏正常表格；窄屏自动转卡片）
- 代码块 ` ```lang `（自动语言标签 + 关键字/字符串/注释/数字轻量高亮）
- 行内代码、**粗体**、*斜体*、~~删除线~~、`[链接](url)`、`![图片](url)`
- 无序/有序列表（支持一层嵌套）、引用 `>`

## 选择配色（10 套内置）

生成的 HTML 右下角有一个**调色板按钮**，点击弹出 10 套配色，点选即整页换肤：

| 编号 | 配色 | 风格 |
| --- | --- | --- |
| t1 | 翠竹绿 | 默认，纸米底 + 墨绿（当前配色） |
| t2 | 海盐蓝 | 清爽蓝调 |
| t3 | 墨黛青 | 青碧沉稳 |
| t4 | 紫罗兰 | 淡紫 + 罗兰紫 |
| t5 | 珊瑚橘 | 暖橙活力 |
| t6 | 胭脂红 | 玫红优雅 |
| t7 | 琥珀金 | 暖金复古 |
| t8 | 石墨岩 | 中性灰蓝 |
| t9 | 莓果粉 | 粉紫温柔 |
| t10 | 曜石黑 | 深色模式，亮绿点缀 |

- 选择会**立即生效并自动记忆**（刷新、下次打开仍是所选配色；仅保存在本机浏览器）。
- 命令行可指定默认配色：`python md2html.py <xxx.md> portrait --theme t10`（横屏/竖屏均支持）。

## 命令行进阶（可选）

引擎也支持直接调用，方便集成到自己的工作流：
```
python md2html.py <xxx.md> [desktop|portrait] [--theme t1..t10]
```

## 多文件合并：一个目录 → 一个 HTML（md2onepagehtml）

`md2html` 是「一份 md → 一份 HTML」；`md2onepagehtml` 是「**一个目录下所有 md → 一份 HTML**」，
适合把整套文档 / 抓下来的一批 README 合成一个可检索的单文件页面。

**拖拽（最简单）**：

- 拖**文件夹** → 合并整个目录；
- 拖**多个 `.md` 文件** → 只合并你选中的这几篇（按拖入顺序）；
- 文件夹和文件可以混着拖。

**命令行**：
```
md2onepagehtml.bat D:\某目录
md2onepagehtml.bat D:\docs\a.md D:\docs\b.md
python md2onepagehtml.py D:\某目录 -o D:\输出.html --theme t10 --portrait
python md2onepagehtml.py D:\docs\a.md D:\docs\b.md --portrait
```

| 参数 | 作用 |
| --- | --- |
| `-o` / `--output` | 输出路径（默认 `该目录/目录名.html`） |
| `--title` | 页面标题（默认取目录名） |
| `--theme t1..t10` | 配色，与 md2html 同一套 10 色 |
| `--portrait` | 竖屏 / 手机优先版式 |
| `--recursive` | 连子目录里的 md 一起收 |
| `--no-inline-img` | 图片不内联（保留原路径，文件更小但拷走会失效） |
| `--fetch-remote-img` | 连远程图片也下载内联（较慢） |
| `--base-url` | 相对资源的远端前缀（默认从 git remote 自动推断） |
| `--exclude` | 排除文件名含指定关键字的 md，逗号分隔 |

产物特点：
- 输入是**目录**时输出 `该目录\目录名.html`；输入是**文件**时输出与首个 md 同名同位置的 `.html`；
- 每篇一个卡片，**首个 `#` 标题**自动提成篇名；侧栏是「篇 + 小节」两级目录，配**过滤框**、滚动高亮；
- 图片默认内联成 data URI，HTML **拷到任何机器都能看**；
- README 里的相对链接会自动改写成该仓库的 GitHub 地址（从 git remote 推断，
  若目录里有 `_index.md` 索引表则按篇精确对应仓库）；
- 多篇之间的锚点加了篇前缀，不会互相撞车。

## 环境要求

- Windows 10/11
- 已安装 Python 3.8+（在 PATH 中，`python` 命令可用）
- 无任何第三方依赖

## 常见问题

- **提示“python 不是内部或外部命令”**：安装 Python 时勾选 “Add Python to PATH”，或在 Windows 商店安装 Python。
- **生成的 HTML 打不开/样式错乱**：用 Chrome / Edge 打开，不要用记事本查看。
- **想加/改配色**：编辑 `md2html.py` 中 `THEMES` 字典（每套配色是一组 CSS 变量，变量名见 `VAR_ORDER`），改完重新转换即可。
- **想改字体/排版细节**：编辑 `md2html.py` 顶部的 `BASE_CSS`、`LAYOUT_DESKTOP`、`LAYOUT_PORTRAIT` 变量。
- **选好的配色“丢了”**：配色记忆保存在浏览器本地（localStorage）。换浏览器、清缓存或换电脑后需重新选一次；也可用命令行 `--theme` 固定默认配色。

## 示例

`examples/sample.md` 是一份语法展示样例，覆盖了标题、列表、表格、代码块、引用、分隔线等，
用它跑一遍就能看到转换效果：

```bash
python md2html.py examples\sample.md desktop      # 单文件
python md2onepagehtml.py examples                 # 整目录合并
```

## 二次开发

- 改配色：编辑 `md2html.py` 里的 `THEMES` 字典（每套配色是一组 CSS 变量，变量名见 `VAR_ORDER`）。
- 改排版：编辑 `md2html.py` 的 `BASE_CSS` / `LAYOUT_DESKTOP` / `LAYOUT_PORTRAIT`。
- 改 bat：`_make_bats.py` 会以 GBK(ANSI) 编码重新生成三个 `.bat`（中文 Windows 下才不乱码），生成在本脚本所在目录。
- `md2onepagehtml.py` 通过 `from md2html import ...` 复用引擎，改动引擎会同时影响两个入口。

## 许可证

[MIT](LICENSE) © 2026 dingwei2028

欢迎 Issue 与 PR。
