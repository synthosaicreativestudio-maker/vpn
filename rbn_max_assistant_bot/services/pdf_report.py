"""PDF reports for investment analysis responses."""

from __future__ import annotations

import html
import logging
import os
import re
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)


def _plain_text(text: str) -> str:
    """Convert lightweight Markdown/HTML from the LLM into readable report text."""
    text = html.unescape(text or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"```(?:\w*)\n?(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Сохраняем текст в чистом виде для построения структуры
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _find_font() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def create_investment_pdf(text: str, title: str = "Инвестиционный анализ объекта") -> str | None:
    """Create a PDF report and return its temporary file path.

    Returns None if the optional PDF dependency is not available.
    """
    text = text.replace('₽', 'руб.')
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
            KeepTogether,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except Exception:
        logger.exception("reportlab is not installed; PDF report was not created")
        return None

    font_name = "Helvetica"
    font_path = _find_font()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("RBNReportFont", font_path))
            font_name = "RBNReportFont"
        except Exception:
            logger.exception("Could not register PDF font: %s", font_path)

    fd, pdf_path = tempfile.mkstemp(prefix="rbn_invest_report_", suffix=".pdf")
    os.close(fd)

    # Инициализация стилей
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'RBNTitle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),  # Slate 900
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'RBNHeading1',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#1E293B'),  # Slate 800
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'RBNBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),  # Slate 700
        spaceAfter=4
    )
    
    list_style = ParagraphStyle(
        'RBNList',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        leftIndent=12,
        spaceAfter=3
    )
    
    alert_style = ParagraphStyle(
        'RBNAlert',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#1E293B')
    )
    
    cell_style = ParagraphStyle(
        'RBNCell',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )
    
    header_style = ParagraphStyle(
        'RBNHeaderCell',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    
    cell_bold_style = ParagraphStyle(
        'RBNCellBold',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    def make_alert_box(text_list):
        content = []
        for t in text_list:
            clean_t = t.replace('<b>', '').replace('</b>', '')
            content.append(Paragraph(clean_t, alert_style))
            content.append(Spacer(1, 3))
        if content:
            content.pop()
            
        alert_table = Table([[content]], colWidths=[515])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF3C7')),  # Amber 100
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#F59E0B')),  # Amber 500
            ('LINEBEFORE', (0, 0), (0, -1), 3.0, colors.HexColor('#EF4444')),  # Red 500
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        return alert_table

    def make_styled_table(raw_rows):
        data = []
        for r in raw_rows:
            cells = [c.strip() for c in r.split('|')]
            data.append(cells)
            
        if not data:
            return None
            
        col_count = len(data[0])
        formatted_data = []
        
        for row_idx, row in enumerate(data):
            formatted_row = []
            for col_idx, cell in enumerate(row):
                clean_cell = cell.replace('<b>', '').replace('</b>', '')
                if row_idx == 0:
                    p_style = header_style
                else:
                    is_bold = "Итого" in clean_cell or "Факт" in clean_cell or "Депозит" in clean_cell or "Ключевая ставка" in clean_cell
                    p_style = cell_bold_style if is_bold else cell_style
                formatted_row.append(Paragraph(clean_cell, p_style))
            
            while len(formatted_row) < col_count:
                formatted_row.append(Paragraph("", cell_style))
            formatted_row = formatted_row[:col_count]
            formatted_data.append(formatted_row)
            
        available_width = 515
        if col_count == 2:
            col_widths = [available_width * 0.6, available_width * 0.4]
        elif col_count == 3:
            col_widths = [available_width * 0.4, available_width * 0.3, available_width * 0.3]
        elif col_count == 4:
            col_widths = [available_width * 0.25, available_width * 0.25, available_width * 0.25, available_width * 0.25]
        elif col_count == 5:
            col_widths = [available_width * 0.2, available_width * 0.2, available_width * 0.2, available_width * 0.2, available_width * 0.2]
        elif col_count == 7:  # Сценарный анализ
            col_widths = [
                available_width * 0.22,
                available_width * 0.12,
                available_width * 0.12,
                available_width * 0.13,
                available_width * 0.11,
                available_width * 0.11,
                available_width * 0.19
            ]
        else:
            col_widths = [available_width / col_count] * col_count
            
        t = Table(formatted_data, colWidths=col_widths)
        t_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]
        
        for row_idx in range(1, len(data)):
            first_cell = data[row_idx][0].lower() if len(data[row_idx]) > 0 else ""
            if "факт" in first_cell:
                bg_color = colors.HexColor('#FEF2F2')  # Red 50
            elif "цель 9 лет" in first_cell or "рыночная" in first_cell or "цель 8 лет" in first_cell:
                bg_color = colors.HexColor('#ECFDF5')  # Emerald 50
            elif "депозит" in first_cell or "ключевая" in first_cell:
                bg_color = colors.HexColor('#EFF6FF')  # Blue 50
            elif "downside" in first_cell:
                bg_color = colors.HexColor('#FFFBEB')  # Amber 50
            elif "upside" in first_cell:
                bg_color = colors.HexColor('#F5F3FF')  # Purple 50
            elif row_idx % 2 == 0:
                bg_color = colors.HexColor('#F8F9FA')
            else:
                bg_color = colors.white
            t_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg_color))
            
        t.setStyle(TableStyle(t_styles))
        return t

    story = []
    lines = text.split('\n')
    i = 0
    n = len(lines)
    
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue
            
        # 1. Заголовок всего отчета (в самом начале)
        if i == 0 and "Инвестиционный расчет" in line:
            clean_title = line.replace('<b>', '').replace('</b>', '').upper()
            story.append(Paragraph(clean_title, title_style))
            story.append(Spacer(1, 10))
            i += 1
            continue
            
        # 2. Заголовок раздела
        h_match = re.match(r'^<b>(\d+\.\s+[^<]+)</b>', line)
        if h_match:
            section_title = h_match.group(1)
            
            # Принудительный перенос страницы перед ключевыми логическими блоками
            if len(story) > 0 and not isinstance(story[-1], PageBreak):
                if any(k in section_title for k in [
                    "3. Финансовая", 
                    "6. Сценарный", 
                    "8. Доход за 10", 
                    "11. Ступенчатая", 
                    "13. Итоговый"
                ]):
                    story.append(PageBreak())
                else:
                    story.append(Spacer(1, 8))
                    
            story.append(Paragraph(section_title, h1_style))
            story.append(Spacer(1, 4))
            
            # Если это "1. Краткий вывод", парсим его контент в Alert Box
            if "1. Краткий" in section_title:
                i += 1
                conclusion_lines = []
                while i < n and not lines[i].strip().startswith("<b>"):
                    l_text = lines[i].strip()
                    if l_text:
                        conclusion_lines.append(l_text)
                    i += 1
                alert_box = make_alert_box(conclusion_lines)
                story.append(alert_box)
                story.append(Spacer(1, 6))
                continue
                
            i += 1
            continue
            
        # 3. Таблица
        if '|' in line:
            table_lines = []
            while i < n and '|' in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            t_obj = make_styled_table(table_lines)
            if t_obj:
                story.append(t_obj)
                story.append(Spacer(1, 6))
            continue
            
        # 4. Список
        if line.startswith('- '):
            list_items = []
            while i < n and lines[i].strip().startswith('- '):
                item_text = "• " + lines[i].strip()[2:]
                list_items.append(Paragraph(item_text, list_style))
                i += 1
            story.append(KeepTogether(list_items))
            story.append(Spacer(1, 4))
            continue
            
        # 5. Обычный текст
        story.append(Paragraph(line, body_style))
        story.append(Spacer(1, 4))
        i += 1

    # Построение документа
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=45
    )

    def draw_decorations(canvas, doc):
        canvas.saveState()
        # Установка метаданных
        canvas.setTitle(title)
        canvas.setAuthor("RBN MAX Assistant Bot")
        
        # Верхняя шапка
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#475569"))  # Slate 600
        canvas.drawString(40, A4[1] - 25, "РБН ИНВЕСТИЦИИ  •  АНАЛИТИЧЕСКИЙ ОТЧЕТ ОБЪЕКТА")
        canvas.drawRightString(A4[0] - 40, A4[1] - 25, datetime.now().strftime("%d.%m.%Y %H:%M"))
        
        # Разделитель шапки
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))  # Slate 200
        canvas.setLineWidth(0.5)
        canvas.line(40, A4[1] - 30, A4[0] - 40, A4[1] - 30)
        
        # Нижний подвал
        canvas.drawString(40, 18, "Регион Бизнес Недвижимость  •  Подготовлено AI-системой MAX")
        canvas.drawRightString(A4[0] - 40, 18, f"Страница {doc.page}")
        
        # Разделитель подвала
        canvas.line(40, 25, A4[0] - 40, 25)
        canvas.restoreState()

    try:
        doc.build(story, onFirstPage=draw_decorations, onLaterPages=draw_decorations)
    except Exception as build_err:
        logger.exception("Error building PDF with SimpleDocTemplate")
        raise build_err

    return pdf_path

