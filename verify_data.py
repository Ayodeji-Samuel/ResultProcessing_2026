"""Verify data visibility"""
from app import create_app, db
from app.models import AcademicSession, Student, Course, Result

app = create_app()

with app.app_context():
    current = AcademicSession.query.filter_by(is_current=True).first()
    print(f'✓ Current Session: {current.session_name}\n')
    
    print('=== Data Summary ===')
    students = Student.query.filter_by(session_id=current.id).all()
    print(f'Students: {len(students)}')
    
    courses = Course.query.all()
    print(f'Courses: {len(courses)}')
    
    results = Result.query.filter_by(session_id=current.id).all()
    print(f'Results: {len(results)}')
    
    print('\n=== Sample Students (First 5) ===')
    for st in students[:5]:
        print(f'  {st.matric_number:<15} {st.surname} {st.first_name:<15} ({st.level} Level, {st.program})')
    
    print('\n=== Sample Courses (First 5) ===')
    for c in courses[:5]:
        result_count = Result.query.filter_by(course_id=c.id, session_id=current.id).count()
        print(f'  {c.course_code:<10} {c.course_title:<35} ({c.level}L, {result_count} results)')
    
    print('\n=== Sample Results (First 5) ===')
    for r in results[:5]:
        print(f'  {r.student.matric_number:<15} {r.course.course_code:<10} CA:{r.ca_score:>2} Exam:{r.exam_score:>2} Total:{r.total_score:>3} Grade:{r.grade}')
