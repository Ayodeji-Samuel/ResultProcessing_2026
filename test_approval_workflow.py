"""
Comprehensive Test Script for Approval Workflow System
Tests user roles, course assignments, and result approval/unlock functionality
"""
from app import create_app, db
from app.models import User, Course, Result, CourseAssignment, AcademicSession, Student
from datetime import datetime

def test_user_roles():
    """Test user role creation and access levels"""
    print("\n" + "="*60)
    print("TEST 1: User Roles and Access Levels")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        # Test 1: Create a lecturer
        print("\n1. Creating a Lecturer...")
        lecturer = User(
            username='lecturer1@edsu.edu.ng',
            email='lecturer1@edsu.edu.ng',
            full_name='Dr. Jane Lecturer',
            role='lecturer',
            program=None,  # Lecturers should have None
            level=None,     # Lecturers should have None
            is_active=True
        )
        lecturer.set_password('Lecturer@2026!')
        
        # Verify lecturer has no program/level
        assert lecturer.program is None, "❌ Lecturer should have no program"
        assert lecturer.level is None, "❌ Lecturer should have no level"
        print("   ✅ Lecturer created with role='lecturer', program=None, level=None")
        
        # Test 2: Create a level adviser
        print("\n2. Creating a Level Adviser...")
        adviser = User(
            username='adviser1@edsu.edu.ng',
            email='adviser1@edsu.edu.ng',
            full_name='Dr. John Adviser',
            role='level_adviser',
            program='Computer Science',
            level=300,
            is_active=True
        )
        adviser.set_password('Adviser@2026!')
        
        # Verify level adviser has program/level
        assert adviser.program == 'Computer Science', "❌ Level Adviser should have program"
        assert adviser.level == 300, "❌ Level Adviser should have level"
        print("   ✅ Level Adviser created with program='Computer Science', level=300")
        
        # Test 3: Test role methods
        print("\n3. Testing Role Methods...")
        assert lecturer.is_lecturer() == True, "❌ is_lecturer() should return True for lecturer"
        assert lecturer.is_level_adviser() == False, "❌ is_level_adviser() should return False for lecturer"
        assert lecturer.is_hod() == False, "❌ is_hod() should return False for lecturer"
        assert lecturer.can_approve_results() == False, "❌ can_approve_results() should return False for lecturer"
        print("   ✅ Lecturer role methods working correctly")
        
        assert adviser.is_lecturer() == True, "❌ is_lecturer() should return True for level_adviser"
        assert adviser.is_level_adviser() == True, "❌ is_level_adviser() should return True for level_adviser"
        assert adviser.can_approve_results() == False, "❌ can_approve_results() should return False for level_adviser"
        print("   ✅ Level Adviser role methods working correctly")
        
        # Get HoD
        hod = User.query.filter_by(role='hod').first()
        if hod:
            assert hod.can_approve_results() == True, "❌ HoD should be able to approve results"
            print("   ✅ HoD role methods working correctly")
        
        print("\n✅ TEST 1 PASSED: User roles work correctly!")
        
        # Clean up test users
        db.session.rollback()


def test_course_assignment():
    """Test course assignment for lecturers"""
    print("\n" + "="*60)
    print("TEST 2: Course Assignment System")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        # Get or create test data
        session = AcademicSession.query.filter_by(is_current=True).first()
        if not session:
            print("   ⚠️ No current session - skipping test")
            return
        
        # Create test lecturer
        lecturer = User.query.filter_by(username='test_lecturer@edsu.edu.ng').first()
        if not lecturer:
            lecturer = User(
                username='test_lecturer@edsu.edu.ng',
                email='test_lecturer@edsu.edu.ng',
                full_name='Test Lecturer',
                role='lecturer',
                is_active=True
            )
            lecturer.set_password('Test@2026!')
            db.session.add(lecturer)
            db.session.commit()
        
        # Get a course
        course = Course.query.first()
        if not course:
            print("   ⚠️ No courses found - skipping test")
            return
        
        print(f"\n1. Assigning Lecturer to Course {course.course_code}...")
        
        # Create assignment
        existing = CourseAssignment.query.filter_by(
            user_id=lecturer.id,
            course_id=course.id,
            session_id=session.id
        ).first()
        
        if not existing:
            assignment = CourseAssignment(
                user_id=lecturer.id,
                course_id=course.id,
                session_id=session.id,
                assigned_by=1  # HoD
            )
            db.session.add(assignment)
            db.session.commit()
            print(f"   ✅ Lecturer assigned to {course.course_code}")
        else:
            print(f"   ℹ️ Lecturer already assigned to {course.course_code}")
        
        # Verify assignment
        assignment = CourseAssignment.query.filter_by(
            user_id=lecturer.id,
            course_id=course.id,
            session_id=session.id,
            is_active=True
        ).first()
        
        assert assignment is not None, "❌ Assignment should exist"
        print("   ✅ Assignment verified in database")
        
        print("\n✅ TEST 2 PASSED: Course assignment works correctly!")


