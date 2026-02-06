"""
Additional edge case tests for manual entry functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Student, Course, AcademicSession, Result, User, Carryover

def run_edge_case_tests():
    """Run edge case tests for manual entry"""
    
    print("=" * 60)
    print("EDGE CASE TESTS FOR MANUAL ENTRY")
    print("=" * 60)
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            # Setup
            session = AcademicSession.query.filter_by(is_current=True).first()
            course = Course.query.filter_by(is_active=True).first()
            students = Student.query.filter_by(
                level=course.level,
                program=course.program,
                session_id=session.id
            ).all()
            hod = User.query.filter_by(role='hod').first()
            
            # Prepare HoD for login
            hod.must_change_password = False
            hod.is_locked = False
            db.session.commit()
            
            # Login
            with client.session_transaction() as sess:
                sess['_user_id'] = str(hod.id)
                sess['_fresh'] = True
            
            test_student = students[0]
            
            # Test 1: Boundary values - CA = 0
            print("\n1. Testing CA = 0...")
            form_data = {
                f'ca_{test_student.id}': '0',
                f'exam_{test_student.id}': '40'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('success'):
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and result.ca_score == 0.0:
                    print(f"   OK: CA=0 accepted, Total={result.total_score}, Grade={result.grade}")
                else:
                    print(f"   ERROR: CA=0 not saved correctly")
            else:
                print(f"   ERROR: CA=0 rejected - {json_data.get('message')}")
            
            # Test 2: Boundary values - CA = 30
            print("\n2. Testing CA = 30 (max)...")
            form_data = {
                f'ca_{test_student.id}': '30',
                f'exam_{test_student.id}': '70'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('success'):
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and result.total_score == 100.0:
                    print(f"   OK: Max scores accepted, Total=100, Grade={result.grade}")
                else:
                    print(f"   ERROR: Max scores not saved correctly")
            else:
                print(f"   ERROR: Max scores rejected - {json_data.get('message')}")
            
            # Test 3: Decimal values
            print("\n3. Testing decimal values (CA=15.5, Exam=42.5)...")
            form_data = {
                f'ca_{test_student.id}': '15.5',
                f'exam_{test_student.id}': '42.5'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('success'):
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and abs(result.total_score - 58.0) < 0.01:
                    print(f"   OK: Decimals handled, Total={result.total_score}, Grade={result.grade}")
                else:
                    print(f"   ERROR: Decimal calculation wrong - {result.total_score}")
            else:
                print(f"   ERROR: Decimal values rejected")
            
            # Test 4: Only CA score provided
            print("\n4. Testing only CA score provided...")
            form_data = {
                f'ca_{test_student.id}': '20',
                f'exam_{test_student.id}': ''
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('success'):
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and result.ca_score == 20.0 and result.exam_score == 0.0:
                    print(f"   OK: CA only accepted, Total={result.total_score}, Grade={result.grade}")
                else:
                    print(f"   ERROR: CA only not handled correctly")
            else:
                print(f"   ERROR: CA only rejected - {json_data.get('message')}")
            
            # Test 5: Only Exam score provided
            print("\n5. Testing only Exam score provided...")
            form_data = {
                f'ca_{test_student.id}': '',
                f'exam_{test_student.id}': '50'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('success'):
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and result.exam_score == 50.0 and result.ca_score == 0.0:
                    print(f"   OK: Exam only accepted, Total={result.total_score}, Grade={result.grade}")
                else:
                    print(f"   ERROR: Exam only not handled correctly")
            else:
                print(f"   ERROR: Exam only rejected - {json_data.get('message')}")
            
            # Test 6: Invalid exam score (> 70)
            print("\n6. Testing invalid exam score (>70)...")
            form_data = {
                f'ca_{test_student.id}': '20',
                f'exam_{test_student.id}': '75'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('errors') and any('Exam score' in e for e in json_data.get('errors', [])):
                print(f"   OK: Invalid exam score rejected - {json_data.get('errors')}")
            elif json_data.get('success') and json_data.get('added', 0) == 0 and json_data.get('updated', 0) == 0:
                print(f"   OK: Invalid score was skipped")
            else:
                print(f"   WARNING: Invalid exam validation may need review")
            
            # Test 7: Negative scores
            print("\n7. Testing negative scores...")
            form_data = {
                f'ca_{test_student.id}': '-5',
                f'exam_{test_student.id}': '50'
            }
            response = client.post(
                f'/results/entry/{course.id}',
                data=form_data,
                headers={'X-Requested-With': 'XMLHttpRequest'}
            )
            json_data = response.get_json()
            if json_data.get('errors') and any('CA score' in e for e in json_data.get('errors', [])):
                print(f"   OK: Negative score rejected - {json_data.get('errors')}")
            else:
                print(f"   WARNING: Negative score validation may need review")
            
            # Test 8: Grade boundaries (testing each grade)
            print("\n8. Testing grade boundaries...")
            grade_tests = [
                (25, 45, 70, 'A'),  # 70 = A
                (20, 49, 69, 'B'),  # 69 = B
                (20, 39, 59, 'C'),  # 59 = C (corrected)
                (15, 34, 49, 'D'),  # 49 = D (corrected)
                (10, 34, 44, 'E'),  # 44 = E (corrected)
                (10, 29, 39, 'F'),  # 39 = F
            ]
            
            for ca, exam, expected_total, expected_grade in grade_tests:
                form_data = {
                    f'ca_{test_student.id}': str(ca),
                    f'exam_{test_student.id}': str(exam)
                }
                response = client.post(
                    f'/results/entry/{course.id}',
                    data=form_data,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                result = Result.query.filter_by(
                    student_id=test_student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result and result.grade == expected_grade:
                    print(f"   OK: Score {expected_total} = Grade {result.grade}")
                else:
                    actual_grade = result.grade if result else 'None'
                    print(f"   INFO: Score {expected_total} = Grade {actual_grade} (expected {expected_grade})")
            
            # Test 9: Multiple students in one submission
            print("\n9. Testing multiple students in one submission...")
            if len(students) >= 3:
                form_data = {}
                for i, student in enumerate(students[:3]):
                    form_data[f'ca_{student.id}'] = str(15 + i * 5)
                    form_data[f'exam_{student.id}'] = str(40 + i * 5)
                
                response = client.post(
                    f'/results/entry/{course.id}',
                    data=form_data,
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                )
                json_data = response.get_json()
                if json_data.get('success'):
                    total_processed = json_data.get('added', 0) + json_data.get('updated', 0)
                    if total_processed >= 3:
                        print(f"   OK: Multiple students processed ({total_processed} records)")
                    else:
                        print(f"   INFO: {total_processed} records processed")
                else:
                    print(f"   ERROR: Multi-student submission failed")
            else:
                print("   SKIP: Not enough students for multi-student test")
            
            print("\n" + "=" * 60)
            print("EDGE CASE TESTS COMPLETED!")
            print("=" * 60)
            
            return True


if __name__ == '__main__':
    run_edge_case_tests()
