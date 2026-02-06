#!/usr/bin/env python3

"""
开发计划：
workspace/过期米老鼠/frames.md 是 通过运行py3lib/assenble.py 获得的。这个md文件内容包含文本和图片。
现在我想使用python把md转化成pdf。请你选择适当的第三方库，实现这个功能。函数传入md文件的绝对路径，自动在同级目录产生同名的pdf。
我预先咨询了其他专家，他们推荐pip install markdown weasyprint
你也可以根据你自己的判断，使用最好的方法将md转化成pdf。
"""

import os
import sys

# 避免与 py3lib/collections.py 冲突
if 'py3lib.collections' in sys.modules:
    del sys.modules['py3lib.collections']

import markdown as md_module
from weasyprint import HTML, CSS


# 获取项目字体目录的绝对路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(PROJECT_ROOT, 'fonts')

# 尝试查找本地中文字体
LOCAL_FONTS = {
    'regular': None,
    'bold': None,
}

def _find_local_fonts():
    """查找项目中的本地字体文件"""
    if os.path.exists(FONTS_DIR):
        for filename in os.listdir(FONTS_DIR):
            if filename.endswith('.otf') or filename.endswith('.ttf'):
                filepath = os.path.join(FONTS_DIR, filename)
                if 'bold' in filename.lower():
                    LOCAL_FONTS['bold'] = filepath
                else:
                    LOCAL_FONTS['regular'] = filepath

# 初始化时查找本地字体
_find_local_fonts()


def _get_font_css():
    """生成字体CSS，支持本地字体回退到系统字体"""
    css_parts = []
    
    # 优先使用本地字体
    if LOCAL_FONTS['regular']:
        css_parts.append(f"""
        @font-face {{
            font-family: 'LocalNotoSans';
            src: url('file://{LOCAL_FONTS['regular']}') format('opentype');
            font-weight: normal;
            font-style: normal;
        }}
        """)
    
    if LOCAL_FONTS['bold']:
        css_parts.append(f"""
        @font-face {{
            font-family: 'LocalNotoSans';
            src: url('file://{LOCAL_FONTS['bold']}') format('opentype');
            font-weight: bold;
            font-style: normal;
        }}
        """)
    
    # 字体栈：优先使用本地字体，然后是常见中文字体，最后是通用sans-serif
    font_family = "'LocalNotoSans', 'Noto Sans CJK SC', 'Source Han Sans CN', 'WenQuanYi Micro Hei', sans-serif"
    
    return ''.join(css_parts), font_family


def md_to_pdf(md_path: str) -> str:
    """
    将Markdown文件转换为PDF文件
    
    Args:
        md_path: Markdown文件的绝对路径
    
    Returns:
        生成的PDF文件的绝对路径
    """
    # 验证输入文件存在
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"文件不存在: {md_path}")
    
    if not md_path.endswith('.md'):
        raise ValueError(f"文件必须是 .md 格式: {md_path}")
    
    # 获取PDF输出路径（同级目录，同名文件）
    pdf_path = os.path.splitext(md_path)[0] + '.pdf'
    
    # 获取MD文件所在目录，用于解析相对图片路径
    md_dir = os.path.dirname(md_path)
    
    # 读取MD文件内容
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 将Markdown转换为HTML
    # 使用的基本扩展：表格、删除线、脚注等
    md_html = md_module.markdown(
        md_content,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
        ]
    )
    
    # 获取字体CSS和字体栈
    font_css, font_family = _get_font_css()
    
    # 构建完整HTML文档（添加样式）
    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{os.path.basename(md_path)}</title>
    <style>
        {font_css}
        body {{
            font-family: {font_family};
            font-size: 12pt;
            line-height: 1.6;
            margin: 2cm;
            color: #333;
        }}
        h1 {{
            font-size: 24pt;
            color: #1a1a1a;
            border-bottom: 2px solid #4a90d9;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            font-size: 18pt;
            color: #2c2c2c;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 15px auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }}
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ccc;
            margin: 20px 0;
        }}
        code {{
            background-color: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Consolas", "Monaco", monospace;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        blockquote {{
            border-left: 4px solid #4a90d9;
            margin: 15px 0;
            padding: 10px 20px;
            background-color: #f9f9f9;
            color: #555;
        }}
    </style>
</head>
<body>
{md_html}
</body>
</html>
"""
    
    # 使用weasyprint将HTML转换为PDF
    # base_url用于解析相对路径的图片
    html_doc = HTML(string=full_html, base_url=md_dir)
    html_doc.write_pdf(pdf_path)
    
    return pdf_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python md2pdf.py <markdown文件路径>")
        print("示例: python md2pdf.py /config/workspace/llmnote/workspace/过期米老鼠/frames.md")
        sys.exit(1)
    
    md_path = sys.argv[1]
    
    # 打印字体信息
    font_css, font_family = _get_font_css()
    if LOCAL_FONTS['regular']:
        print(f"使用本地字体: {LOCAL_FONTS['regular']}")
    else:
        print("未找到本地字体，将使用系统字体")
    
    try:
        pdf_path = md_to_pdf(md_path)
        print(f"PDF生成成功: {pdf_path}")
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
