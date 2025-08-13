#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转图片工具
将PDF文件的每一页转换为单独的图片文件
"""

import fitz  # PyMuPDF
from PIL import Image
import os
import io
import glob
from pathlib import Path


def pdf_to_images(pdf_path, output_dir="comic_pages", dpi=300):
    """
    将PDF文件的每一页转换为图片

    Args:
        pdf_path (str): PDF文件路径
        output_dir (str): 输出目录
        dpi (int): 图片分辨率，默认300DPI

    Returns:
        list: 生成的图片文件路径列表
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 打开PDF文件
    pdf_document = fitz.open(pdf_path)
    image_paths = []

    print(f"开始处理PDF文件: {pdf_path}")
    print(f"总页数: {len(pdf_document)}")

    for page_num in range(len(pdf_document)):
        # 获取页面
        page = pdf_document.load_page(page_num)

        # 设置缩放矩阵 (dpi/72 是缩放因子)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # 渲染页面为图片
        pix = page.get_pixmap(matrix=mat)

        # 转换为PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # 保存图片
        filename = f"page_{page_num + 1:03d}.png"
        filepath = os.path.join(output_dir, filename)
        img.save(filepath, "PNG", quality=95)

        image_paths.append(filepath)
        print(f"✓ 已处理第 {page_num + 1} 页: {filename}")

    pdf_document.close()
    print(f"\n处理完成！共生成 {len(image_paths)} 张图片")
    return image_paths


def batch_process_pdfs(pdf_directory, base_output_dir="processed_comics"):
    """
    批量处理目录中的所有PDF文件

    Args:
        pdf_directory (str): 包含PDF文件的目录
        base_output_dir (str): 基础输出目录
    """
    pdf_files = glob.glob(os.path.join(pdf_directory, "*.pdf"))

    if not pdf_files:
        print("未找到PDF文件")
        return

    print(f"找到 {len(pdf_files)} 个PDF文件")

    for pdf_file in pdf_files:
        # 为每个PDF创建单独的输出目录
        pdf_name = os.path.splitext(os.path.basename(pdf_file))[0]
        output_dir = os.path.join(base_output_dir, pdf_name)

        print(f"\n处理文件: {pdf_name}")
        try:
            images = pdf_to_images(pdf_file, output_dir)
            print(f"✓ {pdf_name} 处理完成")
        except Exception as e:
            print(f"✗ {pdf_name} 处理失败: {str(e)}")


def optimize_comic_images(image_dir, target_width=1920):
    """
    优化漫画图片，统一尺寸和质量

    Args:
        image_dir (str): 图片目录
        target_width (int): 目标宽度
    """
    image_files = glob.glob(os.path.join(image_dir, "*.png"))

    for img_path in image_files:
        try:
            with Image.open(img_path) as img:
                # 计算等比例缩放的高度
                ratio = target_width / img.width
                target_height = int(img.height * ratio)

                # 调整图片尺寸
                if img.width != target_width:
                    img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    img_resized.save(img_path, "PNG", optimize=True)
                    print(f"✓ 优化图片: {os.path.basename(img_path)}")

        except Exception as e:
            print(f"✗ 优化失败 {img_path}: {str(e)}")


if __name__ == "__main__":
    # 使用示例

    # 1. 单个PDF转换
    pdf_file = "001.pdf"  # 替换为实际的PDF文件路径

    if os.path.exists(pdf_file):
        try:
            images = pdf_to_images(pdf_file, output_dir="input_images", dpi=300)
            print(f"成功转换 {len(images)} 页漫画")

            # 可选：优化图片质量
            # optimize_comic_images("comic_pages", target_width=1920)

        except Exception as e:
            print(f"处理失败: {str(e)}")
    else:
        print(f"PDF文件不存在: {pdf_file}")
        print("请将PDF文件放在当前目录下，或修改pdf_file变量的路径")

    # 2. 批量处理示例（取消注释使用）
    # batch_process_pdfs("./comics", "processed_comics")