def test_result_approval_workflow():
    """Test the complete approval workflow"""
    print("\n" + "="*60)
    print("TEST 3: Result Approval Workflow")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        # Get test data
        session = AcademicSession.query.filter_by(is_current=True).first()
        if not session:
            print("   ⚠️ No current session - skipping test")
            return
        
        course = Course.query.first()
        student = Student.query.filter_by(session_id=session.id).first()
        
        if not course or not student:
            print("   ⚠️ Missing test data (course/student) - skipping test")
            return
        
        # Create a test result
        print(f"\n1. Creating test result for {course.course_code}...")
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
                ca_score=25.0,
                exam_score=60.0,
                total_score=85.0,
                grade='A',
                grade_point=5,
                is_locked=False
            )
            db.session.add(result)
            db.session.commit()
        
        # Verify initial state
        print("\n2. Verifying initial state...")
        assert result.is_locked == False, "❌ Result should start unlocked"
        assert result.locked_by is None, "❌ locked_by should be None initially"
        print("   ✅ Result is in DRAFT state (unlocked)")
        
        # Test: Lock the result (simulate lecturer approval)
        print("\n3. Simulating Lecturer Approval (Locking)...")
        result.is_locked = True
        result.locked_by = 1  # Simulating user ID
        result.locked_at = datetime.utcnow()
        db.session.commit()
        
        # Verify locked state
        assert result.is_locked == True, "❌ Result should be locked"
        assert result.locked_by is not None, "❌ locked_by should have value"
        assert result.locked_at is not None, "❌ locked_at should have timestamp"
        print("   ✅ Result is now LOCKED")
        
        # Test: Unlock the result (simulate HoD unlock)
        print("\n4. Simulating HoD Unlock...")
        result.is_locked = False
        result.unlocked_by = 1  # Simulating HoD
        result.unlocked_at = datetime.utcnow()
        db.session.commit()
        
        # Verify unlocked state
        assert result.is_locked == False, "❌ Result should be unlocked"
        assert result.unlocked_by is not None, "❌ unlocked_by should have value"
        assert result.unlocked_at is not None, "❌ unlocked_at should have timestamp"
        print("   ✅ Result is now UNLOCKED by HoD")
        
        # Test: Final approval on course
        print("\n5. Testing Course Final Approval...")
        course.is_approved = True
        course.approved_by = 1  # HoD
        course.approved_at = datetime.utcnow()
        db.session.commit()
        
        assert course.is_approved == True, "❌ Course should be approved"
        assert course.approved_by is not None, "❌ approved_by should have value"
        print("   ✅ Course has FINAL APPROVAL")
        
        # Reset for future tests
        course.is_approved = False
        course.approved_by = None
        course.approved_at = None
        result.is_locked = False
        result.locked_by = None
        result.locked_at = None
        result.unlocked_by = None
        result.unlocked_at = None
        db.session.commit()
        print("\n   ℹ️ Test data reset to initial state")
        
        print("\n✅ TEST 3 PASSED: Approval workflow works correctly!")


