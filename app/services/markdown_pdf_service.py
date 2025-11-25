"""Markdown 转 PDF 服务。"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# 尝试导入 Markdown 相关库
try:
    import markdown  # type: ignore

    MARKDOWN_PDF_AVAILABLE = True
except ImportError:
    MARKDOWN_PDF_AVAILABLE = False
    logger.warning("markdown 未安装，Markdown 转 PDF 功能不可用")

# 尝试导入 ReportLab 字体注册相关模块
try:
    from reportlab.pdfbase import pdfmetrics  # type: ignore
    from reportlab.pdfbase.ttfonts import TTFont  # type: ignore

    FONT_REGISTER_AVAILABLE = True
except Exception:  # pragma: no cover - 极端情况下 reportlab 不可用
    FONT_REGISTER_AVAILABLE = False
    logger.warning("ReportLab 字体注册不可用，可能导致中文无法正常显示")


class MarkdownPdfService:
    """Markdown 转 PDF 服务类."""

    def __init__(self) -> None:
        """初始化 Markdown 转 PDF 服务."""
        # 默认输出目录，可通过环境变量覆盖
        self.output_dir = Path(settings.PDF_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 字体配置
        self.font_name = settings.PDF_FONT_NAME or "SimSun"
        self.font_path: Optional[str] = settings.PDF_FONT_PATH

        self._ensure_chinese_font()

    def _ensure_chinese_font(self) -> None:
        """确保为 PDF 注册中文字体，避免中文显示为方块."""
        logger.debug("开始检查并注册中文字体, FONT_REGISTER_AVAILABLE=%s", FONT_REGISTER_AVAILABLE)

        if not FONT_REGISTER_AVAILABLE:
            logger.warning("ReportLab 字体注册不可用，可能导致 PDF 中文显示异常")
            return

        # 如果通过配置指定了字体路径，优先使用
        if self.font_path:
            path = Path(self.font_path)
            if path.is_file():
                # 如果没有显式配置字体名称，则使用文件名作为字体名称
                font_name = settings.PDF_FONT_NAME or path.stem
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(path)))
                    self.font_name = font_name
                    logger.debug("已注册自定义 PDF 字体: %s (%s)", font_name, path)
                    return
                except Exception as e:
                    logger.error("注册自定义 PDF 字体失败: %s", e)
            else:
                logger.warning("PDF_FONT_PATH 指定的字体文件不存在: %s", path)

        # 自动尝试在常见路径查找中文字体（主要针对 Windows）
        windows_font_candidates = [
            ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
            ("SimSun", r"C:\Windows\Fonts\simsun.ttf"),
            ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
            ("MicrosoftYaHei", r"C:\Windows\Fonts\msyh.ttc"),
        ]

        for name, path_str in windows_font_candidates:
            path = Path(path_str)
            if not path.is_file():
                continue
            try:
                pdfmetrics.registerFont(TTFont(name, str(path)))
                self.font_name = name
                logger.debug("已自动注册 Windows 中文字体: %s (%s)", name, path)
                return
            except Exception as e:
                logger.warning("尝试注册字体 %s 失败: %s", name, e)

        logger.warning(
            "未能成功注册中文字体，当前使用字体名称: %s，建议在 .env 中配置 PDF_FONT_PATH 指向一个支持中文的 TTF/TTC 文件",
            self.font_name,
        )

    def _render_with_reportlab(self, html: str, output_path: Path) -> None:
        """
        使用 ReportLab PLATYPUS 按 Markdown 样式渲染 PDF.

        支持：标题层级、普通段落、粗体/斜体（基于 Paragraph 内联标记）、简单表格。

        Args:
            html: Markdown 渲染后的 HTML 字符串
            output_path: 输出 PDF 文件路径
        """
        try:
            from bs4 import BeautifulSoup  # type: ignore
            from reportlab.lib import colors  # type: ignore
            from reportlab.lib.enums import TA_LEFT  # type: ignore
            from reportlab.lib.pagesizes import A4  # type: ignore
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
            from reportlab.lib.units import mm  # type: ignore
            from reportlab.platypus import (  # type: ignore
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
            )
        except Exception as exc:  # pragma: no cover - 仅在环境缺少依赖时触发
            logger.error("导入 ReportLab / BeautifulSoup 失败，无法生成 PDF: %s", exc)
            raise Exception("环境缺少 ReportLab 或 beautifulsoup4 组件，无法生成 PDF") from exc

        base_font = self.font_name or "Helvetica"

        # 文档基础配置
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        styles = getSampleStyleSheet()

        # 正文样式
        body_style = ParagraphStyle(
            name="BodyCN",
            parent=styles["BodyText"],
            fontName=base_font,
            fontSize=11,
            leading=15,
            alignment=TA_LEFT,
        )

        # 标题样式（H1-H6）
        heading_styles: dict[str, ParagraphStyle] = {}
        heading_sizes = {
            "h1": 22,
            "h2": 18,
            "h3": 16,
            "h4": 14,
            "h5": 13,
            "h6": 12,
        }
        for tag, size in heading_sizes.items():
            heading_styles[tag] = ParagraphStyle(
                name=f"{tag.upper()}CN",
                parent=styles["Heading1"],
                fontName=base_font,
                fontSize=size,
                leading=size + 2,
                spaceBefore=6,
                spaceAfter=6,
            )

        story: List[Any] = []

        # 先用 BeautifulSoup 解析 HTML，并清理 ReportLab 不支持的属性/标签
        soup = BeautifulSoup(html, "html.parser")

        # 1) 处理 <a> 链接：
        #    - 对 http/https 开头的外链，保留 href 以便生成可点击链接
        #    - 对文内锚点（如 href="#ref-1"）退化为纯文本，避免复杂的内部跳转解析
        for a in soup.find_all("a"):
            href = a.get("href")
            if href and href.startswith(("http://", "https://")):
                # 外部链接：保留，稍后只保留 href 属性
                continue
            # 其他情况（如 href="#ref-1"），仅保留可见文本
            a.replace_with(a.get_text(strip=True))

        # 2) 将 <sup> ... </sup> 转成 ReportLab 支持的 <super> 标签，去掉 id 等属性
        for sup in soup.find_all("sup"):
            super_tag = soup.new_tag("super")
            # 保留原有子节点（可能已经在上一步被处理为纯文本或外链）
            for child in list(sup.children):
                super_tag.append(child)
            sup.replace_with(super_tag)

        # 3) 清理所有标签上的多余属性，避免 paraparser 报 "invalid attribute name"
        for tag in soup.find_all(True):
            if tag.name == "a":
                # 链接标签仅保留 href 属性
                href = tag.get("href")
                tag.attrs = {}
                if href:
                    tag["href"] = href
            else:
                tag.attrs = {}

        body = soup.body or soup

        def _append_paragraph(tag, style: ParagraphStyle) -> None:
            """将 HTML 标签内容作为段落添加到文档中。"""
            inner_html = tag.decode_contents().strip()
            if not inner_html:
                return
            story.append(Paragraph(inner_html, style))
            story.append(Spacer(1, 4))

        def _append_table(table_tag: Any) -> None:
            """将 HTML 表格转换为 ReportLab 表格."""
            rows: List[List[str]] = []
            for tr in table_tag.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                row = [cell.get_text(" ", strip=True) for cell in cells]
                rows.append(row)

            if not rows:
                return

            tbl = Table(rows, hAlign="LEFT")
            tbl_style = TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), base_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
            tbl.setStyle(tbl_style)
            story.append(tbl)
            story.append(Spacer(1, 6))

        for element in body.children:
            if not getattr(element, "name", None):
                # 处理裸文本
                text = str(element).strip()
                if text:
                    story.append(Paragraph(text, body_style))
                    story.append(Spacer(1, 4))
                continue

            tag_name = element.name.lower()

            if tag_name in heading_styles:
                _append_paragraph(element, heading_styles[tag_name])
            elif tag_name == "p":
                _append_paragraph(element, body_style)
            elif tag_name in ("ul", "ol"):
                # 简单处理列表为多个段落
                for li in element.find_all("li", recursive=False):
                    text = li.decode_contents().strip()
                    if not text:
                        continue
                    bullet_html = f"• {text}"
                    story.append(Paragraph(bullet_html, body_style))
                    story.append(Spacer(1, 2))
                story.append(Spacer(1, 4))
            elif tag_name == "table":
                _append_table(element)
            elif tag_name == "hr":
                story.append(Spacer(1, 8))
            else:
                # 未特别处理的标签，退化为正文段落
                _append_paragraph(element, body_style)

        if not story:
            # 安全兜底：避免空文档
            story.append(Paragraph("（空文档）", body_style))

        logger.info("开始使用 ReportLab PLATYPUS 渲染 PDF，flowables 数量: %d", len(story))
        doc.build(story)

    async def markdown_to_pdf(
        self,
        markdown_text: str,
        filename: Optional[str] = None,
    ) -> str:
        """
        将 Markdown 文本转换为 PDF 文件并保存.

        Args:
            markdown_text: Markdown 格式的文本内容
            filename: 可选的 PDF 文件名（不包含扩展名或包含 .pdf 均可）

        Returns:
            str: 生成的 PDF 文件绝对路径

        Raises:
            ValueError: 当依赖未安装或参数无效时
            Exception: 当 PDF 生成失败时
        """
        if not MARKDOWN_PDF_AVAILABLE:
            raise ValueError("Markdown 转 PDF 依赖未安装，请安装 markdown")

        if not markdown_text or not markdown_text.strip():
            raise ValueError("Markdown 内容不能为空")

        # 规范化文件名
        if filename:
            name = filename.strip()
            if not name:
                raise ValueError("文件名不能为空")
            if not name.lower().endswith(".pdf"):
                name = f"{name}.pdf"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"markdown_report_{timestamp}.pdf"

        output_path = self.output_dir / name

        logger.info(
            "开始进行 Markdown 转 PDF, 目标文件: %s, 使用字体: %s",
            output_path,
            self.font_name,
        )

        # 先将 Markdown 转为 HTML
        html_body = markdown.markdown(
            markdown_text,
            extensions=[
                "extra",
                "toc",
                "tables",
            ],
        )

        logger.info("开始使用 ReportLab 渲染 PDF 文档，HTML 长度: %d", len(html_body))

        self._render_with_reportlab(html_body, output_path)

        logger.info("Markdown 已成功转换为 PDF: %s", output_path)
        return str(output_path.resolve())


# 创建全局服务实例
markdown_pdf_service = MarkdownPdfService()


