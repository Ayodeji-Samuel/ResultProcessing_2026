"""
Simple standalone test for PDF generation without Flask app dependencies
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
import sys
import os

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the VerticalText class
from app.utils.pdf_generator import VerticalText

def simple_pdf_test():
    """Simple PDF generation test without Flask dependencies"""
    
    print("=" * 80)
    print("SIMPLE PDF GENERATION TEST")
    print("=" * 80)
    
    buffer = BytesIO()
    page_size = landscape(A4)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=0.5*cm,
        rightMargin=0.5*cm,
        topMargin=0.5*cm,
        bottomMargin=0.5*cm
    )
    
    # Create simple table data
    data = [
        ['S/N', 'Name', 'FIRST SEMESTER', '', '', 'SECOND SEMESTER', '', '', 'Remarks'],
        ['', '', VerticalText('CSC201'), VerticalText('CSC203'), 'GPA', VerticalText('CSC202'), VerticalText('CSC204'), 'GPA', ''],
        ['1', 'Student One', '75', '68', '4.0', '72', '65', '3.8', 'Proceed'],
        ['2', 'Student Two', '70', '72', '4.2', '68', '70', '4.0', 'Proceed'],
    ]
    
    # Calculate column widths
    col_widths = [0.7*cm, 3*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1*cm, 1*cm, 2*cm]
    
    table = Table(data, colWidths=col_widths)
    
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 1), 10),
        ('FONTSIZE', (0, 2), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        # Span headers
        ('SPAN', (2, 0), (4, 0)),  # First semester
        ('SPAN', (5, 0), (7, 0)),  # Second semester
    ])
    
    table.setStyle(style)
    
    doc.build([table])
    buffer.seek(0)
    
    # Save PDF
    filename = 'simple_test.pdf'
    with open(filename, 'wb') as f:
        f.write(buffer.getvalue())
    
    print(f"✓ PDF generated: {filename}")
    print(f"✓ Size: {len(buffer.getvalue()):,} bytes")
    print("\nPlease check the PDF to verify:")
    print("1. First semester heading spans correctly")
    print("2. Second semester heading spans correctly")
    print("3. Vertical text is readable")
    print("4. Column widths are appropriate")
    print("=" * 80)

if __name__ == '__main__':
    simple_pdf_test()
