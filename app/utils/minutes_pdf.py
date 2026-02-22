"""PDF generator for Meeting Minutes using ReportLab"""
import os
import re
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable, Image, KeepTogether)
from reportlab.pdfbase.pdfmetrics import stringWidth


# ─────────────────────── colour palette ─────────────────────────────────────
NAVY   = colors.HexColor('#0c4a6e')
BLUE   = colors.HexColor('#0284c7')
LBLUE  = colors.HexColor('#e0f2fe')
LGRAY  = colors.HexColor('#f8fafc')
DGRAY  = colors.HexColor('#374151')
MGRAY  = colors.HexColor('#6b7280')
WHITE  = colors.white
GREEN  = colors.HexColor('#065f46')
LGREEN = colors.HexColor('#d1fae5')


def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base:
            base.add(ParagraphStyle(name=name, **kw))

    add('UniName',    fontSize=15, fontName='Helvetica-Bold',
        alignment=TA_CENTER, textColor=NAVY, spaceAfter=2)
    add('FacName',    fontSize=11, fontName='Helvetica',
        alignment=TA_CENTER, textColor=DGRAY, spaceAfter=2)
    add('DocTitle',   fontSize=14, fontName='Helvetica-Bold',
        alignment=TA_CENTER, textColor=WHITE, spaceAfter=0)
    add('MetaLabel',  fontSize=9,  fontName='Helvetica-Bold',
        textColor=NAVY)
    add('MetaValue',  fontSize=9,  fontName='Helvetica',
        textColor=DGRAY)
    add('H2',         fontSize=11, fontName='Helvetica-Bold',
        textColor=NAVY, spaceBefore=10, spaceAfter=4)
    add('H3',         fontSize=10, fontName='Helvetica-Bold',
        textColor=DGRAY, spaceBefore=6, spaceAfter=3)
    add('Body',       fontSize=9,  fontName='Helvetica',
        textColor=DGRAY, leading=14, alignment=TA_JUSTIFY, spaceAfter=4)
    add('BulletItem', fontSize=9,  fontName='Helvetica',
        textColor=DGRAY, leading=13, leftIndent=12, bulletIndent=0,
        spaceAfter=2)
    add('ActionHdr',  fontSize=9,  fontName='Helvetica-Bold',
        textColor=WHITE)
    add('Footer',     fontSize=7,  fontName='Helvetica',
        textColor=MGRAY, alignment=TA_CENTER)
    return base


def _get_logo():
    try:
        from flask import current_app
        logo_dir = current_app.config.get('LOGO_FOLDER', '')
        path = os.path.join(logo_dir, 'university_logo.jpg')
        if os.path.exists(path):
            return path
    except RuntimeError:
        pass
    return None


def _md_to_paragraphs(text: str, styles) -> list:
    """Very lightweight Markdown → ReportLab paragraph converter."""
    flowables = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()

        # Blank line → small spacer
        if not stripped:
            flowables.append(Spacer(1, 4))
            i += 1
            continue

        # H1 → H2 style
        if stripped.startswith('# '):
            flowables.append(Paragraph(_clean(stripped[2:]), styles['H2']))
            i += 1
            continue

        # H2 → H2 style
        if stripped.startswith('## '):
            flowables.append(Paragraph(_clean(stripped[3:]), styles['H2']))
            i += 1
            continue

        # H3 → H3 style
        if stripped.startswith('### '):
            flowables.append(Paragraph(_clean(stripped[4:]), styles['H3']))
            i += 1
            continue

        # Horizontal rule
        if stripped.startswith('---') and len(stripped.strip('-')) == 0:
            flowables.append(HRFlowable(width='100%', thickness=0.5,
                                        color=BLUE, spaceAfter=4))
            i += 1
            continue

        # Table rows – skip (handled separately via _extract_table)
        if stripped.startswith('|') and stripped.endswith('|'):
            # Collect whole table
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i].strip())
                i += 1
            tbl = _md_table_to_flowable(table_lines, styles)
            if tbl:
                flowables.append(tbl)
            continue

        # Bullet / numbered list
        bullet_match = re.match(r'^(\s*[-*•]|\s*\d+[.)]) (.+)', stripped)
        if bullet_match:
            content = _clean(bullet_match.group(2))
            flowables.append(Paragraph(f'• {content}',
                                       styles['BulletItem']))
            i += 1
            continue

        # Bold line (whole line wrapped in ** or __)
        if ((stripped.startswith('**') and stripped.endswith('**'))
                or (stripped.startswith('__') and stripped.endswith('__'))):
            inner = stripped[2:-2]
            flowables.append(Paragraph(f'<b>{_clean(inner)}</b>',
                                       styles['Body']))
            i += 1
            continue

        # Default body
        flowables.append(Paragraph(_clean(stripped), styles['Body']))
        i += 1

    return flowables


