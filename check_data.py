"""Check database data"""
from app import create_app, db
from app.models import AcademicSession, Student, Course, Result

app = create_app()

with app.app_context():
    sessions = AcademicSession.query.all()
    print('=== Sessions ===')
    for s in sessions:
        print(f'{s.id}. {s.session_name} - Current: {s.is_current}')
    
    current = AcademicSession.query.filter_by(is_current=True).first()
    print(f'\nCurrent Session: {current.session_name if current else "None"}')
    
    print(f'\n=== Data Counts ===')
    print(f'Students: {Student.query.count()}')
    print(f'Courses: {Course.query.count()}')
    print(f'Results: {Result.query.count()}')
    
    if current:
        print(f'\nData for current session ({current.session_name}):')
        print(f'  Students: {Student.query.filter_by(session_id=current.id).count()}')
        print(f'  Courses: {Course.query.filter_by(session_id=current.id).count()}')
        
        # Get results count for current session
        results_count = db.session.query(Result).join(Course).filter(
            Course.session_id == current.id
        ).count()
        print(f'  Results: {results_count}')
        
        # Show some sample data
        print(f'\n=== Sample Students ===')
        students = Student.query.filter_by(session_id=current.id).limit(5).all()
        for st in students:
            print(f'  {st.matric_number} - {st.surname} {st.first_name} ({st.level} Level)')
        
        print(f'\n=== Sample Courses ===')
        courses = Course.query.filter_by(session_id=current.id).limit(5).all()
        for c in courses:
            print(f'  {c.course_code} - {c.course_title} ({c.level} Level)')
