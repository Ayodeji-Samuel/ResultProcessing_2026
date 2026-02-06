"""
Test script for combined semester PDF generation
Tests all the fixes: column widths, font sizing, and second semester heading
"""
import sys
import os
from io import BytesIO

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.pdf_generator import generate_spreadsheet_pdf

def test_combined_semester_pdf():
    """Test PDF generation for combined semesters"""
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("TESTING COMBINED SEMESTER PDF GENERATION")
        print("=" * 80)
    
    # Sample data for combined semesters
    first_courses_data = [
        {'code': 'CSC201', 'title': 'Data Structures and Algorithms', 'status': 'C', 'credit_unit': 3},
        {'code': 'CSC203', 'title': 'Object Oriented Programming', 'status': 'C', 'credit_unit': 3},
        {'code': 'MTH201', 'title': 'Mathematical Methods I', 'status': 'R', 'credit_unit': 3},
        {'code': 'STA201', 'title': 'Probability Theory', 'status': 'R', 'credit_unit': 2},
    ]
    
    second_courses_data = [
        {'code': 'CSC202', 'title': 'Database Management Systems', 'status': 'C', 'credit_unit': 3},
        {'code': 'CSC204', 'title': 'Computer Architecture', 'status': 'C', 'credit_unit': 3},
        {'code': 'MTH202', 'title': 'Mathematical Methods II', 'status': 'R', 'credit_unit': 3},
        {'code': 'STA202', 'title': 'Statistical Inference', 'status': 'R', 'credit_unit': 2},
    ]
    
    students_data = [
        {
            'matric_number': 'CS/2023/001',
            'name': 'ADEYEMI JOHN',
            'gender': 'M',
            'first_semester': {
                'CSC201': '75 (A)',
                'CSC203': '68 (B)',
                'MTH201': '62 (B)',
                'STA201': '55 (C)',
            },
            'first_semester_summary': {
                'failed_units': 0,
                'passed_units': 11,
                'total_units': 11,
                'gpa': 4.18
            },
            'second_semester': {
                'CSC202': '72 (A)',
                'CSC204': '65 (B)',
                'MTH202': '58 (C)',
                'STA202': '60 (B)',
            },
            'second_semester_summary': {
                'failed_units': 0,
                'passed_units': 11,
                'total_units': 11,
                'gpa': 3.91
            },
            'session_summary': {
                'failed_units': 0,
                'passed_units': 22,
                'total_units': 22,
                'cgpa': 4.05
            },
            'remark': 'Proceed'
        },
        {
            'matric_number': 'CS/2023/002',
            'name': 'BAKARE ESTHER',
            'gender': 'F',
            'first_semester': {
                'CSC201': '68 (B)',
                'CSC203': '72 (A)',
                'MTH201': '38 (F)',
                'STA201': '52 (C)',
            },
            'first_semester_summary': {
                'failed_units': 3,
                'passed_units': 8,
                'total_units': 11,
                'gpa': 3.09
            },
            'second_semester': {
                'CSC202': '70 (A)',
                'CSC204': '66 (B)',
                'MTH202': '54 (C)',
                'STA202': '58 (C)',
            },
            'second_semester_summary': {
                'failed_units': 0,
                'passed_units': 11,
                'total_units': 11,
                'gpa': 3.73
            },
            'session_summary': {
                'failed_units': 3,
                'passed_units': 19,
                'total_units': 22,
                'cgpa': 3.41
            },
            'remark': 'CO: MTH201'
        },
        {
            'matric_number': 'CS/2023/003',
            'name': 'CHUKWUEMEKA PROMISE',
            'gender': 'M',
            'first_semester': {
                'CSC201': '82 (A)',
                'CSC203': '78 (A)',
                'MTH201': '70 (A)',
                'STA201': '65 (B)',
            },
            'first_semester_summary': {
                'failed_units': 0,
                'passed_units': 11,
                'total_units': 11,
                'gpa': 4.64
            },
            'second_semester': {
                'CSC202': '80 (A)',
                'CSC204': '75 (A)',
                'MTH202': '68 (B)',
                'STA202': '70 (A)',
            },
            'second_semester_summary': {
                'failed_units': 0,
                'passed_units': 11,
                'total_units': 11,
                'gpa': 4.55
            },
            'session_summary': {
                'failed_units': 0,
                'passed_units': 22,
                'total_units': 22,
                'cgpa': 4.59
            },
            'remark': 'Proceed'
        },
    ]
    
    data = {
        'students': students_data,
        'first_semester_courses': first_courses_data,
        'second_semester_courses': second_courses_data,
        'level': 200,
        'program': 'Computer Science',
        'semester': 'both',
        'session': '2023/2024'
    }
    
    config = {
        'university_name': 'EDO STATE UNIVERSITY UZAIRUE',
        'faculty_name': 'Faculty of Science',
        'department_name': 'Computer Science'
    }
    
    signatories = {
        'course_adviser': 'Dr. A. B. Adeleke',
        'hod': 'Prof. C. D. Okonkwo',
        'dean': 'Prof. E. F. Okafor'
    }
    
    # Test different font sizes
    test_cases = [
        {'font_size': 10, 'description': 'Default (10pt)'},
        {'font_size': 12, 'description': 'Larger (12pt)'},
        {'font_size': 8, 'description': 'Should auto-adjust to 10pt minimum'},
    ]
    
    for idx, test_case in enumerate(test_cases, 1):
        font_size = test_case['font_size']
        description = test_case['description']
        
        print(f"\nTest {idx}: {description}")
        print("-" * 60)
        
        try:
            pdf_buffer = generate_spreadsheet_pdf(data, config, signatories, font_size=font_size)
            
            if pdf_buffer and isinstance(pdf_buffer, BytesIO):
                pdf_size = len(pdf_buffer.getvalue())
                print(f"✓ PDF generated successfully")
                print(f"  - Size: {pdf_size:,} bytes")
                print(f"  - Font size requested: {font_size}pt")
                
                # Save to file for manual inspection
                filename = f"test_combined_sem_font{font_size}.pdf"
                with open(filename, 'wb') as f:
                    f.write(pdf_buffer.getvalue())
                print(f"  - Saved as: {filename}")
            else:
                print("✗ Failed - No PDF buffer returned")
        except Exception as e:
            print(f"✗ Failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("VERIFICATION CHECKLIST:")
        print("=" * 80)
        print("Please open the generated PDFs and verify:")
        print("1. ✓ First semester heading is visible and spans correctly")
        print("2. ✓ Second semester heading is visible and spans correctly")
        print("3. ✓ Column widths are appropriate (not too wide)")
        print("4. ✓ No content overlapping")
        print("5. ✓ Font size is readable (minimum 10pt)")
        print("6. ✓ All course codes and titles are visible")
        print("7. ✓ Summary columns (CUF, CUP, TCU, GPA, CGPA) are correct")
        print("8. ✓ Session summary shows combined results")
        print("9. ✓ Remarks show carryovers correctly")
        print("=" * 80)
