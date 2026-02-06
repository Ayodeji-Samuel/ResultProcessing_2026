"""PDF generation utility functions using ReportLab"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
import os
from datetime import datetime


class VerticalText(Flowable):
    """Flowable for rendering vertical text rotated 90 degrees"""
    def __init__(self, text, fontName="Helvetica-Bold", fontSize=8):
        Flowable.__init__(self)
        self.text = text
        self.fontName = fontName
        self.fontSize = fontSize

    def wrap(self, availWidth, availHeight):
        # swap width/height because text is rotated
        self.width = self.fontSize
        self.height = stringWidth(self.text, self.fontName, self.fontSize)
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.rotate(90)          # rotate like Excel
        self.canv.setFont(self.fontName, self.fontSize)
        self.canv.drawString(0, -self.fontSize, self.text)
        self.canv.restoreState()


def get_logo_path():
    """Get the university logo path"""
    from flask import current_app
    logo_dir = current_app.config.get('LOGO_FOLDER', 'app/static/logos')
    custom_logo = os.path.join(logo_dir, 'university_logo.jpg')
    default_logo = os.path.join(current_app.root_path, 'static', 'images', 'default_logo.png')
    
    if os.path.exists(custom_logo):
        return custom_logo
    elif os.path.exists(default_logo):
        return default_logo
    return None


def create_header_styles():
    """Create custom paragraph styles for headers"""
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='UniversityName',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='FacultyName',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=4,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        name='SheetTitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='InfoText',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=2,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        name='VerticalText',
        parent=styles['Normal'],
        fontSize=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    ))
    
    return styles


def generate_spreadsheet_pdf(data, config, signatories=None):
    """
    Generate the examination record spreadsheet PDF.
    
    Args:
        data: Dictionary containing:
            - students: List of student result data
            - courses: List of courses (first semester, then second if applicable)
            - level: Level (100, 200, 300, 400)
            - program: Program name
            - semester: 'first', 'second', or 'both'
            - session: Academic session
        config: System configuration
        signatories: Dictionary containing signatory names:
            - course_adviser: Name of course adviser
            - hod: Name of HOD
            - dean: Name of Dean
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    
    # Use landscape orientation for wide spreadsheets
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=0.5*cm,
        rightMargin=0.5*cm,
        topMargin=0.5*cm,
        bottomMargin=0.5*cm
    )
    
    styles = create_header_styles()
    elements = []
    
    # Header with logo
    header_data = []
    logo_path = get_logo_path()
    
    # Build header table with logo on left
    header_content = []
    
    # University info
    header_content.append(Paragraph(config.get('university_name', 'EDO STATE UNIVERSITY UZAIRUE'), styles['UniversityName']))
    header_content.append(Paragraph(f"FACULTY: {config.get('faculty_name', 'Faculty of Science')}", styles['FacultyName']))
    header_content.append(Paragraph("EXAMINATION RECORD SHEET", styles['SheetTitle']))
    header_content.append(Spacer(1, 6))
    
    # Level, Program, Department info - create styled paragraphs with bold keys
    level_para = Paragraph(f"<b>LEVEL:</b> {data['level']}", styles['InfoText'])
    program_para = Paragraph(f"<b>PROGRAMME:</b> {data['program']}", styles['InfoText'])
    department_para = Paragraph(f"<b>DEPARTMENT:</b> {config.get('department_name', 'Computer Science')}", styles['InfoText'])
    
    # Create a table for level, program, department (left, center, right)
    info_table = Table([[level_para, program_para, department_para]], colWidths=[None, None, None])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    header_content.append(info_table)
    
    # Session centered with bold key
    session_para = Paragraph(f"<b>SESSION:</b> {data['session']}", styles['InfoText'])
    session_para.alignment = TA_CENTER
    header_content.append(session_para)
    
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=1.5*cm, height=1.5*cm)
            header_table = Table([[logo, header_content]], colWidths=[2*cm, None])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ]))
            elements.append(header_table)
        except:
            for item in header_content:
                elements.append(item)
    else:
        for item in header_content:
            elements.append(item)
    
    elements.append(Spacer(1, 10))
    
    # Build the result table
    students = data['students']
    first_sem_courses = data.get('first_semester_courses', [])
    second_sem_courses = data.get('second_semester_courses', [])
    semester_type = data.get('semester')
    
    # Determine which courses to show
    if semester_type == '1':
        courses_to_show = first_sem_courses
        semester_label = 'FIRST SEMESTER'
    elif semester_type == '2':
        courses_to_show = second_sem_courses
        semester_label = 'SECOND SEMESTER'
    else:
        courses_to_show = first_sem_courses + second_sem_courses
        semester_label = 'BOTH SEMESTERS'
    
    # Calculate column counts
    base_cols = 3  # S/N, Matric, Name
    course_cols = len(courses_to_show)
    summary_cols = 4  # CUP, CUF, TCU, GPA
    total_cols = base_cols + course_cols + summary_cols + 1  # +1 for Remarks
    
    # Build table header rows (4 rows: semester label, course names, course status, credit units)
    # Row 1: Headers for fixed columns and semester label
    row1 = ['S/N', 'Matric Number', 'Student Name\n(Surname First)']  # Fixed column headers (will be spanned vertically)
    row1.append(semester_label)  # This will span all course + summary columns
    row1.append('Remarks')  # Remarks (will be spanned vertically)
    
    # Row 2: Course codes and titles (simulating vertical text with newlines)
    row2 = ['', '', '']  # S/N, Matric, Name columns
    row3 = ['', '', '']  # Course status row
    row4 = ['', '', '']  # Credit units row
    
    # Add courses to headers
    max_course_text_length = 0  # Track longest course text for header height
    for course in courses_to_show:
        # Course code and title - use VerticalText for proper rotation
        course_text = f"{course['code']}: {course['title'][:20]}"
        # Calculate length for height determination
        text_length = stringWidth(course_text, 'Helvetica-Bold', 8)
        max_course_text_length = max(max_course_text_length, text_length)
        
        row2.append(VerticalText(course_text))
        row3.append(course['status'])  # Course status (C, R, or E)
        row4.append(str(course['credit_unit']))  # Credit unit for each course
    
    # Add summary column headers - make them vertical too
    summary_labels = ['Credit Unit Passed', 'Credit Unit Failed', 'Total Credit Unit', 'GPA']
    for label in summary_labels:
        row2.append(VerticalText(label))
    row3.extend(['', '', '', ''])  # No status for summary columns
    row4.extend(['', '', '', ''])  # No credit units for summary columns
    
    # Add Remarks column - empty in rows 2, 3, 4 since row 1 has the header
    row2.append('')
    row3.append('')
    row4.append('')
    
    table_data = [row1, row2, row3, row4]
    
    # Add student data rows
    for idx, student in enumerate(students, 1):
        # Format student name with (Miss) prefix for females
        student_name = student['name']
        if student.get('gender') == 'F':
            student_name = f"(Miss) {student_name}"
        
        row = [
            str(idx),
            student['matric_number'],
            student_name
        ]
        
        # Get appropriate semester data
        if semester_type == '1':
            semester_data = student.get('first_semester', {})
            summary = student.get('first_semester_summary', {})
        elif semester_type == '2':
            semester_data = student.get('second_semester', {})
            summary = student.get('second_semester_summary', {})
        else:
            # For both semesters, combine data (this is simplified)
            semester_data = {**student.get('first_semester', {}), **student.get('second_semester', {})}
            summary = student.get('first_semester_summary', {})  # Use first semester summary for now
        
        # Course scores
        for course in courses_to_show:
            course_result = semester_data.get(course['code'], '-')
            row.append(course_result)
        
        # Summary columns
        row.append(str(summary.get('passed_units', 0)))  # CUP
        row.append(str(summary.get('failed_units', 0)))  # CUF
        row.append(str(summary.get('total_units', 0)))   # TCU
        row.append(f"{summary.get('gpa', 0.00):.2f}")    # GPA
        
        # Remarks - use carryover data if available
        remark = student.get('remark', 'Proceed')
        row.append(remark)
        
        table_data.append(row)
    
    # Calculate dynamic column widths based on content
    col_widths = []
    padding = 0.3*cm  # Extra padding for each column
    
    # Calculate width for each column
    for col_idx in range(total_cols):
        max_width = 0
        
        # Check all rows for this column
        for row_idx, row in enumerate(table_data):
            if col_idx < len(row):
                cell_content = row[col_idx]
                
                # Handle VerticalText objects
                if isinstance(cell_content, VerticalText):
                    # For vertical text, width is just the font size + padding
                    cell_width = cell_content.fontSize + padding
                else:
                    # For regular text, calculate based on string width
                    text = str(cell_content)
                    # Use appropriate font size based on row
                    if row_idx <= 3:  # Header rows
                        font_size = 8
                    else:  # Data rows
                        font_size = 9
                    
                    # Calculate width for multi-line text (take max line width)
                    lines = text.split('\n')
                    max_line_width = max([stringWidth(line, 'Helvetica-Bold' if row_idx <= 3 else 'Helvetica', font_size) for line in lines] or [0])
                    cell_width = max_line_width + padding
                
                max_width = max(max_width, cell_width)
        
        # Set minimum widths for specific columns
        if col_idx == 0:  # S/N
            max_width = max(max_width, 0.8*cm)
        elif col_idx == 1:  # Matric
            max_width = max(max_width, 2.5*cm)
        elif col_idx == 2:  # Name
            max_width = max(max_width, 4*cm)
        elif col_idx == total_cols - 1:  # Remarks
            max_width = max(max_width, 1.5*cm)
        else:  # Course and summary columns
            max_width = max(max_width, 1.2*cm)
        
        col_widths.append(max_width)
    
    # Adjust if total width exceeds page width
    available_width = page_size[0] - 1*cm
    total_width = sum(col_widths)
    if total_width > available_width:
        # Scale down proportionally
        scale_factor = available_width / total_width
        col_widths = [w * scale_factor for w in col_widths]
    
    # Create table
    table = Table(table_data, colWidths=col_widths, repeatRows=4)
    
    # Make header tall enough for vertical text based on longest course text
    # Add padding for better spacing
    header_height = max_course_text_length + 1*cm
    table._argH[1] = header_height  # row containing vertical course names
    
    # Style the table - All White Background with Black Text and Grid
    style = TableStyle([
        # All backgrounds white
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        
        # All text black
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        
        # Header rows styling
        ('FONTNAME', (0, 0), (-1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (2, 3), 8),  # Base columns
        ('FONTSIZE', (3, 0), (3, 0), 12),  # Semester label - larger
        ('FONTSIZE', (3, 1), (3, 1), 8),  # Course headers - larger for better visualization
        ('FONTSIZE', (3, 2), (-1, 3), 8),  # Status and credit units - larger
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 3), 'BOTTOM'),  # Header rows - bottom alignment
        ('VALIGN', (0, 4), (-1, -1), 'MIDDLE'),  # Data rows - middle alignment
        
        # Data rows styling
        ('FONTNAME', (0, 4), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 4), (-1, -1), 9),
        
        # Grid - Black lines
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.black),
        
        # Name column left aligned for data rows
        ('ALIGN', (2, 4), (2, -1), 'LEFT'),
        
        # Span cells for fixed columns (S/N, Matric, Name)
        ('SPAN', (0, 0), (0, 3)),  # S/N - spans all 4 header rows
        ('SPAN', (1, 0), (1, 3)),  # Matric - spans all 4 header rows
        ('SPAN', (2, 0), (2, 3)),  # Name - spans all 4 header rows
        
        # Span semester label across all course and summary columns (not including Remarks)
        ('SPAN', (3, 0), (3 + course_cols + summary_cols - 1, 0)),
        
        # Span Remarks column (last column) - spans all 4 header rows
        ('SPAN', (3 + course_cols + summary_cols, 0), (3 + course_cols + summary_cols, 3)),
        
        # Add thicker border for semester label
        ('BOX', (3, 0), (3 + course_cols + summary_cols - 1, 0), 1.5, colors.black),
    ])
    
    # Span course name headers (row 1) - each course column spans only row 1
    col_idx = 3
    for _ in courses_to_show:
        # Row 1 has course name (single row, not spanned)
        # Row 2 has course status (not spanned)
        # Row 3 has credit unit (not spanned)
        col_idx += 1
    
    # Span summary headers (rows 1, 2, 3 for CUP, CUF, TCU, GPA)
    for i in range(summary_cols):
        style.add('SPAN', (col_idx + i, 1), (col_idx + i, 3))  # Span rows 1-3 for summary columns

    
    table.setStyle(style)
    elements.append(table)
    
    # Add signature section at the bottom
    elements.append(Spacer(1, 1.5*cm))
    
    # Create signature lines
    name_style = ParagraphStyle(
        name='SignatureName',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    position_style = ParagraphStyle(
        name='SignaturePosition',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    line_style = ParagraphStyle(
        name='SignatureLine',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Get signatory names or use defaults
    if signatories is None:
        signatories = {}
    
    course_adviser_name = signatories.get('course_adviser', 'N/A')
    hod_name = signatories.get('hod', 'N/A')
    dean_name = signatories.get('dean', 'N/A')
    
    # Create three signature boxes with names before positions
    sig_line = "________________________"
    
    sig1 = [
        Paragraph(sig_line, line_style),
        Paragraph(course_adviser_name, name_style),
        Paragraph("Course Adviser", position_style)
    ]
    
    sig2 = [
        Paragraph(sig_line, line_style),
        Paragraph(hod_name, name_style),
        Paragraph("Ag. HOD Computer Science", position_style)
    ]
    
    sig3 = [
        Paragraph(sig_line, line_style),
        Paragraph(dean_name, name_style),
        Paragraph("Dean Faculty of Science", position_style)
    ]
    
    # Create table for signatures (evenly spaced)
    signature_table = Table([[sig1, sig2, sig3]], colWidths=[None, None, None])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(signature_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_student_result_pdf(student_data, results_data, config):
    """
    Generate individual student result PDF.
    
    Args:
        student_data: Student information dictionary
        results_data: Dictionary with semester results
        config: System configuration
    
    Returns:
        BytesIO: PDF file buffer
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    styles = create_header_styles()
    elements = []
    
    # Header
    logo_path = get_logo_path()
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=2*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            elements.append(logo)
        except:
            pass
    
    elements.append(Paragraph(config.get('university_name', 'EDO STATE UNIVERSITY UZAIRUE'), styles['UniversityName']))
    elements.append(Paragraph(f"FACULTY: {config.get('faculty_name', 'Faculty of Science')}", styles['FacultyName']))
    elements.append(Paragraph(f"DEPARTMENT: {config.get('department_name', 'Computer Science')}", styles['FacultyName']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("STUDENT RESULT SLIP", styles['SheetTitle']))
    elements.append(Spacer(1, 15))
    
    # Student Information
    info_style = ParagraphStyle(
        name='StudentInfo',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4
    )
    
    # Format student name with (Miss) prefix for females
    student_name = student_data['name']
    if student_data.get('gender') == 'F':
        student_name = f"(Miss) {student_name}"
    
    elements.append(Paragraph(f"<b>Name:</b> {student_name}", info_style))
    elements.append(Paragraph(f"<b>Matric Number:</b> {student_data['matric_number']}", info_style))
    elements.append(Paragraph(f"<b>Programme:</b> {student_data['program']}", info_style))
    elements.append(Paragraph(f"<b>Level:</b> {student_data['level']}", info_style))
    elements.append(Paragraph(f"<b>Session:</b> {results_data['session']}", info_style))
    elements.append(Spacer(1, 15))
    
    # First Semester Results
    if results_data.get('first_semester'):
        elements.append(Paragraph("<b>FIRST SEMESTER</b>", styles['InfoText']))
        elements.append(Spacer(1, 8))
        
        first_table_data = [['S/N', 'Course Code', 'Course Title', 'Unit', 'Score', 'Grade', 'Points']]
        for idx, result in enumerate(results_data['first_semester'], 1):
            first_table_data.append([
                str(idx),
                result['course_code'],
                result['course_title'][:30],
                str(result['credit_unit']),
                str(int(result['total_score'])),
                result['grade'],
                str(result['grade_point'])
            ])
        
        # Summary row
        summary = results_data.get('first_semester_summary', {})
        first_table_data.append([
            '', '', 'TOTAL', str(summary.get('total', 0)), '', '',
            f"GPA: {summary.get('gpa', 0.00):.2f}"
        ])
        
        first_table = Table(first_table_data, colWidths=[1*cm, 2.5*cm, 6*cm, 1.2*cm, 1.5*cm, 1.2*cm, 2*cm])
        first_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(first_table)
        elements.append(Spacer(1, 15))
    
    # Second Semester Results
    if results_data.get('second_semester'):
        elements.append(Paragraph("<b>SECOND SEMESTER</b>", styles['InfoText']))
        elements.append(Spacer(1, 8))
        
        second_table_data = [['S/N', 'Course Code', 'Course Title', 'Unit', 'Score', 'Grade', 'Points']]
        for idx, result in enumerate(results_data['second_semester'], 1):
            second_table_data.append([
                str(idx),
                result['course_code'],
                result['course_title'][:30],
                str(result['credit_unit']),
                str(int(result['total_score'])),
                result['grade'],
                str(result['grade_point'])
            ])
        
        summary = results_data.get('second_semester_summary', {})
        second_table_data.append([
            '', '', 'TOTAL', str(summary.get('total', 0)), '', '',
            f"GPA: {summary.get('gpa', 0.00):.2f}"
        ])
        
        second_table = Table(second_table_data, colWidths=[1*cm, 2.5*cm, 6*cm, 1.2*cm, 1.5*cm, 1.2*cm, 2*cm])
        second_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(second_table)
        elements.append(Spacer(1, 15))
    
    # Cumulative/Semester Summary
    cumulative = results_data.get('cumulative', {})
    summary_title = results_data.get('summary_title', 'CUMULATIVE SUMMARY')
    gpa_label = results_data.get('gpa_label', 'Cumulative GPA')
    summary_gpa = results_data.get('summary_gpa', cumulative.get('cgpa', 0.00))
    elements.append(Spacer(1, 10))
    summary_style = ParagraphStyle(
        name='Summary',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    elements.append(Paragraph(summary_title, summary_style))
    elements.append(Paragraph(f"Total Credit Units Passed: {cumulative.get('passed', 0)}", info_style))
    elements.append(Paragraph(f"Total Credit Units Failed: {cumulative.get('failed', 0)}", info_style))
    elements.append(Paragraph(f"Total Credit Units Registered: {cumulative.get('total', 0)}", info_style))
    elements.append(Paragraph(f"<b>{gpa_label}: {summary_gpa:.2f}</b>", info_style))
    
    # Footer
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER
    )
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
    elements.append(Paragraph("This is a computer-generated document and does not require a signature.", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