def _clean(text: str) -> str:
    """Convert Markdown inline markup to ReportLab XML tags."""
    # Bold+italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__',    r'<b>\1</b>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_',   r'<i>\1</i>', text)
    # Code
    text = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', text)
    # Escape ampersands not already escaped
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;)', '&amp;', text)
    return text


def _md_table_to_flowable(lines: list, styles) -> Table | None:
    rows = []
    is_first = True
    for line in lines:
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if not parts:
            continue
        if re.fullmatch(r'[-| :]+', line.replace(' ', '')):
            continue   # separator row
        row = [Paragraph(_clean(p),
                         styles['ActionHdr'] if is_first else styles['Body'])
               for p in parts]
        rows.append(row)
        is_first = False

    if len(rows) < 2:
        return None

    col_count = max(len(r) for r in rows)
    # Normalise column count
    for r in rows:
        while len(r) < col_count:
            r.append(Paragraph('', styles['Body']))

    page_w = A4[0] - 4 * cm
    col_w  = page_w / col_count

    tbl = Table(rows, colWidths=[col_w] * col_count, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0),  NAVY),
        ('TEXTCOLOR',   (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('BACKGROUND',  (0, 1), (-1, -1), LGRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LGRAY]),
        ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING',  (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return tbl


# ─────────────────────── main entry point ───────────────────────────────────

def generate_minutes_pdf(record, action_items: list) -> bytes:
    """Generate a professional PDF for the given MeetingMinutes record."""
    buffer = BytesIO()
    styles = _styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
        title=record.title,
        author='EDSU Result Processing System',
    )

    story = []

    # ── University header ────────────────────────────────────────────────────
    logo_path = _get_logo()
    header_data = [[]]
    if logo_path:
        try:
            logo_img = Image(logo_path, width=1.8 * cm, height=1.8 * cm)
            header_data[0].append(logo_img)
        except Exception:
            header_data[0].append('')
    else:
        header_data[0].append('')

    try:
        from flask import current_app
        uni_name  = current_app.config.get('UNIVERSITY_NAME', 'Edo State University Iyamho')
        fac_name  = current_app.config.get('FACULTY_NAME', 'Faculty of Science')
        dept_name = current_app.config.get('DEPARTMENT_NAME', 'Computer Science')
    except RuntimeError:
        uni_name  = 'Edo State University Iyamho'
        fac_name  = 'Faculty of Science'
        dept_name = 'Computer Science'

    header_text = (
        f'<b>{uni_name}</b><br/>'
        f'{fac_name}<br/>'
        f'Department of {dept_name}'
    )
    header_data[0].append(
        Paragraph(header_text,
                  ParagraphStyle('hdr', fontSize=11, fontName='Helvetica',
                                 alignment=TA_CENTER, textColor=NAVY,
                                 leading=15))
    )

    col_widths = [2.2 * cm, doc.width - 2.2 * cm]
    hdr_tbl = Table(header_data, colWidths=col_widths)
    hdr_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(hdr_tbl)
    story.append(HRFlowable(width='100%', thickness=1.5, color=BLUE,
                             spaceAfter=8, spaceBefore=6))

    # ── Title banner ─────────────────────────────────────────────────────────
    title_tbl = Table(
        [[Paragraph('MINUTES OF MEETING', styles['DocTitle'])]],
        colWidths=[doc.width]
    )
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, 0), NAVY),
        ('TOPPADDING',    (0, 0), (0, 0), 10),
        ('BOTTOMPADDING', (0, 0), (0, 0), 10),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 10))

    # ── Meeting metadata box ─────────────────────────────────────────────────
    date_str = record.meeting_date.strftime('%A, %d %B %Y') if record.meeting_date else '—'
    time_str = record.meeting_time or '—'
    meta_rows = [
        ['Meeting Title:', record.title or '—'],
        ['Date:',          date_str],
        ['Time:',          time_str],
        ['Venue:',         record.venue or '—'],
        ['Chairperson:',   record.chairperson or '—'],
        ['Attendees:',     record.attendees or '—'],
        ['Status:',        (record.status or 'draft').capitalize()],
        ['Recorded by:',   record.created_by.full_name if record.created_by else '—'],
        ['Generated on:',  datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')],
    ]
    meta_flowable_rows = [
        [Paragraph(label, styles['MetaLabel']),
         Paragraph(value, styles['MetaValue'])]
        for label, value in meta_rows
    ]
    meta_tbl = Table(meta_flowable_rows, colWidths=[3.5 * cm, doc.width - 3.5 * cm])
    meta_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), LBLUE),
        ('LINEBELOW',    (0, 0), (-1, -2), 0.3, colors.HexColor('#bae6fd')),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [LBLUE, WHITE]),
    ]))
    story.append(KeepTogether([meta_tbl]))
    story.append(Spacer(1, 14))

    # ── Agenda ───────────────────────────────────────────────────────────────
    if record.agenda:
        story.append(Paragraph('AGENDA', styles['H2']))
        story.append(HRFlowable(width='100%', thickness=0.5,
                                color=BLUE, spaceAfter=4))
        for idx, item in enumerate(record.agenda.splitlines(), 1):
            item = item.strip()
            if item:
                story.append(Paragraph(f'{idx}. {_clean(item)}',
                                       styles['BulletItem']))
        story.append(Spacer(1, 10))

    # ── AI Minutes body ───────────────────────────────────────────────────────
    if record.ai_minutes:
        story.append(Paragraph('MINUTES', styles['H2']))
        story.append(HRFlowable(width='100%', thickness=0.5,
                                color=BLUE, spaceAfter=6))
        story.extend(_md_to_paragraphs(record.ai_minutes, styles))
    else:
        # Fall back to raw transcript
        if record.raw_transcript:
            story.append(Paragraph('TRANSCRIPT', styles['H2']))
            story.append(HRFlowable(width='100%', thickness=0.5,
                                    color=BLUE, spaceAfter=6))
            story.append(Paragraph(_clean(record.raw_transcript), styles['Body']))

    story.append(Spacer(1, 14))

    # ── Action items table ────────────────────────────────────────────────────
    if action_items:
        story.append(Paragraph('ACTION ITEMS', styles['H2']))
        story.append(HRFlowable(width='100%', thickness=0.5,
                                color=BLUE, spaceAfter=6))
        ai_rows = [[
            Paragraph('#',           styles['ActionHdr']),
            Paragraph('Action',      styles['ActionHdr']),
            Paragraph('Responsible', styles['ActionHdr']),
            Paragraph('Deadline',    styles['ActionHdr']),
        ]]
        for idx, item in enumerate(action_items, 1):
            ai_rows.append([
                Paragraph(str(idx), styles['Body']),
                Paragraph(_clean(str(item.get('action', ''))), styles['Body']),
                Paragraph(_clean(str(item.get('responsible', ''))), styles['Body']),
                Paragraph(_clean(str(item.get('deadline', ''))), styles['Body']),
            ])
        ai_tbl = Table(ai_rows,
                       colWidths=[1 * cm,
                                  doc.width - 1 * cm - 4 * cm - 3 * cm,
                                  4 * cm, 3 * cm],
                       repeatRows=1)
        ai_tbl.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, LGREEN]),
            ('GRID',          (0, 0), (-1, -1), 0.4,
             colors.HexColor('#d1d5db')),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        story.append(ai_tbl)
        story.append(Spacer(1, 14))

    # ── Signature section ─────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=1, color=BLUE,
                             spaceAfter=8))
    sig_rows = [[
        Paragraph('____________________________<br/>Chairperson<br/>'
                  f'<b>{record.chairperson or ""}</b>',
                  ParagraphStyle('sig', fontSize=9, fontName='Helvetica',
                                 alignment=TA_LEFT, textColor=DGRAY, leading=14)),
        Paragraph('____________________________<br/>Secretary<br/>'
                  f'<b>{record.created_by.full_name if record.created_by else ""}</b>',
                  ParagraphStyle('sig2', fontSize=9, fontName='Helvetica',
                                 alignment=TA_RIGHT, textColor=DGRAY, leading=14)),
    ]]
    sig_tbl = Table(sig_rows, colWidths=[doc.width / 2, doc.width / 2])
    sig_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_tbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f'Generated by EDSU Result Processing System | {datetime.utcnow().strftime("%d %b %Y")}',
        styles['Footer']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
