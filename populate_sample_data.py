"""
Populate database with sample data for testing
"""
from app import create_app, db
from app.models import User, Student, Course, Result, AcademicSession, GradingSystem
from werkzeug.security import generate_password_hash
from datetime import datetime

app = create_app()

with app.app_context():
    print("Creating sample data...")
    
    # Create academic session
    session = AcademicSession.query.filter_by(is_current=True).first()
    if not session:
        session = AcademicSession(
            session_name='2025/2026',
            description='Current Academic Session',
            is_current=True
        )
        db.session.add(session)
        db.session.commit()
        print(f"✓ Created session: {session.session_name}")
    
    # Create level advisers
    advisers = [
        {
            'username': 'adviser1@university.edu.ng',
            'email': 'adviser1@university.edu.ng',
            'password': 'Adviser@123',
            'full_name': 'Dr. Ibrahim Abubakar',
            'role': 'level_adviser',
            'program': 'Computer Science',
            'level': 100
        },
        {
            'username': 'adviser2@university.edu.ng',
            'email': 'adviser2@university.edu.ng',
            'password': 'Adviser@123',
            'full_name': 'Dr. Blessing Okonkwo',
            'role': 'level_adviser',
            'program': 'Computer Science',
            'level': 200
        },
        {
            'username': 'adviser3@university.edu.ng',
            'email': 'adviser3@university.edu.ng',
            'password': 'Adviser@123',
            'full_name': 'Prof. Ahmed Yusuf',
            'role': 'level_adviser',
            'program': 'Software Engineering',
            'level': 100
        }
    ]
    
    for adv_data in advisers:
        if not User.query.filter_by(username=adv_data['username']).first():
            adviser = User(
                username=adv_data['username'],
                email=adv_data['email'],
                password_hash=generate_password_hash(adv_data['password']),
                full_name=adv_data['full_name'],
                role=adv_data['role'],
                program=adv_data['program'],
                level=adv_data['level'],
                is_active=True,
                must_change_password=False
            )
            db.session.add(adviser)
            print(f"✓ Created adviser: {adv_data['full_name']}")
    
    db.session.commit()
    
    # Create students
    students_data = [
        # Computer Science 100 Level
        {'matric': 'CS/2025/001', 'surname': 'Johnson', 'first_name': 'Adekunle', 'program': 'Computer Science', 'level': 100},
        {'matric': 'CS/2025/002', 'surname': 'Mohammed', 'first_name': 'Fatima', 'program': 'Computer Science', 'level': 100},
        {'matric': 'CS/2025/003', 'surname': 'Okafor', 'first_name': 'Chinedu', 'program': 'Computer Science', 'level': 100},
        {'matric': 'CS/2025/004', 'surname': 'Eze', 'first_name': 'Blessing', 'program': 'Computer Science', 'level': 100},
        {'matric': 'CS/2025/005', 'surname': 'Garba', 'first_name': 'Ibrahim', 'program': 'Computer Science', 'level': 100},
        # Computer Science 200 Level
        {'matric': 'CS/2024/001', 'surname': 'Nwosu', 'first_name': 'Adaeze', 'program': 'Computer Science', 'level': 200},
        {'matric': 'CS/2024/002', 'surname': 'Abdullahi', 'first_name': 'Yusuf', 'program': 'Computer Science', 'level': 200},
        {'matric': 'CS/2024/003', 'surname': 'Okoro', 'first_name': 'Grace', 'program': 'Computer Science', 'level': 200},
        # Software Engineering 100 Level
        {'matric': 'SE/2025/001', 'surname': 'Obi', 'first_name': 'Emeka', 'program': 'Software Engineering', 'level': 100},
        {'matric': 'SE/2025/002', 'surname': 'Bello', 'first_name': 'Aisha', 'program': 'Software Engineering', 'level': 100},
        {'matric': 'SE/2025/003', 'surname': 'Adeyemi', 'first_name': 'Michael', 'program': 'Software Engineering', 'level': 100},
        # Cyber Security 100 Level
        {'matric': 'CY/2025/001', 'surname': 'Adebayo', 'first_name': 'Funmilayo', 'program': 'Cyber Security', 'level': 100},
        {'matric': 'CY/2025/002', 'surname': 'Hassan', 'first_name': 'Khalid', 'program': 'Cyber Security', 'level': 100},
    ]
    
    for std_data in students_data:
        if not Student.query.filter_by(matric_number=std_data['matric']).first():
            student = Student(
                matric_number=std_data['matric'],
                surname=std_data['surname'],
                first_name=std_data['first_name'],
                program=std_data['program'],
                level=std_data['level'],
                session_id=session.id,
                is_active=True
            )
            db.session.add(student)
            print(f"✓ Created student: {std_data['surname']} {std_data['first_name']} ({std_data['matric']})")
    
    db.session.commit()
    
    # Create courses
    courses_data = [
        # 100 Level First Semester
        {'code': 'CSC101', 'title': 'Introduction to Computer Science', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'CSC103', 'title': 'Introduction to Programming', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'MTH101', 'title': 'Elementary Mathematics I', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'PHY101', 'title': 'General Physics I', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'GST101', 'title': 'Use of English', 'units': 2, 'level': 100, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        # 100 Level Second Semester
        {'code': 'CSC102', 'title': 'Computer Programming I', 'units': 4, 'level': 100, 'semester': 'second', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'CSC104', 'title': 'Discrete Mathematics', 'units': 3, 'level': 100, 'semester': 'second', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'MTH102', 'title': 'Elementary Mathematics II', 'units': 3, 'level': 100, 'semester': 'second', 'program': 'Computer Science', 'compulsory': True},
        # 200 Level First Semester
        {'code': 'CSC201', 'title': 'Computer Programming II', 'units': 4, 'level': 200, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'CSC203', 'title': 'Data Structures', 'units': 3, 'level': 200, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        {'code': 'CSC205', 'title': 'Operating Systems', 'units': 3, 'level': 200, 'semester': 'first', 'program': 'Computer Science', 'compulsory': True},
        # Software Engineering
        {'code': 'SEN101', 'title': 'Introduction to Software Engineering', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Software Engineering', 'compulsory': True},
        {'code': 'SEN103', 'title': 'Programming Fundamentals', 'units': 4, 'level': 100, 'semester': 'first', 'program': 'Software Engineering', 'compulsory': True},
        # Cyber Security
        {'code': 'CYB101', 'title': 'Introduction to Cyber Security', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Cyber Security', 'compulsory': True},
        {'code': 'CYB103', 'title': 'Network Fundamentals', 'units': 3, 'level': 100, 'semester': 'first', 'program': 'Cyber Security', 'compulsory': True},
    ]
    
    for crs_data in courses_data:
        if not Course.query.filter_by(course_code=crs_data['code']).first():
            course = Course(
                course_code=crs_data['code'],
                course_title=crs_data['title'],
                credit_unit=crs_data['units'],
                level=crs_data['level'],
                semester=1 if crs_data['semester'] == 'first' else 2,
                program=crs_data['program'],
                status='C',
                is_active=True
            )
            db.session.add(course)
            print(f"✓ Created course: {crs_data['code']} - {crs_data['title']}")
    
    db.session.commit()
    
    # Create results
    import random
    
    students = Student.query.all()
    courses = Course.query.all()
    
    for student in students:
        # Get courses for this student's program and level
        student_courses = [c for c in courses if c.program == student.program and c.level == student.level]
        
        for course in student_courses:
            if not Result.query.filter_by(student_id=student.id, course_id=course.id, session_id=session.id).first():
                # Generate realistic scores
                ca_score = random.randint(15, 30)
                exam_score = random.randint(40, 70)
                total = ca_score + exam_score
                
                # Determine grade
                if total >= 70:
                    grade, points = 'A', 5.0
                elif total >= 60:
                    grade, points = 'B', 4.0
                elif total >= 50:
                    grade, points = 'C', 3.0
                elif total >= 45:
                    grade, points = 'D', 2.0
                else:
                    grade, points = 'F', 0.0
                
                result = Result(
                    student_id=student.id,
                    course_id=course.id,
                    session_id=session.id,
                    ca_score=ca_score,
                    exam_score=exam_score,
                    total_score=total,
                    grade=grade,
                    grade_point=points
                )
                db.session.add(result)
        
        print(f"✓ Created results for: {student.full_name}")
    
    db.session.commit()
    
    # Create grading system if not exists
    if GradingSystem.query.count() == 0:
        grading_data = [
            {'min': 70, 'max': 100, 'grade': 'A', 'point': 5.0, 'remark': 'Excellent'},
            {'min': 60, 'max': 69, 'grade': 'B', 'point': 4.0, 'remark': 'Very Good'},
            {'min': 50, 'max': 59, 'grade': 'C', 'point': 3.0, 'remark': 'Good'},
            {'min': 45, 'max': 49, 'grade': 'D', 'point': 2.0, 'remark': 'Fair'},
            {'min': 40, 'max': 44, 'grade': 'E', 'point': 1.0, 'remark': 'Pass'},
            {'min': 0, 'max': 39, 'grade': 'F', 'point': 0.0, 'remark': 'Fail'},
        ]
        
        for g_data in grading_data:
            grading = GradingSystem(
                degree_type='B.Sc.',
                min_score=g_data['min'],
                max_score=g_data['max'],
                grade=g_data['grade'],
                grade_point=g_data['point'],
                remark=g_data['remark']
            )
            db.session.add(grading)
        
        db.session.commit()
        print("✓ Created grading system")
    
    print("\n" + "="*60)
    print("SAMPLE DATA CREATED SUCCESSFULLY!")
    print("="*60)
    print("\nDatabase Statistics:")
    print(f"  Sessions: {AcademicSession.query.count()}")
    print(f"  Users: {User.query.count()}")
    print(f"  Students: {Student.query.count()}")
    print(f"  Courses: {Course.query.count()}")
    print(f"  Results: {Result.query.count()}")
    print("\nTest Accounts:")
    print("  HoD: hod@university.edu.ng / HoD@2026!")
    print("  Adviser 1: adviser1@university.edu.ng / Adviser@123")
    print("  Adviser 2: adviser2@university.edu.ng / Adviser@123")
    print("  Adviser 3: adviser3@university.edu.ng / Adviser@123")
    print("="*60)
