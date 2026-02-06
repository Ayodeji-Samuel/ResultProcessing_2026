"""
Create another test alteration to verify the fix
"""
from app import create_app, db
from app.models import User, Student, Course, Result, AcademicSession
from flask import request
from flask_login import login_user
from app.routes.auth import log_result_alteration
from types import SimpleNamespace

app = create_app()

with app.app_context():
    # Get the HoD user
    hod = User.query.filter_by(role='hod').first()
    
    with app.test_request_context(
        '/',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'X-Forwarded-For': '41.203.72.1'  # Nigerian IP for testing
        },
        environ_base={'REMOTE_ADDR': '41.203.72.1'}
    ):
        login_user(hod)
        
        print("=" * 60)
        print("Creating Another Test Alteration")
        print("=" * 60)
        
        # Get another student
        student = Student.query.filter_by(matric_number='CS/2025/002').first()
        course = Course.query.filter_by(course_code='CSC103').first()
        session = AcademicSession.query.filter_by(is_current=True).first()
        
        if not student or not course or not session:
            print("❌ Required data not found")
            exit(1)
        
        result = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            session_id=session.id
        ).first()
        
        if not result:
            result = Result(
                student_id=student.id,
                course_id=course.id,
                session_id=session.id,
                ca_score=20.0,
                exam_score=55.0,
                total_score=75.0,
                grade='A',
                grade_point=5.0,
                uploaded_by=1
            )
            db.session.add(result)
            db.session.commit()
        
        old_result = SimpleNamespace(
            ca_score=result.ca_score,
            exam_score=result.exam_score,
            total_score=result.total_score,
            grade=result.grade
        )
        
        new_result = SimpleNamespace(
            ca_score=29.0,
            exam_score=68.0,
            total_score=97.0,
            grade='A'
        )
        
        print(f"\nStudent: {student.full_name} ({student.matric_number})")
        print(f"Course: {course.course_code} - {course.course_title}")
        print(f"Browser: Firefox 121.0 (simulated)")
        print(f"IP: 41.203.72.1 (Nigerian IP)")
        
        log_result_alteration(
            result_id=result.id,
            student=student,
            course=course,
            session_name=session.session_name,
            alteration_type='UPDATE',
            old_result=old_result,
            new_result=new_result,
            reason='Second test - verifying User-Agent capture fix'
        )
        
        result.ca_score = new_result.ca_score
        result.exam_score = new_result.exam_score
        result.total_score = new_result.total_score
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("✅ TEST ALTERATION #2 CREATED!")
        print("=" * 60)
        print("\nThis should now show:")
        print("  ✅ Browser: Firefox 121.0")
        print("  ✅ Device: Desktop")
        print("  ✅ OS: Windows 10")
        print("  ✅ Location: Lagos, Nigeria (or similar)")
        print("  ✅ GPS Coordinates")
        print("\nRefresh http://127.0.0.1:5000/result-alterations to see it!")
        print("=" * 60)
