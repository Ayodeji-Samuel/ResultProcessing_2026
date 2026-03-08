#!/usr/bin/env python3
"""
Comprehensive tests for NR (Not Registered) grades, carryover detection,
and past-carryover scanning.

Run with:
    .venv\Scripts\python.exe -m pytest test_nr_carryover.py -v --tb=short 2>&1
"""
import os
import sys
import pytest

# Force SQLite for tests BEFORE anything imports the config
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db as _db
from app.models import (
    User, AcademicSession, Student, Course, Result, Carryover,
    GradingSystem, SystemSetting
)
from app.utils.grading import (
    get_grade_info, format_score_grade, calculate_gpa,
    get_credit_units_summary, process_carryovers_for_student,
    check_and_clear_carryovers, get_carryover_students_for_level,
    get_required_courses_for_level_program, scan_and_create_past_carryovers,
    get_outstanding_carryovers,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Create a test Flask application."""
    _app = create_app('default')
    _app.config['TESTING'] = True
    _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    _app.config['WTF_CSRF_ENABLED'] = False
    _app.config['SERVER_NAME'] = 'localhost'
    return _app


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def session(db):
    """Create a current academic session."""
    s = AcademicSession(session_name='2025/2026', is_current=True)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def prev_session(db):
    """Create a previous academic session."""
    s = AcademicSession(session_name='2024/2025', is_current=False)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def courses_100l(db, session):
    """Create 100L Computer Science courses."""
    courses = []
    course_data = [
        ('CSC101', 'Introduction to Computer Science', 3, 1, 'C'),
        ('CSC102', 'Introduction to Programming', 3, 1, 'C'),
        ('MTH101', 'General Mathematics I', 3, 1, 'C'),
        ('CSC111', 'Computer Programming II', 3, 2, 'C'),
        ('CSC112', 'Data Structures', 3, 2, 'C'),
    ]
    for code, title, cu, sem, status in course_data:
        c = Course(
            course_code=code, course_title=title, credit_unit=cu,
            semester=sem, level=100, program='Computer Science',
            status=status, degree_type='BSc', is_active=True
        )
        db.session.add(c)
        courses.append(c)
    db.session.commit()
    return courses


@pytest.fixture
def courses_200l(db, session):
    """Create 200L Computer Science courses."""
    courses = []
    course_data = [
        ('CSC201', 'Computer Architecture', 3, 1, 'C'),
        ('CSC202', 'Operating Systems', 3, 1, 'C'),
    ]
    for code, title, cu, sem, status in course_data:
        c = Course(
            course_code=code, course_title=title, credit_unit=cu,
            semester=sem, level=200, program='Computer Science',
            status=status, degree_type='BSc', is_active=True
        )
        db.session.add(c)
        courses.append(c)
    db.session.commit()
    return courses


@pytest.fixture
def courses_cyber_100l(db, session):
    """Create 100L Cybersecurity courses."""
    courses = []
    course_data = [
        ('CBS101', 'Intro to Cybersecurity', 3, 1, 'C'),
        ('CBS102', 'Network Fundamentals', 3, 1, 'C'),
    ]
    for code, title, cu, sem, status in course_data:
        c = Course(
            course_code=code, course_title=title, credit_unit=cu,
            semester=sem, level=100, program='Cyber Security',
            status=status, degree_type='BSc', is_active=True
        )
        db.session.add(c)
        courses.append(c)
    db.session.commit()
    return courses


def _make_student(db, matric, surname, first_name, level, program, session):
    """Helper to create a student."""
    s = Student(
        matric_number=matric, surname=surname, first_name=first_name,
        gender='M', program=program, level=level, session_id=session.id
    )
    db.session.add(s)
    db.session.commit()
    return s


def _make_result(db, student, course, session, ca, exam):
    """Helper to create a result with grade calculation."""
    total = ca + exam
    grade, gp = get_grade_info(total)
    r = Result(
        student_id=student.id, course_id=course.id,
        session_id=session.id, ca_score=ca, exam_score=exam,
        total_score=total, grade=grade, grade_point=gp,
        is_carryover=student.level > course.level
    )
    db.session.add(r)
    db.session.commit()
    return r


# ──────────────────────────────────────────────────────────────────────────────
# Tests: NR Grade Display
# ──────────────────────────────────────────────────────────────────────────────

class TestNRGradeDisplay:
    """Tests that courses without results show 'NR' instead of '-' or '0F'."""

    def test_nr_for_unregistered_course_in_spreadsheet_data(
        self, app, db, session, courses_100l
    ):
        """When a student has no result for a course, NR should appear."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0001', 'DOE', 'John', 100,
                'Computer Science', session
            )
            # Only create result for the first course
            _make_result(db, student, courses_100l[0], session, 20, 50)

            # Simulate what reports.py does
            first_sem_courses = [c for c in courses_100l if c.semester == 1]
            student_row = {'first_semester': {}}

            for course in first_sem_courses:
                result = Result.query.filter_by(
                    student_id=student.id,
                    course_id=course.id,
                    session_id=session.id
                ).first()
                if result:
                    student_row['first_semester'][course.course_code] = \
                        format_score_grade(result.total_score, result.grade)
                else:
                    student_row['first_semester'][course.course_code] = 'NR'

            # CSC101 should have a score
            assert student_row['first_semester']['CSC101'] == '70A'
            # CSC102 and MTH101 should be NR
            assert student_row['first_semester']['CSC102'] == 'NR'
            assert student_row['first_semester']['MTH101'] == 'NR'

    def test_nr_does_not_affect_gpa(self, app, db, session, courses_100l):
        """NR courses should NOT affect GPA calculations."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0002', 'SMITH', 'Jane', 100,
                'Computer Science', session
            )
            # Only register 1 course with A grade (70)
            r = _make_result(db, student, courses_100l[0], session, 20, 50)

            results = [r]
            gpa = calculate_gpa(results)
            summary = get_credit_units_summary(results)

            assert gpa == 5.0  # Only the A-grade course
            assert summary['total'] == 3  # Only 1 course x 3 CU
            assert summary['passed'] == 3
            assert summary['failed'] == 0


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Carryover Student Detection
# ──────────────────────────────────────────────────────────────────────────────

class TestCarryoverStudentDetection:
    """Tests for detecting higher-level students taking lower-level courses."""

    def test_detect_carryover_students_for_level(
        self, app, db, session, courses_100l
    ):
        """A 400L student with results for a 100L course should be detected."""
        with app.app_context():
            # Regular 100L student
            s100 = _make_student(
                db, 'FSC/CSC/0010', 'ALPHA', 'First', 100,
                'Computer Science', session
            )
            # 400L student taking a 100L course as carryover
            s400 = _make_student(
                db, 'FSC/CSC/0011', 'BETA', 'Fourth', 400,
                'Computer Science', session
            )
            _make_result(db, s100, courses_100l[0], session, 15, 45)
            _make_result(db, s400, courses_100l[0], session, 10, 35)

            carryover = get_carryover_students_for_level(
                100, 'Computer Science', session.id
            )
            matrics = [s.matric_number for s in carryover]

            assert 'FSC/CSC/0011' in matrics  # 400L student detected
            assert 'FSC/CSC/0010' not in matrics  # 100L student NOT in carryover list

    def test_no_false_positives_different_program(
        self, app, db, session, courses_100l, courses_cyber_100l
    ):
        """A 400L Cybersecurity student should NOT appear on CS 100L carryover."""
        with app.app_context():
            s_cyber_400 = _make_student(
                db, 'FSC/CBS/0001', 'GAMMA', 'Cyber', 400,
                'Cyber Security', session
            )
            # Give this student a result for a CYBERSECURITY 100L course
            _make_result(db, s_cyber_400, courses_cyber_100l[0], session, 15, 30)

            carryover = get_carryover_students_for_level(
                100, 'Computer Science', session.id
            )
            matrics = [s.matric_number for s in carryover]

            assert 'FSC/CBS/0001' not in matrics  # Different program

    def test_carryover_students_included_in_spreadsheet_combined(
        self, app, db, session, courses_100l
    ):
        """Combined student list should have both regular + carryover, no dupes."""
        with app.app_context():
            s100_a = _make_student(
                db, 'FSC/CSC/0020', 'REG', 'One', 100,
                'Computer Science', session
            )
            s100_b = _make_student(
                db, 'FSC/CSC/0021', 'REG', 'Two', 100,
                'Computer Science', session
            )
            s300 = _make_student(
                db, 'FSC/CSC/0022', 'CARRY', 'Three', 300,
                'Computer Science', session
            )
            # Give 300L student a result for a 100L course
            _make_result(db, s300, courses_100l[0], session, 10, 30)

            regular = Student.query.filter_by(
                level=100, program='Computer Science',
                session_id=session.id
            ).order_by(Student.matric_number).all()

            carryover = get_carryover_students_for_level(
                100, 'Computer Science', session.id
            )

            regular_ids = {s.id for s in regular}
            unique_carryover = [s for s in carryover if s.id not in regular_ids]
            combined = regular + unique_carryover

            matrics = [s.matric_number for s in combined]
            assert len(matrics) == 3
            assert 'FSC/CSC/0020' in matrics
            assert 'FSC/CSC/0021' in matrics
            assert 'FSC/CSC/0022' in matrics
            # Check no duplicates
            assert len(matrics) == len(set(matrics))


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Past Carryover Scanning
# ──────────────────────────────────────────────────────────────────────────────

class TestPastCarryoverScanning:
    """Tests for scan_and_create_past_carryovers functionality."""

    def test_creates_carryover_from_failed_result(
        self, app, db, session, courses_100l
    ):
        """Failed results should generate carryover records."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0030', 'FAIL', 'Student', 100,
                'Computer Science', session
            )
            # Create a failing result (score < 40 = F)
            _make_result(db, student, courses_100l[0], session, 5, 10)

            # Verify grade is F
            r = Result.query.filter_by(student_id=student.id).first()
            assert r.grade == 'F'

            # Run scanner
            result = scan_and_create_past_carryovers(session.id)
            assert result['created_from_failures'] >= 1

            # Verify carryover was created
            co = Carryover.query.filter_by(
                student_matric='FSC/CSC/0030',
                course_id=courses_100l[0].id
            ).first()
            assert co is not None
            assert co.is_cleared is False

    def test_no_duplicate_carryovers(
        self, app, db, session, courses_100l
    ):
        """Running the scanner twice should not create duplicates."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0031', 'DUP', 'Test', 100,
                'Computer Science', session
            )
            _make_result(db, student, courses_100l[0], session, 5, 10)

            scan_and_create_past_carryovers(session.id)
            scan_and_create_past_carryovers(session.id)

            count = Carryover.query.filter_by(
                student_matric='FSC/CSC/0031',
                course_id=courses_100l[0].id,
                original_session_id=session.id
            ).count()
            assert count == 1  # Only ONE carryover entry

    def test_auto_clears_carryover_when_passed_later(
        self, app, db, session, prev_session, courses_100l
    ):
        """If a student passed the course in a later session, carryover should
        be automatically cleared by the scanner."""
        with app.app_context():
            # Student failed in previous session
            student_prev = _make_student(
                db, 'FSC/CSC/0032', 'CLEAR', 'Me', 100,
                'Computer Science', prev_session
            )
            _make_result(db, student_prev, courses_100l[0], prev_session, 5, 10)

            # Student passed in current session (now at 200L)
            student_curr = _make_student(
                db, 'FSC/CSC/0032', 'CLEAR', 'Me', 200,
                'Computer Science', session
            )
            _make_result(db, student_curr, courses_100l[0], session, 20, 55)

            result = scan_and_create_past_carryovers()

            co = Carryover.query.filter_by(
                student_matric='FSC/CSC/0032',
                course_id=courses_100l[0].id
            ).first()
            assert co is not None
            assert co.is_cleared is True
            assert co.cleared_session_id == session.id

    def test_flags_higher_level_student_result_as_carryover(
        self, app, db, session, courses_100l
    ):
        """A 300L student with a 100L result should have it flagged as carryover."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0033', 'FLAG', 'This', 300,
                'Computer Science', session
            )
            r = _make_result(db, student, courses_100l[0], session, 20, 50)
            # Reset the flag to test scanner
            r.is_carryover = False
            db.session.commit()

            result = scan_and_create_past_carryovers(session.id)
            assert result['flagged_carryover_results'] >= 1

            r_updated = Result.query.get(r.id)
            assert r_updated.is_carryover is True


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Required Courses per Level/Programme
# ──────────────────────────────────────────────────────────────────────────────

