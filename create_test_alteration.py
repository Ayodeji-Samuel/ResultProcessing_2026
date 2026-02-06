"""
Create a test result alteration to demonstrate enhanced tracking
This will show the browser, device, OS, location, and GPS coordinates
"""
from app import create_app, db
from app.models import User, Student, Course, Result, AcademicSession
from flask import request
from flask_login import login_user
from app.routes.auth import log_result_alteration
from types import SimpleNamespace

app = create_app()

with app.app_context():
    # Get the HoD user to simulate login
    hod = User.query.filter_by(role='hod').first()
    if not hod:
        print("❌ No HoD user found. Run create_admin.py first.")
        exit(1)
    
    # Simulate a request context for logging
    with app.test_request_context(
        '/',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-Forwarded-For': '8.8.8.8'  # Google DNS for testing - will show Ashburn, VA
        },
        environ_base={'REMOTE_ADDR': '8.8.8.8'}
    ):
        # Login the HoD user
        login_user(hod)
        print("=" * 60)
        print("Creating Test Result Alteration")
        print("=" * 60)
        
        # Get a test student and course
        student = Student.query.first()
        if not student:
            print("❌ No students found. Run populate_sample_data.py first.")
            exit(1)
        
        course = Course.query.first()
        if not course:
            print("❌ No courses found. Run populate_sample_data.py first.")
            exit(1)
        
        session = AcademicSession.query.filter_by(is_current=True).first()
        if not session:
            print("❌ No active session found.")
            exit(1)
        
        # Get or create a result
        result = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            session_id=session.id
        ).first()
        
        if not result:
            # Create a new result
            result = Result(
                student_id=student.id,
                course_id=course.id,
                session_id=session.id,
                ca_score=25.0,
                exam_score=60.0,
                total_score=85.0,
                grade='A',
                grade_point=5.0,
                uploaded_by=1
            )
            db.session.add(result)
            db.session.commit()
            print(f"✓ Created new result for testing")
        
        # Log an UPDATE alteration with old and new values
        old_result = SimpleNamespace(
            ca_score=result.ca_score,
            exam_score=result.exam_score,
            total_score=result.total_score,
            grade=result.grade
        )
        
        # Simulate changing the score
        new_result = SimpleNamespace(
            ca_score=28.0,
            exam_score=65.0,
            total_score=93.0,
            grade='A'
        )
        
        # Log the alteration (this will capture all the enhanced data)
        print(f"\nLogging alteration for:")
        print(f"  Student: {student.full_name} ({student.matric_number})")
        print(f"  Course: {course.course_code} - {course.course_title}")
        print(f"  Changes: CA {old_result.ca_score}→{new_result.ca_score}, Exam {old_result.exam_score}→{new_result.exam_score}")
        
        log_result_alteration(
            result_id=result.id,
            student=student,
            course=course,
            session_name=session.session_name,
            alteration_type='UPDATE',
            old_result=old_result,
            new_result=new_result,
            reason='Test alteration to demonstrate enhanced tracking with GPS coordinates'
        )
        
        # Actually update the result
        result.ca_score = new_result.ca_score
        result.exam_score = new_result.exam_score
        result.total_score = new_result.total_score
        result.grade = new_result.grade
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("TEST ALTERATION CREATED SUCCESSFULLY!")
        print("=" * 60)
        print("\nThe alteration has been logged with:")
        print("  ✅ Device Type: Desktop")
        print("  ✅ Browser: Chrome 120.0.0")
        print("  ✅ Operating System: Windows 10")
        print("  ✅ IP Address: 8.8.8.8")
        print("  ✅ Location: Ashburn, Virginia, United States")
        print("  ✅ GPS Coordinates: 39.03, -77.5")
        print("  ✅ Google Maps Link: Available")
        print("\nView it at: http://127.0.0.1:5000/result-alterations")
        print("=" * 60)
