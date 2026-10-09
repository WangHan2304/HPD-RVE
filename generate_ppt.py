# -*- coding: utf-8 -*-
"""
将论文中的所有图片生成可编辑的 PPT 格式。
按论文章节分组，每页1-4张图，配有标题和简要说明。
"""

import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

# ============================================================
# 配色方案（深蓝色调，专业学术风格）
# ============================================================
COLORS = {
    'bg_dark': RGBColor(0x1A, 0x27, 0x3E),       # 深蓝背景（标题页）
    'bg_light': RGBColor(0xF0, 0xF4, 0xF8),       # 浅灰蓝背景（内容页）
    'bg_white': RGBColor(0xFF, 0xFF, 0xFF),
    'primary': RGBColor(0x1A, 0x52, 0x76),         # 深蓝主色
    'accent': RGBColor(0xE7, 0x4C, 0x3C),           # 红色强调
    'accent2': RGBColor(0x27, 0xAE, 0x60),          # 绿色
    'accent3': RGBColor(0xF3, 0x9C, 0x12),          # 金色
    'text_dark': RGBColor(0x2C, 0x3E, 0x50),
    'text_light': RGBColor(0xFF, 0xFF, 0xFF),
    'text_muted': RGBColor(0x7F, 0x8C, 0x8D),
    'line': RGBColor(0xBD, 0xC3, 0xC7),
    'card': RGBColor(0xFF, 0xFF, 0xFF),
    'section_bg': RGBColor(0x1A, 0x52, 0x76),
    'subtitle': RGBColor(0x29, 0x80, 0xB9),
}

# ============================================================
# 图片配置：按章节分组
# ============================================================
FIGURES_DIR = 'figures_paper'

