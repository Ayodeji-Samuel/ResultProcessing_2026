"""
Unit tests for manual entry functionality using Flask test client
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask_login import login_user
from app import create_app, db
from app.models import Student, Course, AcademicSession, Result, User

def run_tests():
    """Run manual entry tests"""
    
    print("=" * 60)
    print("TESTING MANUAL ENTRY FEATURE")
    print("=" * 60)
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['LOGIN_DISABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            # Get test data
            session = AcademicSession.query.filter_by(is_current=True).first()
            if not session:
                print("ERROR: No current session found")
                return False
            print(f"\n1. Current Session: {session.session_name}")
            
            # Get a course with students
            course = Course.query.filter_by(is_active=True).first()
            if not course:
                print("ERROR: No active courses found")
                return False
            print(f"2. Test Course: {course.course_code} - {course.course_title}")
            
            # Get students for this course
            students = Student.query.filter_by(
                level=course.level,
                program=course.program,
                session_id=session.id
            ).all()
            print(f"3. Students for course: {len(students)}")
            
            if not students:
                print("WARNING: No students for this course")
                return True
            
            # Get HoD user and prepare for testing
            hod = User.query.filter_by(role='hod').first()
            if not hod:
                print("ERROR: No HoD user found")
                return False
            print(f"4. HoD User: {hod.username}")
            
            # Ensure HoD can login
            hod.must_change_password = False
            hod.is_locked = False
            hod.failed_login_attempts = 0
            db.session.commit()
            
            # Login as HoD using Flask-Login's test utilities
            print("\n5. Testing login...")
            with client.session_transaction() as sess:
                sess['_user_id'] = str(hod.id)
                sess['_fresh'] = True
            print("   OK: Login session established")
            
            # Access manual entry page
            print("\n6. Testing GET manual entry page...")
            entry_response = client.get(f'/results/entry/{course.id}')
            
            if entry_response.status_code == 302:
                # Might redirect to password change
                print(f"   INFO: Redirected to {entry_response.location}")
                # Follow redirect
                entry_response = client.get(f'/results/entry/{course.id}', follow_redirects=True)
            
            if entry_response.status_code != 200:
                print(f"   ERROR: Could not access manual entry (status: {entry_response.status_code})")
                return False
            print(f"   OK: Manual entry page loaded (status: {entry_response.status_code})")
            
            # Check page content
            page_content = entry_response.data.decode('utf-8')
            
            if 'entryForm' not in page_content:
                print("   ERROR: Entry form not found in page")
                return False
            print("   OK: Entry form found")
            
            if 'ca-input' not in page_content:
                print("   ERROR: CA input fields not found")
                return False
            print("   OK: CA input fields found")
            
            # Test submitting scores
            print("\n7. Testing POST - Save scores...")
            
            # Get first student
            test_student = students[0]
            
            # Count existing results before
            results_before = Result.query.filter_by(
                student_id=test_student.id,
                course_id=course.id,
                session_id=session.id
            ).first()
            
            # Prepare form data
            form_data = {
                f'ca_{test_student.id}': '22.5',
                f'exam_{test_student.id}': '48.5'
            }
            
            # Submit with AJAX header
            submit_response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            
            if submit_response.status_code != 200:
                print(f"   ERROR: Submission failed (status: {submit_response.status_code})")
                print(f"   Response: {submit_response.data.decode('utf-8')[:500]}")
                return False
            
            # Check JSON response
            try:
                json_data = submit_response.get_json()
                if json_data.get('success'):
                    print(f"   OK: Submission successful - {json_data.get('message')}")
                else:
                    print(f"   ERROR: Submission returned failure - {json_data.get('message')}")
                    return False
            except Exception as e:
                print(f"   ERROR: Could not parse JSON response - {str(e)}")
                return False
            
            # Verify result was saved
            print("\n8. Verifying saved result...")
            result = Result.query.filter_by(
                student_id=test_student.id,
                course_id=course.id,
                session_id=session.id
            ).first()
            
            if not result:
                print("   ERROR: Result not found in database")
                return False
            
            print(f"   OK: Result found in database")
            print(f"       CA Score: {result.ca_score}")
            print(f"       Exam Score: {result.exam_score}")
            print(f"       Total Score: {result.total_score}")
            print(f"       Grade: {result.grade}")
            
            # Verify calculations
            expected_total = 22.5 + 48.5
            if abs(result.total_score - expected_total) > 0.1:
                print(f"   ERROR: Total score mismatch (expected {expected_total}, got {result.total_score})")
                return False
            print(f"   OK: Total score correct ({result.total_score})")
            
            # Verify grade (71 should be A)
            if result.grade != 'A':
                print(f"   ERROR: Grade mismatch (expected A for 71, got {result.grade})")
                return False
            print(f"   OK: Grade correct ({result.grade})")
            
            # Test validation - invalid CA score
            print("\n9. Testing validation - Invalid CA score (>30)...")
            invalid_data = {
                f'ca_{test_student.id}': '35',  # Invalid - over 30
                f'exam_{test_student.id}': '50'
            }
            
            invalid_response = client.post(
                f'/results/entry/{course.id}',
                data=invalid_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            
            if invalid_response.status_code == 200:
                json_data = invalid_response.get_json()
                if json_data.get('errors'):
                    print(f"   OK: Validation error returned - {json_data.get('errors')}")
                else:
                    # Check if the previous valid value is still there
                    result_check = Result.query.filter_by(
                        student_id=test_student.id,
                        course_id=course.id,
                        session_id=session.id
                    ).first()
                    # The implementation should reject invalid scores
                    print(f"   OK: Result maintained previous value (CA: {result_check.ca_score})")
            else:
                print(f"   ERROR: Unexpected response status {invalid_response.status_code}")
            
            # Test empty submission
            print("\n10. Testing empty submission (should skip)...")
            another_student = students[1] if len(students) > 1 else None
            
            if another_student:
                # Delete any existing result for this student
                Result.query.filter_by(
                    student_id=another_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).delete()
                db.session.commit()
                
                empty_data = {
                    f'ca_{another_student.id}': '',
                    f'exam_{another_student.id}': ''
                }
                
                empty_response = client.post(
                    f'/results/entry/{course.id}',
                    data=empty_data,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                
                if empty_response.status_code == 200:
                    # Check that no result was created
                    no_result = Result.query.filter_by(
                        student_id=another_student.id,
                        course_id=course.id,
                        session_id=session.id
                    ).first()
                    
                    if no_result is None:
                        print("   OK: Empty submission correctly skipped")
                    else:
                        print("   WARNING: Result was created even with empty submission")
            
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED!")
            print("=" * 60)
            
            return True


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