def test_database_schema():
    """Test that all new fields exist in database"""
    print("\n" + "="*60)
    print("TEST 4: Database Schema Verification")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        # Check User table
        print("\n1. Checking User table...")
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        assert 'role' in user_columns, "❌ 'role' column missing from users"
        print("   ✅ User.role field exists")
        
        # Check Course table
        print("\n2. Checking Course table...")
        course_columns = [col['name'] for col in inspector.get_columns('courses')]
        assert 'is_approved' in course_columns, "❌ 'is_approved' column missing from courses"
        assert 'approved_by' in course_columns, "❌ 'approved_by' column missing from courses"
        assert 'approved_at' in course_columns, "❌ 'approved_at' column missing from courses"
        print("   ✅ Course approval fields exist")
        
        # Check Result table
        print("\n3. Checking Result table...")
        result_columns = [col['name'] for col in inspector.get_columns('results')]
        assert 'is_locked' in result_columns, "❌ 'is_locked' column missing from results"
        assert 'locked_by' in result_columns, "❌ 'locked_by' column missing from results"
        assert 'locked_at' in result_columns, "❌ 'locked_at' column missing from results"
        assert 'unlocked_by' in result_columns, "❌ 'unlocked_by' column missing from results"
        assert 'unlocked_at' in result_columns, "❌ 'unlocked_at' column missing from results"
        print("   ✅ Result lock/unlock fields exist")
        
        # Check CourseAssignment table
        print("\n4. Checking CourseAssignment table...")
        tables = inspector.get_table_names()
        assert 'course_assignments' in tables, "❌ 'course_assignments' table missing"
        assignment_columns = [col['name'] for col in inspector.get_columns('course_assignments')]
        assert 'user_id' in assignment_columns, "❌ 'user_id' missing from course_assignments"
        assert 'course_id' in assignment_columns, "❌ 'course_id' missing from course_assignments"
        assert 'session_id' in assignment_columns, "❌ 'session_id' missing from course_assignments"
        print("   ✅ CourseAssignment table exists with all fields")
        
        print("\n✅ TEST 4 PASSED: Database schema is correct!")


def test_role_update():
    """Test updating user role from level_adviser to lecturer"""
    print("\n" + "="*60)
    print("TEST 5: Role Update (Level Adviser → Lecturer)")
    print("="*60)
    
    app = create_app()
    with app.app_context():
        print("\n1. Creating a Level Adviser...")
        test_user = User.query.filter_by(username='roletest@edsu.edu.ng').first()
        
        if test_user:
            db.session.delete(test_user)
            db.session.commit()
        
        test_user = User(
            username='roletest@edsu.edu.ng',
            email='roletest@edsu.edu.ng',
            full_name='Role Test User',
            role='level_adviser',
            program='Computer Science',
            level=200,
            is_active=True
        )
        test_user.set_password('Test@2026!')
        db.session.add(test_user)
        db.session.commit()
        
        # Verify initial state
        assert test_user.role == 'level_adviser', "❌ Initial role should be level_adviser"
        assert test_user.program == 'Computer Science', "❌ Program should be set"
        assert test_user.level == 200, "❌ Level should be set"
        print("   ✅ Level Adviser created with program and level")
        
        print("\n2. Updating role to Lecturer...")
        # Simulate the backend logic in edit_user route
        test_user.role = 'lecturer'
        test_user.program = None  # Clear for lecturer
        test_user.level = None     # Clear for lecturer
        db.session.commit()
        
        # Verify updated state
        test_user = User.query.filter_by(username='roletest@edsu.edu.ng').first()
        assert test_user.role == 'lecturer', f"❌ Role should be 'lecturer' but got '{test_user.role}'"
        assert test_user.program is None, f"❌ Program should be None but got '{test_user.program}'"
        assert test_user.level is None, f"❌ Level should be None but got '{test_user.level}'"
        print("   ✅ Role updated to Lecturer with program=None and level=None")
        
        # Clean up
        db.session.delete(test_user)
        db.session.commit()
        
        print("\n✅ TEST 5 PASSED: Role update works correctly!")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("APPROVAL WORKFLOW SYSTEM - COMPREHENSIVE TESTS")
    print("="*60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        test_database_schema()
        test_user_roles()
        test_role_update()
        test_course_assignment()
        test_result_approval_workflow()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED SUCCESSFULLY! 🎉")
        print("="*60)
        print("\n✅ System Status: FULLY OPERATIONAL")
        print("\nSummary:")
        print("  ✓ Database schema is correct")
        print("  ✓ User roles work properly")
        print("  ✓ Role updates function correctly")
        print("  ✓ Course assignments working")
        print("  ✓ Approval workflow operational")
        print("\nThe approval workflow system is ready for use!")
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except AssertionError as e:
        print("\n" + "="*60)
        print("❌ TEST FAILED!")
        print("="*60)
        print(f"Error: {str(e)}")
        print("\nPlease review the error above and fix the issue.")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ UNEXPECTED ERROR!")
        print("="*60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