SLIDES_CONFIG = [
    # ==================== 标题页 ====================
    {
        'type': 'title',
        'title': 'HPD-RVE: A Hierarchical Parameter-Driven\nMethodology for Automated RVE Generation',
        'subtitle': 'Computational Benchmarking, Experimental Validation,\nand Microstructure-Property Quantitative Mapping',
        'info': 'Figure Collection • 29 Figures • June 2026'
    },

    # ==================== 目录页 ====================
    {
        'type': 'toc',
        'title': 'Figure Index',
        'sections': [
            'Section 3: Methodology (Figures 1-4)',
            'Section 4: Benchmarking Results (Figures 5-17)',
            'Section 5: Microstructure-Property Mapping (Figures 18-20)',
            'Section 6: Parametric Scanning & Surrogate (Figures 21-27)',
            'Section 7: Validation & UQ (Figures 28-29)',
        ]
    },

    # ==================== Section 3: Methodology ====================
    {
        'type': 'section',
        'number': '3',
        'title': 'Methodology: Core Framework',
        'figures': [
            {
                'file': 'Figure1_Pipeline_Architecture.png',
                'caption': 'Figure 1: HPD-RVE Pipeline Architecture — End-to-end workflow from hierarchical parameters to CPFEM/DAMASK-ready RVE models, with four key innovations integrated into each stage.'
            },
            {
                'file': 'Figure2_Hierarchical_Framework.png',
                'caption': 'Figure 2: Hierarchical Material Parameter Description Framework — Three-level parameter hierarchy (Material → Phase → Grain) with crystallographic orientation visualization.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '3',
        'title': 'Methodology: Data Fusion & Adaptive Models',
        'figures': [
            {
                'file': 'Figure3_Data_Fusion.png',
                'caption': 'Figure 3: Multi-Source Data Fusion Strategy — Priority-weighted fusion engine combining experimental data with prior knowledge.'
            },
            {
                'file': 'Figure4_Adaptive_Models.png',
                'caption': 'Figure 4: Adaptive Model Quantity — Phase-dependent RVE count determination and model complexity mapping.'
            },
        ]
    },

    # ==================== Section 4: Benchmarking Results ====================
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Efficiency & Quality',
        'figures': [
            {
                'file': 'Figure5_Efficiency_Comparison.png',
                'caption': 'Figure 5: Modeling Time Comparison — HPD-RVE vs. Voronoi tessellation and manual modeling across five material groups.'
            },
            {
                'file': 'Figure6_Mesh_Quality.png',
                'caption': 'Figure 6: Mesh Quality Comparison — Element quality metrics with percent improvement annotations. HPD-RVE shows zero variance due to deterministic algorithm.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Phase Accuracy & Consistency',
        'figures': [
            {
                'file': 'Figure7_Phase_Accuracy.png',
                'caption': 'Figure 7: Phase Volume Fraction Accuracy — Error comparison with statistical significance markers (*** p<0.001).'
            },
            {
                'file': 'Figure8_Consistency.png',
                'caption': 'Figure 8: Generation Consistency — Deterministic repeatability across five material groups with perfect consistency benchmark line.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Speedup Analysis',
        'figures': [
            {
                'file': 'Figure9_Speedup_Analysis.png',
                'caption': 'Figure 9: Speedup Analysis — Bubble chart (size ∝ generation time) and log-scale speedup over Voronoi baseline.'
            },
            {
                'file': 'Figure10_Radar_Chart.png',
                'caption': 'Figure 10: Multi-Dimensional Performance Comparison — Radar chart across five evaluation dimensions for all material groups.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Stage Breakdown & Generalization',
        'figures': [
            {
                'file': 'Figure11_Stage_Breakdown.png',
                'caption': 'Figure 11: Stage-Level Timing Breakdown — Per-stage time distribution across the HPD-RVE pipeline.'
            },
            {
                'file': 'Figure12_Generalization_Matrix.png',
                'caption': 'Figure 12: Generalization Performance Matrix — Cross-material validation of the hierarchical parameter-driven approach.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Ablation & Sensitivity',
        'figures': [
            {
                'file': 'Figure13_Ablation_Study.png',
                'caption': 'Figure 13: Ablation Study — Pipeline time and model quality under component removal across five material groups.'
            },
            {
                'file': 'Figure14_Sensitivity_Analysis.png',
                'caption': 'Figure 14: Sensitivity Analysis — Parameter sensitivity of key performance metrics to input variations.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Statistical Validation',
        'figures': [
            {
                'file': 'Figure15_Statistical_Analysis.png',
                'caption': 'Figure 15: Statistical Analysis — Grain size distribution validation against target specifications.'
            },
            {
                'file': 'Figure16_Ablation_Radar.png',
                'caption': 'Figure 16: Ablation Radar Chart — Multi-dimensional impact assessment of component removal.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '4',
        'title': 'Benchmarking: Reproducibility & Experimental Validation',
        'figures': [
            {
                'file': 'Figure17_Reproducibility.png',
                'caption': 'Figure 17: Reproducibility Analysis — Cross-run consistency verification across all material groups.'
            },
            {
                'file': 'Figure18_Experimental_Benchmark.png',
                'caption': 'Figure 18: Experimental Benchmark — Comparison of HPD-RVE generated microstructures with experimental data.'
            },
        ]
    },

    # ==================== Section 5: CPFEM Case Studies ====================
    {
        'type': 'section',
        'number': '5',
        'title': 'Microstructure-Property Mapping: CPFEM Case Studies',
        'figures': [
            {
                'file': 'Figure19_CPFEM_Case_Study.png',
                'caption': 'Figure 19: CPFEM Case Study — Crystal plasticity finite element simulation results on HPD-RVE generated models.'
            },
            {
                'file': 'Figure20_FullField_CPFEM.png',
                'caption': 'Figure 20: Full-Field CPFEM Results — Intra-RVE stress/strain distributions and texture evolution.'
            },
        ]
    },

    # ==================== Section 6: Parametric Scanning ====================
    {
        'type': 'section',
        'number': '6',
        'title': 'Parametric Scanning: DAMASK Comparison',
        'figures': [
            {
                'file': 'Figure21_DAMASK_Comparison.png',
                'caption': 'Figure 21: DAMASK Full-Field Comparison — HPD-RVE models validated against DAMASK spectral method simulations.'
            },
            {
                'file': 'Figure22_ParametricScan_Core.png',
                'caption': 'Figure 22: Parametric Scan Core Results — Systematic variation of microstructural parameters and property responses.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '6',
        'title': 'Parametric Scanning: Sensitivity & Stress-Strain',
        'figures': [
            {
                'file': 'Figure23_SensitivityValidation.png',
                'caption': 'Figure 23: Parametric Scan Sensitivity — Parameter-to-property sensitivity mapping across the design space.'
            },
            {
                'file': 'Figure24_StressStrainAtlas.png',
                'caption': 'Figure 24: Stress-Strain Response Grid — Systematic stress-strain curves across parametric variations.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '6',
        'title': 'Surrogate Modeling & Predictions',
        'figures': [
            {
                'file': 'Figure25_ExpBenchmark.png',
                'caption': 'Figure 25: Extended Experimental Benchmark — Additional validation against diverse experimental datasets.'
            },
            {
                'file': 'Figure26_Predictions.png',
                'caption': 'Figure 26: Surrogate Model Predictions — Predicted vs. actual mechanical properties across the parametric space.'
            },
        ]
    },
    {
        'type': 'section',
        'number': '6',
        'title': 'Surrogate Model Performance',
        'figures': [
            {
                'file': 'Figure27_SurrogateModel.png',
                'caption': 'Figure 27: Surrogate Model Architecture & Performance — Training convergence, validation metrics, and prediction accuracy.'
            },
        ]
    },

    # ==================== Section 7: Validation & UQ ====================
    {
        'type': 'section',
        'number': '7',
        'title': 'Validation & Uncertainty Quantification',
        'figures': [
            {
                'file': 'Figure28_G3_Validation.png',
                'caption': 'Figure 28: G3 Validation Results — Independent validation on Group 3 material system with comprehensive metrics.'
            },
            {
                'file': 'Figure29_UQ_Analysis.png',
                'caption': 'Figure 29: Uncertainty Quantification — Propagation of input parameter uncertainties to RVE property predictions.'
            },
        ]
    },

    # ==================== 结束页 ====================
    {
        'type': 'end',
        'title': 'Thank You',
        'subtitle': 'HPD-RVE: Automated RVE Generation for\nCrystal Plasticity Finite Element Modeling',
        'info': '29 Figures • Comprehensive Benchmarking • Production-Ready Framework'
    },
]


def get_image_size(img_path):
    """获取图片原始尺寸"""
    with Image.open(img_path) as img:
        return img.size  # (width, height) in pixels


def add_slide_number(slide, num, total):
    """在幻灯片右下角添加页码"""
    txBox = slide.shapes.add_textbox(
        Inches(8.8), Inches(5.1), Inches(1.0), Inches(0.4),
    )
    run = txBox.text_frame.paragraphs[0].add_run()
    run.text = f'{num}/{total}'
    run.font.size = Pt(8)
    run.font.color.rgb = COLORS['text_muted']


def add_top_bar(slide):
    """在内容页顶部添加装饰条"""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0), Inches(0), Inches(10), Inches(0.06)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['primary']
    shape.line.fill.background()


def add_section_header(slide, section_num, title):
    """添加节标题"""
    # 章节号圆圈
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(0.4), Inches(0.2), Inches(0.45), Inches(0.45)
    )
    circle.fill.solid()
    circle.fill.fore_color.rgb = COLORS['primary']
    circle.line.fill.background()
    tf = circle.text_frame
    tf.word_wrap = False
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = section_num
    run.font.size = Pt(18)
    run.font.bold = True
    run.font.color.rgb = COLORS['text_light']

    # 标题
    txBox = slide.shapes.add_textbox(
        Inches(1.0), Inches(0.15), Inches(8.5), Inches(0.55)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = f'Section {section_num}: {title}'
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = COLORS['primary']


def create_title_slide(prs, config, slide_num, total):
    """创建标题页"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout

    # 深蓝背景
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLORS['bg_dark']

    # 装饰性左侧竖条
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(1.0), Inches(0.08), Inches(3.5)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['accent3']
    shape.line.fill.background()

    # 主标题
    txBox = slide.shapes.add_textbox(
        Inches(1.2), Inches(1.0), Inches(8.0), Inches(2.0)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = config['title']
    run.font.size = Pt(32)
    run.font.bold = True
    run.font.color.rgb = COLORS['text_light']

    # 副标题
    txBox2 = slide.shapes.add_textbox(
        Inches(1.2), Inches(3.0), Inches(8.0), Inches(1.2)
    )
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.LEFT
    run2 = p2.add_run()
    run2.text = config['subtitle']
    run2.font.size = Pt(16)
    run2.font.color.rgb = RGBColor(0xAE, 0xC6, 0xE0)

    # 底部信息
    txBox3 = slide.shapes.add_textbox(
        Inches(1.2), Inches(4.5), Inches(8.0), Inches(0.5)
    )
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    run3 = p3.add_run()
    run3.text = config['info']
    run3.font.size = Pt(12)
    run3.font.color.rgb = COLORS['text_muted']

    # 页码
    add_slide_number(slide, slide_num, total)


def create_toc_slide(prs, config, slide_num, total):
    """创建目录页"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 背景
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLORS['bg_white']

    add_top_bar(slide)

    # 标题
    txBox = slide.shapes.add_textbox(
        Inches(0.5), Inches(0.3), Inches(9.0), Inches(0.6)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = config['title']
    run.font.size = Pt(28)
    run.font.bold = True
    run.font.color.rgb = COLORS['primary']

    # 分割线
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.5), Inches(1.0), Inches(9.0), Inches(0.02)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = COLORS['line']
    line.line.fill.background()

    # 目录条目
    y = 1.3
    for i, section in enumerate(config['sections']):
        # 编号圆圈
        circle = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(0.6), Inches(y), Inches(0.35), Inches(0.35)
        )
        circle.fill.solid()
        circle.fill.fore_color.rgb = COLORS['primary']
        circle.line.fill.background()
        ctf = circle.text_frame
        cp = ctf.paragraphs[0]
        cp.alignment = PP_ALIGN.CENTER
        cr = cp.add_run()
        cr.text = str(i + 1)
        cr.font.size = Pt(14)
        cr.font.bold = True
        cr.font.color.rgb = COLORS['text_light']

        # 文本
        txBox = slide.shapes.add_textbox(
            Inches(1.2), Inches(y - 0.02), Inches(8.0), Inches(0.35)
        )
        tf2 = txBox.text_frame
        p2 = tf2.paragraphs[0]
        run2 = p2.add_run()
        run2.text = section
        run2.font.size = Pt(16)
        run2.font.color.rgb = COLORS['text_dark']

        y += 0.55

    add_slide_number(slide, slide_num, total)


def create_figure_slide(prs, config, slide_num, total):
    """创建带图片的内容页"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 背景
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLORS['bg_light']

    add_top_bar(slide)
    add_section_header(slide, config['number'], config['title'])

    figures = config['figures']
    n_figs = len(figures)

    if n_figs == 1:
        # 单图布局：大图居中
        fig = figures[0]
        img_path = os.path.join(FIGURES_DIR, fig['file'])
        if not os.path.exists(img_path):
            print(f'  [WARN] 图片不存在: {img_path}')
            return

        w_px, h_px = get_image_size(img_path)
        aspect = w_px / h_px

        # 图片区域：宽 8.5"，高按比例，最大 3.8"
        img_w = Inches(8.5)
        img_h = Inches(min(8.5 / aspect, 3.8))
        if img_h < Inches(2.5):
            img_h = Inches(2.5)
            img_w = Inches(2.5 * aspect)

        x = (Inches(10) - img_w) / 2
        y = Inches(0.85)

        slide.shapes.add_picture(img_path, x, y, img_w, img_h)

        # 图注
        caption_y = y + img_h + Inches(0.15)
        txBox = slide.shapes.add_textbox(
            Inches(0.75), caption_y, Inches(8.5), Inches(0.8)
        )
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = fig['caption']
        run.font.size = Pt(10)
        run.font.italic = True
        run.font.color.rgb = COLORS['text_muted']

    elif n_figs == 2:
        # 双图布局：左右并排
        for i, fig in enumerate(figures):
            img_path = os.path.join(FIGURES_DIR, fig['file'])
            if not os.path.exists(img_path):
                print(f'  [WARN] 图片不存在: {img_path}')
                continue

            w_px, h_px = get_image_size(img_path)
            aspect = w_px / h_px

            # 每张图宽 4.2"，高 2.5" 以内
            col_w = Inches(4.2)
            col_h = Inches(min(4.2 / aspect, 2.5))

            x = Inches(0.55) + i * Inches(4.8)
            y = Inches(0.85)

            # 白色卡片背景
            card = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                x - Inches(0.05), y - Inches(0.05),
                col_w + Inches(0.1), col_h + Inches(0.1)
            )
            card.fill.solid()
            card.fill.fore_color.rgb = COLORS['card']
            card.line.color.rgb = COLORS['line']
            card.line.width = Pt(0.5)

            slide.shapes.add_picture(img_path, x, y, col_w, col_h)

            # 图注
            cap_y = y + col_h + Inches(0.1)
            txBox = slide.shapes.add_textbox(
                x - Inches(0.05), cap_y, col_w + Inches(0.1), Inches(0.8)
            )
            tf = txBox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = fig['caption']
            run.font.size = Pt(9)
            run.font.italic = True
            run.font.color.rgb = COLORS['text_muted']

    elif n_figs == 4:
        # 四图布局：2x2 网格
        positions = [
            (Inches(0.4), Inches(0.85)),
            (Inches(5.2), Inches(0.85)),
            (Inches(0.4), Inches(3.1)),
            (Inches(5.2), Inches(3.1)),
        ]

        for i, fig in enumerate(figures):
            img_path = os.path.join(FIGURES_DIR, fig['file'])
            if not os.path.exists(img_path):
                print(f'  [WARN] 图片不存在: {img_path}')
                continue

            w_px, h_px = get_image_size(img_path)
            aspect = w_px / h_px

            cell_w = Inches(4.3)
            cell_h = Inches(min(4.3 / aspect, 1.9))

            x, y = positions[i]

            # 白色卡片
            card = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                x - Inches(0.04), y - Inches(0.04),
                cell_w + Inches(0.08), cell_h + Inches(0.08)
            )
            card.fill.solid()
            card.fill.fore_color.rgb = COLORS['card']
            card.line.color.rgb = COLORS['line']
            card.line.width = Pt(0.5)

            slide.shapes.add_picture(img_path, x, y, cell_w, cell_h)

            # 图注
            cap_y = y + cell_h + Inches(0.05)
            txBox = slide.shapes.add_textbox(
                x - Inches(0.04), cap_y, cell_w + Inches(0.08), Inches(0.55)
            )
            tf = txBox.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = fig['caption']
            run.font.size = Pt(7.5)
            run.font.italic = True
            run.font.color.rgb = COLORS['text_muted']

    add_slide_number(slide, slide_num, total)


def create_end_slide(prs, config, slide_num, total):
    """创建结束页"""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = COLORS['bg_dark']

    # 装饰线
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(3.5), Inches(2.0), Inches(3.0), Inches(0.06)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = COLORS['accent3']
    shape.line.fill.background()

    # 标题
    txBox = slide.shapes.add_textbox(
        Inches(1.0), Inches(2.3), Inches(8.0), Inches(1.0)
    )
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = config['title']
    run.font.size = Pt(44)
    run.font.bold = True
    run.font.color.rgb = COLORS['text_light']

    # 副标题
    txBox2 = slide.shapes.add_textbox(
        Inches(1.0), Inches(3.3), Inches(8.0), Inches(1.2)
    )
    tf2 = txBox2.text_frame
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = config['subtitle']
    run2.font.size = Pt(18)
    run2.font.color.rgb = RGBColor(0xAE, 0xC6, 0xE0)

    # 底部信息
    txBox3 = slide.shapes.add_textbox(
        Inches(1.0), Inches(4.8), Inches(8.0), Inches(0.5)
    )
    tf3 = txBox3.text_frame
    p3 = tf3.paragraphs[0]
    p3.alignment = PP_ALIGN.CENTER
    run3 = p3.add_run()
    run3.text = config['info']
    run3.font.size = Pt(12)
    run3.font.color.rgb = COLORS['text_muted']


def main():
    print('=' * 60)
    print('Generating HPD-RVE Figure Collection PPT')
    print('=' * 60)

    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)

    total_slides = len(SLIDES_CONFIG)
    slide_num = 0

    for config in SLIDES_CONFIG:
        slide_num += 1
        slide_type = config['type']

        if slide_type == 'title':
            print(f'  [{slide_num}/{total_slides}] Title Slide')
            create_title_slide(prs, config, slide_num, total_slides)

        elif slide_type == 'toc':
            print(f'  [{slide_num}/{total_slides}] Table of Contents')
            create_toc_slide(prs, config, slide_num, total_slides)

        elif slide_type == 'section':
            print(f'  [{slide_num}/{total_slides}] Section {config["number"]}: {config["title"]}')
            create_figure_slide(prs, config, slide_num, total_slides)

        elif slide_type == 'end':
            print(f'  [{slide_num}/{total_slides}] End Slide')
            create_end_slide(prs, config, slide_num, total_slides)

    # 保存
    output_path = 'HPD-RVE_Figure_Collection.pptx'
    prs.save(output_path)
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f'\n{"=" * 60}')
    print(f'PPT saved: {output_path}')
    print(f'File size: {file_size_mb:.1f} MB')
    print(f'Total slides: {total_slides}')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