class TestRequiredCourses:
    """Tests for get_required_courses_for_level_program."""

    def test_returns_all_courses_for_level_program(
        self, app, db, session, courses_100l, courses_200l
    ):
        with app.app_context():
            courses = get_required_courses_for_level_program(100, 'Computer Science')
            codes = {c.course_code for c in courses}
            assert 'CSC101' in codes
            assert 'CSC102' in codes
            assert 'MTH101' in codes
            assert 'CSC111' in codes
            assert 'CSC112' in codes
            # 200L courses should NOT appear
            assert 'CSC201' not in codes

    def test_filter_by_semester(self, app, db, session, courses_100l):
        with app.app_context():
            first_sem = get_required_courses_for_level_program(
                100, 'Computer Science', semester=1
            )
            codes = {c.course_code for c in first_sem}
            assert 'CSC101' in codes
            assert 'CSC111' not in codes  # semester 2

    def test_different_programs_separate(
        self, app, db, session, courses_100l, courses_cyber_100l
    ):
        """Courses for different programs are separate."""
        with app.app_context():
            cs_courses = get_required_courses_for_level_program(
                100, 'Computer Science'
            )
            cb_courses = get_required_courses_for_level_program(
                100, 'Cyber Security'
            )
            cs_codes = {c.course_code for c in cs_courses}
            cb_codes = {c.course_code for c in cb_courses}
            assert 'CSC101' in cs_codes
            assert 'CBS101' in cb_codes
            assert 'CBS101' not in cs_codes
            assert 'CSC101' not in cb_codes


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Student Upload Lookup (Carryover Fix)
# ──────────────────────────────────────────────────────────────────────────────

