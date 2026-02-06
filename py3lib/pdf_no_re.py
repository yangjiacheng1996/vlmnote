#!/usr/bin/env python3

"""
开发计划：
1. 使用evp命令解析视频，提取关键帧到pdf中。本项目中已经存在一个pdf，相对路径是workspace/过期米老鼠/过期米老鼠.pdf
2. 关键帧pdf中，每个关键帧左上角是这个图片的文件名，文件名格式是frame00.00.46-0.51.jpg，即hh.mm.ss-n.nn.jpg，其中hh.mm.ss是视频的时刻，n.nn是视频的帧数。
3. 编写一个函数，函数名save_frame_to_dir，两个参数，pdfpath和output_dir.使用pdfplumber提取所有每张关键帧图片到output目录中，文件名以各自图片左上角文件名来命名。
4. 测试：pdfpath是/config/workspace/llmnote/workspace/过期米老鼠/过期米老鼠.pdf ，输出目录是/config/workspace/llmnote/workspace/过期米老鼠/frames/，如果没有frames函数自动创建。
"""

import os
import pdfplumber
from PIL import Image
import io


def save_frame_to_dir(pdfpath: str, output_dir: str) -> None:
    """
    从PDF中提取所有关键帧图片并保存到指定目录。
    
    Args:
        pdfpath: PDF文件的路径
        output_dir: 输出目录路径
    """
    os.makedirs(output_dir, exist_ok=True)
    
    with pdfplumber.open(pdfpath) as pdf:
        print(f"PDF共有 {len(pdf.pages)} 页")
        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"处理第 {page_num} 页...")
            
            # 获取页面尺寸
            page_width = page.width
            page_height = page.height
            
            # 尝试提取表格
            tables = page.extract_tables()
            print(f"  检测到 {len(tables)} 个表格")
            
            # 创建图片到文件名的映射
            img_to_filename = {}
            
            if tables:
                for table_idx, table in enumerate(tables):
                    print(f"  表格 {table_idx}: {len(table)} 行")
                    for row_idx, row in enumerate(table):
                        if row and len(row) >= 1:
                            # 第一列就是文件名，直接使用
                            filename = row[0]
                            if filename and isinstance(filename, str):
                                print(f"    行 {row_idx}: 找到文件名 {filename}")
                                img_to_filename[(table_idx, row_idx)] = filename
            
            # 如果表格方式没找到，尝试直接提取页面文本
            if not img_to_filename:
                text = page.extract_text()
                if text:
                    print(f"  页面文本长度: {len(text)} 字符")
                    # 表格中只有文件名，直接按行分割
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    if lines:
                        print(f"  从页面文本中找到 {len(lines)} 行文本")
                        for i, line in enumerate(lines):
                            img_to_filename[(0, i)] = line
            
            images = page.images
            print(f"  检测到 {len(images)} 张图片")
            
            for img_idx, img_info in enumerate(images):
                # 获取图片位置信息
                x0 = img_info['x0']
                top = img_info['top']
                width = img_info['width']
                height = img_info['height']
                
                # 修正边界，确保裁剪区域在页面内
                crop_x0 = max(0, x0)
                crop_top = max(0, top)
                crop_x1 = min(page_width, x0 + width)
                crop_y1 = min(page_height, top + height)
                
                # 确保有有效的裁剪区域
                if crop_x1 > crop_x0 and crop_y1 > crop_top:
                    # 从页面裁剪图片区域
                    img = page.crop((crop_x0, crop_top, crop_x1, crop_y1))
                    
                    if img:
                        # 尝试获取文件名
                        filename = img_to_filename.get((0, img_idx))
                        
                        # 如果没找到，使用基于位置的映射（按top坐标排序）
                        if not filename:
                            # 获取所有文件名，按top位置排序
                            sorted_files = sorted(img_to_filename.items(), 
                                                 key=lambda x: page.images[x[0][1]]['top'] if x[0][1] < len(page.images) else 0)
                            if img_idx < len(sorted_files):
                                filename = sorted_files[img_idx][1]
                        
                        # 如果还没找到，使用默认命名
                        if not filename:
                            filename = f"frame_page{page_num:03d}_img{img_idx:03d}.jpg"
                        
                        # 保存图片
                        img_path = os.path.join(output_dir, filename)
                        pil_img = img.to_image()
                        pil_img.save(img_path)
                        print(f"    已保存: {img_path}")


if __name__ == "__main__":
    # 测试代码
    pdfpath = "/config/workspace/llmnote/workspace/过期米老鼠/过期米老鼠.pdf"
    output_dir = "/config/workspace/llmnote/workspace/过期米老鼠/frames/"
    os.makedirs(output_dir, exist_ok=True)
    save_frame_to_dir(pdfpath, output_dir)
