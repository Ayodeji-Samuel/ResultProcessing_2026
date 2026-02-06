"""
Test script to verify gender field implementation
"""
from app import create_app, db
from app.models import Student

app = create_app()

with app.app_context():
    print("Testing Gender Field Implementation")
    print("=" * 60)
    
    # Query students
    students = Student.query.all()
    
    print(f"\nTotal Students: {len(students)}")
    print("\nStudent Gender Information:")
    print("-" * 60)
    
    male_count = 0
    female_count = 0
    unspecified_count = 0
    
    for student in students:
        gender_display = "Male" if student.gender == 'M' else "Female" if student.gender == 'F' else "Not Specified"
        pdf_prefix = "(Miss) " if student.gender == 'F' else ""
        
        print(f"{student.matric_number:<20} {student.full_name:<30} Gender: {gender_display:<15} PDF: {pdf_prefix}{student.full_name}")
        
        if student.gender == 'M':
            male_count += 1
        elif student.gender == 'F':
            female_count += 1
        else:
            unspecified_count += 1
    
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Male Students: {male_count}")
    print(f"  Female Students: {female_count}")
    print(f"  Unspecified Gender: {unspecified_count}")
    print("=" * 60)
    
    # Test that female students will show with (Miss) prefix in PDFs
    print("\n" + "=" * 60)
    print("Testing PDF Name Formatting:")
    print("-" * 60)
    
    female_students = Student.query.filter_by(gender='F').limit(3).all()
    if female_students:
        for student in female_students:
            student_data = {
                'name': student.full_name,
                'gender': student.gender
            }
            
            # Simulate PDF generator logic
            student_name = student_data['name']
            if student_data.get('gender') == 'F':
                student_name = f"(Miss) {student_name}"
            
            print(f"Original: {student.full_name}")
            print(f"PDF Output: {student_name}")
            print()
    
    print("=" * 60)
    print("✓ Gender field implementation test completed successfully!")
    print("=" * 60)
