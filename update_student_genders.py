"""
Update existing students with gender information
"""
from app import create_app, db
from app.models import Student

app = create_app()

with app.app_context():
    print("Updating existing students with gender information...")
    print("=" * 60)
    
    # Define gender mapping based on names
    gender_map = {
        'CS/2025/001': 'M',  # Adekunle
        'CS/2025/002': 'F',  # Fatima
        'CS/2025/003': 'M',  # Chinedu
        'CS/2025/004': 'F',  # Blessing
        'CS/2025/005': 'M',  # Ibrahim
        'CS/2024/001': 'F',  # Adaeze
        'CS/2024/002': 'M',  # Yusuf
        'CS/2024/003': 'F',  # Grace
        'SE/2025/001': 'M',  # Emeka
        'SE/2025/002': 'F',  # Aisha
        'SE/2025/003': 'M',  # Michael
        'CY/2025/001': 'F',  # Funmilayo
        'CY/2025/002': 'M',  # Khalid
    }
    
    updated = 0
    for matric, gender in gender_map.items():
        student = Student.query.filter_by(matric_number=matric).first()
        if student:
            student.gender = gender
            print(f"✓ Updated {matric}: {student.full_name} -> {gender}")
            updated += 1
        else:
            print(f"✗ Student not found: {matric}")
    
    db.session.commit()
    
    print("\n" + "=" * 60)
    print(f"Updated {updated} students with gender information")
    print("=" * 60)
    
    # Verify updates
    print("\nVerification:")
    print("-" * 60)
    male = Student.query.filter_by(gender='M').count()
    female = Student.query.filter_by(gender='F').count()
    unspecified = Student.query.filter(Student.gender.is_(None)).count()
    
    print(f"Male Students: {male}")
    print(f"Female Students: {female}")
    print(f"Unspecified: {unspecified}")
    print("=" * 60)