class TestUploadStudentLookup:
    """Tests that result upload finds carryover students at higher levels."""

    def test_find_higher_level_student_for_lower_course(
        self, app, db, session, courses_100l
    ):
        """A 400L student should be found when uploading results for a 100L course."""
        with app.app_context():
            s400 = _make_student(
                db, 'FSC/CSC/0040', 'LOOKUP', 'Test', 400,
                'Computer Science', session
            )
            course = courses_100l[0]  # 100L course

            # Exact match (level+program) — should NOT find
            exact = Student.query.filter_by(
                matric_number='FSC/CSC/0040',
                session_id=session.id,
                level=course.level,
                program=course.program
            ).first()
            assert exact is None

            # Relaxed match — should find
            relaxed = Student.query.filter_by(
                matric_number='FSC/CSC/0040',
                session_id=session.id
            ).filter(Student.level > course.level).first()
            assert relaxed is not None
            assert relaxed.id == s400.id

    def test_prefers_exact_level_match(
        self, app, db, session, courses_100l
    ):
        """If a student exists at the exact level, prefer that over a higher-level match."""
        with app.app_context():
            s100 = _make_student(
                db, 'FSC/CSC/0041', 'PREFER', 'Exact', 100,
                'Computer Science', session
            )
            course = courses_100l[0]

            exact = Student.query.filter_by(
                matric_number='FSC/CSC/0041',
                session_id=session.id,
                level=course.level,
                program=course.program
            ).first()
            assert exact is not None
            assert exact.id == s100.id


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Carryover Tracking Integration
# ──────────────────────────────────────────────────────────────────────────────

