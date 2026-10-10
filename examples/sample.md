# 示例：md2html 语法展示

> 这份文件用来演示 md2html 支持的 Markdown 语法。
> 用它跑一遍（`md2html.bat examples\sample.md`），就能看到转换效果。

## 一、行内格式

普通段落。支持 **加粗**、*斜体*、~~删除线~~，以及 `行内代码`。
链接写法：[md2html 项目](https://github.com/dingwei2028/md2html)。

## 二、列表

无序列表：

- 一级项目
- 一级项目
  - 二级项目
  - 二级项目

有序列表：

1. 第一步：准备 Markdown
2. 第二步：拖到 bat 上
3. 第三步：得到 HTML

## 三、表格

| 文件 | 作用 | 备注 |
| --- | --- | --- |
| `md2html.py` | 单文件转换引擎 | 也是 md2onepagehtml 的引擎 |
| `md2html.bat` | 桌面版入口 | 拖拽使用 |
| `md2html-竖屏.bat` | 竖屏版入口 | 手机优先 |
| `md2onepagehtml.py` | 多文件合并入口 | 一个目录合成一页 |

## 四、代码块

Python：

```python
def hello(name):
    """打招呼"""
    print(f"Hello, {name}!")
    return True
```

命令行：

```bash
python md2html.py README.md desktop --theme t3
python md2onepagehtml.py D:\docs --recursive
```

## 五、引用

> 单文件 HTML 的好处是：拷到断网的机器上照样能看，
> 因为图片已经内联进文件里了。

## 六、分隔线

---

以上是 md2html 支持的主要语法。窄屏（手机）下表格会自动转成卡片式布局。