class TestCarryoverTrackingIntegration:
    """End-to-end tests for the carryover tracking lifecycle."""

    def test_full_carryover_lifecycle(
        self, app, db, session, prev_session, courses_100l
    ):
        """Test: fail → carryover created → pass → carryover cleared."""
        with app.app_context():
            course = courses_100l[0]

            # Session 1: Student fails at 100L
            s1 = _make_student(
                db, 'FSC/CSC/0050', 'LIFE', 'Cycle', 100,
                'Computer Science', prev_session
            )
            _make_result(db, s1, course, prev_session, 5, 10)
            process_carryovers_for_student('FSC/CSC/0050', prev_session.id, _db)

            # Verify carryover exists
            co = Carryover.query.filter_by(
                student_matric='FSC/CSC/0050',
                course_id=course.id
            ).first()
            assert co is not None
            assert co.is_cleared is False

            # Session 2: Student now at 200L, retakes the course and passes
            s2 = _make_student(
                db, 'FSC/CSC/0050', 'LIFE', 'Cycle', 200,
                'Computer Science', session
            )
            r = _make_result(db, s2, course, session, 20, 50)
            check_and_clear_carryovers(
                'FSC/CSC/0050', course.id, session.id, r.id, _db
            )

            # Verify carryover is cleared
            db.session.expire_all()  # Refresh from DB
            co_updated = Carryover.query.filter_by(
                student_matric='FSC/CSC/0050',
                course_id=course.id
            ).first()
            assert co_updated.is_cleared is True

    def test_outstanding_carryovers(
        self, app, db, session, courses_100l
    ):
        """get_outstanding_carryovers returns only uncleared items."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0051', 'OUT', 'Standing', 100,
                'Computer Science', session
            )
            # Fail two courses
            _make_result(db, student, courses_100l[0], session, 5, 10)
            _make_result(db, student, courses_100l[1], session, 5, 5)
            process_carryovers_for_student('FSC/CSC/0051', session.id, _db)

            outstanding = get_outstanding_carryovers('FSC/CSC/0051')
            assert len(outstanding) == 2

            # Clear one
            outstanding[0].is_cleared = True
            db.session.commit()

            outstanding2 = get_outstanding_carryovers('FSC/CSC/0051')
            assert len(outstanding2) == 1


# ──────────────────────────────────────────────────────────────────────────────
# Tests: Edge Cases
# ──────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_no_students_at_level_no_carryovers(
        self, app, db, session, courses_100l
    ):
        """No students and no carryovers → empty list."""
        with app.app_context():
            carryover = get_carryover_students_for_level(
                100, 'Computer Science', session.id
            )
            assert carryover == []

    def test_student_with_all_results_has_no_nr(
        self, app, db, session, courses_100l
    ):
        """A student with all results should have no NR entries."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0060', 'ALL', 'Results', 100,
                'Computer Science', session
            )
            first_sem = [c for c in courses_100l if c.semester == 1]
            for course in first_sem:
                _make_result(db, student, course, session, 20, 50)

            row = {}
            for course in first_sem:
                result = Result.query.filter_by(
                    student_id=student.id, course_id=course.id,
                    session_id=session.id
                ).first()
                row[course.course_code] = (
                    format_score_grade(result.total_score, result.grade)
                    if result else 'NR'
                )

            for code, val in row.items():
                assert val != 'NR', f"{code} should not be NR"

    def test_carryover_student_nr_for_unregistered_courses(
        self, app, db, session, courses_100l
    ):
        """A 300L carryover student taking only 1 out of 3 first-sem courses
        should have NR for the other 2."""
        with app.app_context():
            s300 = _make_student(
                db, 'FSC/CSC/0061', 'PARTIAL', 'CO', 300,
                'Computer Science', session
            )
            first_sem = [c for c in courses_100l if c.semester == 1]
            # Only take the first course
            _make_result(db, s300, first_sem[0], session, 15, 40)

            row = {}
            for course in first_sem:
                result = Result.query.filter_by(
                    student_id=s300.id, course_id=course.id,
                    session_id=session.id
                ).first()
                row[course.course_code] = (
                    format_score_grade(result.total_score, result.grade)
                    if result else 'NR'
                )

            assert row['CSC101'] != 'NR'  # Has result
            assert row['CSC102'] == 'NR'  # Not registered
            assert row['MTH101'] == 'NR'  # Not registered

    def test_scan_carryovers_all_sessions(
        self, app, db, session, prev_session, courses_100l
    ):
        """Scanner covers all sessions when no session_id is given."""
        with app.app_context():
            # Fail in prev session
            s1 = _make_student(
                db, 'FSC/CSC/0062', 'ALLSESS', 'Scan', 100,
                'Computer Science', prev_session
            )
            _make_result(db, s1, courses_100l[0], prev_session, 0, 10)

            # Fail in current session
            s2 = _make_student(
                db, 'FSC/CSC/0063', 'ALLSESS', 'Scan2', 100,
                'Computer Science', session
            )
            _make_result(db, s2, courses_100l[1], session, 5, 5)

            result = scan_and_create_past_carryovers()  # No session filter
            assert result['created_from_failures'] >= 2

    def test_process_carryovers_no_duplicates(
        self, app, db, session, courses_100l
    ):
        """process_carryovers_for_student must not create duplicate entries."""
        with app.app_context():
            student = _make_student(
                db, 'FSC/CSC/0064', 'NODUP', 'Test', 100,
                'Computer Science', session
            )
            _make_result(db, student, courses_100l[0], session, 5, 10)

            process_carryovers_for_student('FSC/CSC/0064', session.id, _db)
            process_carryovers_for_student('FSC/CSC/0064', session.id, _db)
            process_carryovers_for_student('FSC/CSC/0064', session.id, _db)

            count = Carryover.query.filter_by(
                student_matric='FSC/CSC/0064',
                course_id=courses_100l[0].id,
                original_session_id=session.id
            ).count()
            assert count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
