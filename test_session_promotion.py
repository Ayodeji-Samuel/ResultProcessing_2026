#!/usr/bin/env python3
"""
Comprehensive tests for the student session-promotion feature.

Covers:
  - Normal level progression (100→200, 200→300, 300→400)
  - 400L graduation (no outstanding carryovers)
  - 400L non-graduating (outstanding carryovers present)
  - Idempotency (safe to re-run)
  - Academic history snapshot creation
  - Mixed cohort scenarios
  - Non-graduating students appearing on 400L spreadsheets
  - Non-graduating student eventually clears carryovers and graduates

Run:
    .venv\\Scripts\\python.exe -m pytest test_session_promotion.py -v --tb=short 2>&1
"""
import os
import sys
import pytest

# Force SQLite in-memory BEFORE importing anything from the app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db as _db
from app.models import (
    User, AcademicSession, Student, Course, Result, Carryover,
    GradingSystem, StudentAcademicHistory,
)
from app.utils.grading import (
    promote_students_to_new_session,
    get_outstanding_carryovers,
    process_carryovers_for_student,
)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    _app = create_app('default')
    _app.config['TESTING'] = True
    _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    _app.config['WTF_CSRF_ENABLED'] = False
    _app.config['SERVER_NAME'] = 'localhost'
    return _app


@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_session(db, name, is_current=False):
    s = AcademicSession(session_name=name, is_current=is_current)
    db.session.add(s)
    db.session.flush()
    return s


def make_student(db, matric, level, program, session_id, **kwargs):
    s = Student(
        matric_number=matric,
        surname='TEST',
        first_name='STUDENT',
        program=program,
        level=level,
        session_id=session_id,
        **kwargs,
    )
    db.session.add(s)
    db.session.flush()
    return s


def make_course(db, code, level, program, semester=1, credit_unit=3):
    c = Course(
        course_code=code,
        course_title=f'Title of {code}',
        credit_unit=credit_unit,
        semester=semester,
        level=level,
        program=program,
        status='C',
        degree_type='BSc',
        is_active=True,
    )
    db.session.add(c)
    db.session.flush()
    return c


def make_result(db, student, course, session, ca=20, exam=50):
    total = ca + exam
    grade = 'A' if total >= 70 else ('B' if total >= 60 else ('C' if total >= 50 else ('F' if total < 40 else 'D')))
    gp = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'F': 0}.get(grade, 0)
    r = Result(
        student_id=student.id,
        course_id=course.id,
        session_id=session.id,
        ca_score=ca,
        exam_score=exam,
        total_score=total,
        grade=grade,
        grade_point=gp,
    )
    db.session.add(r)
    db.session.flush()
    return r


def make_carryover(db, matric, course, session, level):
    co = Carryover(
        student_matric=matric,
        course_id=course.id,
        original_session_id=session.id,
        original_level=level,
        is_cleared=False,
    )
    db.session.add(co)
    db.session.flush()
    return co


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalLevelProgression:
    """Students below 400L always move up one level."""

    def test_100l_promotes_to_200l(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/21/001', 100, 'Computer Science', s1.id)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/21/001', session_id=s2.id
        ).first()
        assert new_st is not None
        assert new_st.level == 200
        assert new_st.remarks is None
        assert result['promoted'] == 1
        assert result['non_graduating'] == 0
        assert result['graduated'] == []

    def test_200l_promotes_to_300l(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/002', 200, 'Computer Science', s1.id)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/21/002', session_id=s2.id
        ).first()
        assert new_st.level == 300

    def test_300l_promotes_to_400l(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/003', 300, 'Computer Science', s1.id)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/21/003', session_id=s2.id
        ).first()
        assert new_st.level == 400
        assert new_st.remarks is None

    def test_student_name_and_program_copied(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = Student(
            matric_number='FSC/CBS/21/001',
            surname='JOHNSON',
            first_name='Alice',
            other_names='Marie',
            gender='F',
            program='Cyber Security',
            level=100,
            session_id=s1.id,
        )
        db.session.add(st)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(
            matric_number='FSC/CBS/21/001', session_id=s2.id
        ).first()
        assert new_st.surname == 'JOHNSON'
        assert new_st.first_name == 'Alice'
        assert new_st.gender == 'F'
        assert new_st.program == 'Cyber Security'
        assert new_st.level == 200


class TestGraduation:
    """400L students with NO outstanding carryovers should graduate."""

    def test_clean_400l_graduates(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/20/001', 400, 'Computer Science', s1.id)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        # Must NOT appear in new session
        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/20/001', session_id=s2.id
        ).first()
        assert new_st is None, 'Graduated student must not be in the new session'
        assert 'FSC/CSC/20/001' in result['graduated']
        assert result['promoted'] == 0
        assert result['non_graduating'] == 0

    def test_400l_with_cleared_carryovers_graduates(self, db):
        """Cleared carryovers should not block graduation."""
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/20/002', 400, 'Computer Science', s1.id)
        course = make_course(db, 'CSC101', 100, 'Computer Science')

        # Carryover that has been CLEARED
        co = Carryover(
            student_matric='FSC/CSC/20/002',
            course_id=course.id,
            original_session_id=s1.id,
            original_level=100,
            is_cleared=True,   # already cleared
        )
        db.session.add(co)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        # Should graduate
        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/20/002', session_id=s2.id
        ).first()
        assert new_st is None
        assert 'FSC/CSC/20/002' in result['graduated']

    def test_multiple_graduates_reported(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        for i in range(3):
            make_student(db, f'FSC/CSC/20/00{i+1}', 400, 'Computer Science', s1.id)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        assert len(result['graduated']) == 3
        assert Student.query.filter_by(session_id=s2.id).count() == 0


class TestNonGraduating:
    """400L students WITH outstanding carryovers must stay at 400L."""

    def test_400l_with_carryover_stays_non_graduating(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        course = make_course(db, 'CSC202', 200, 'Computer Science')
        st = make_student(db, 'FSC/CSC/20/010', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/20/010', course, s1, 200)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(
            matric_number='FSC/CSC/20/010', session_id=s2.id
        ).first()
        assert new_st is not None, 'Non-graduating student must appear in new session'
        assert new_st.level == 400, 'Level must remain 400'
        assert new_st.remarks == 'Non-Graduating'
        assert new_st.is_non_graduating is True
        assert result['non_graduating'] == 1
        assert 'FSC/CSC/20/010' not in result['graduated']

    def test_non_graduating_properties(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        course = make_course(db, 'CSC303', 300, 'Computer Science')
        make_student(db, 'FSC/CSC/20/011', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/20/011', course, s1, 300)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        ng = Student.query.filter_by(
            matric_number='FSC/CSC/20/011', session_id=s2.id
        ).first()
        assert ng.is_non_graduating is True
        assert ng.is_graduated is False

    def test_multiple_carryovers_all_outstanding_non_graduating(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        c1 = make_course(db, 'CSC101A', 100, 'Computer Science')
        c2 = make_course(db, 'CSC202A', 200, 'Computer Science')
        make_student(db, 'FSC/CSC/20/012', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/20/012', c1, s1, 100)
        make_carryover(db, 'FSC/CSC/20/012', c2, s1, 200)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        assert result['non_graduating'] == 1
        ng = Student.query.filter_by(
            matric_number='FSC/CSC/20/012', session_id=s2.id
        ).first()
        assert ng.level == 400
        assert ng.remarks == 'Non-Graduating'


class TestIdempotency:
    """Running promotion twice must not create duplicate students."""

    def test_double_run_skips_existing(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/020', 100, 'Computer Science', s1.id)
        db.session.commit()

        r1 = promote_students_to_new_session(s1.id, s2.id, db)
        r2 = promote_students_to_new_session(s1.id, s2.id, db)

        # Only 1 student in session s2
        count = Student.query.filter_by(session_id=s2.id).count()
        assert count == 1
        assert r1['promoted'] == 1
        assert r2['skipped'] == 1
        assert r2['promoted'] == 0

    def test_double_run_non_graduating_skips(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        course = make_course(db, 'CSC404', 400, 'Computer Science')
        make_student(db, 'FSC/CSC/20/021', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/20/021', course, s1, 400)
        db.session.commit()

        r1 = promote_students_to_new_session(s1.id, s2.id, db)
        r2 = promote_students_to_new_session(s1.id, s2.id, db)

        count = Student.query.filter_by(session_id=s2.id).count()
        assert count == 1
        assert r1['non_graduating'] == 1
        assert r2['skipped'] == 1


class TestAcademicHistorySnapshot:
    """promote_students_to_new_session should record StudentAcademicHistory."""

    def test_history_snapshot_created(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/21/030', 200, 'Computer Science', s1.id)
        c1 = make_course(db, 'CSC201', 200, 'Computer Science', semester=1, credit_unit=3)
        c2 = make_course(db, 'CSC202B', 200, 'Computer Science', semester=2, credit_unit=3)
        make_result(db, st, c1, s1, ca=25, exam=55)  # total=80 → A
        make_result(db, st, c2, s1, ca=15, exam=35)  # total=50 → C
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        hist = StudentAcademicHistory.query.filter_by(
            student_matric='FSC/CSC/21/030',
            session_id=s1.id,
        ).first()
        assert hist is not None
        assert hist.level == 200
        assert hist.program == 'Computer Science'
        assert hist.total_units_registered == 6   # 3 + 3
        assert hist.cgpa > 0

    def test_history_not_duplicated_on_second_run(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/031', 100, 'Computer Science', s1.id)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)
        promote_students_to_new_session(s1.id, s2.id, db)

        count = StudentAcademicHistory.query.filter_by(
            student_matric='FSC/CSC/21/031',
            session_id=s1.id,
        ).count()
        assert count == 1, 'History must not be duplicated'

    def test_history_good_standing_remark(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/21/032', 100, 'Computer Science', s1.id)
        c = make_course(db, 'CSC101B', 100, 'Computer Science')
        make_result(db, st, c, s1, ca=25, exam=55)  # A → GPA ≥ 1.50
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        hist = StudentAcademicHistory.query.filter_by(
            student_matric='FSC/CSC/21/032', session_id=s1.id
        ).first()
        assert hist.remarks == 'Good Standing'

    def test_history_no_results_remark(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/033', 100, 'Computer Science', s1.id)
        db.session.commit()

        promote_students_to_new_session(s1.id, s2.id, db)

        hist = StudentAcademicHistory.query.filter_by(
            student_matric='FSC/CSC/21/033', session_id=s1.id
        ).first()
        assert hist.remarks == 'No Results'


class TestMixedCohort:
    """Test a realistic cohort of different levels + outcomes."""

    def test_full_cohort_promotion(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')

        course_100 = make_course(db, 'CSC101C', 100, 'Computer Science')

        # 100L → 200L
        make_student(db, 'FSC/CSC/24/001', 100, 'Computer Science', s1.id)
        # 200L → 300L
        make_student(db, 'FSC/CSC/23/001', 200, 'Computer Science', s1.id)
        # 300L → 400L
        make_student(db, 'FSC/CSC/22/001', 300, 'Computer Science', s1.id)
        # 400L clean → graduated
        make_student(db, 'FSC/CSC/21/040', 400, 'Computer Science', s1.id)
        # 400L with carryover → non-graduating
        make_student(db, 'FSC/CSC/21/041', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/21/041', course_100, s1, 100)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        assert result['promoted'] == 3         # 100, 200, 300
        assert result['non_graduating'] == 1   # 400 with carryover
        assert len(result['graduated']) == 1   # 400 clean
        assert result['skipped'] == 0

        # Spot-check levels in new session
        st_100 = Student.query.filter_by(matric_number='FSC/CSC/24/001', session_id=s2.id).first()
        assert st_100.level == 200

        st_400_ng = Student.query.filter_by(matric_number='FSC/CSC/21/041', session_id=s2.id).first()
        assert st_400_ng.level == 400
        assert st_400_ng.remarks == 'Non-Graduating'

        graduated_in_s2 = Student.query.filter_by(matric_number='FSC/CSC/21/040', session_id=s2.id).first()
        assert graduated_in_s2 is None


class TestNonGraduatingLifecycle:
    """Test the full lifecycle of a non-graduating student who eventually clears carryovers."""

    def test_non_graduating_clears_carryovers_and_graduates_next_session(self, db):
        """
        Lifecycle:
          Session 1: Student is 400L with carryover → non-graduating into Session 2
          Session 2: Student clears the carryover (passes the course)
          Session 3: Now no outstanding carryovers → should graduate
        """
        s1 = make_session(db, '2023/2024')
        s2 = make_session(db, '2024/2025')
        s3 = make_session(db, '2025/2026')

        course = make_course(db, 'CSC202C', 200, 'Computer Science')

        # Session 1: student at 400L, fails a carryover course
        st1 = make_student(db, 'FSC/CSC/20/099', 400, 'Computer Science', s1.id)
        co = make_carryover(db, 'FSC/CSC/20/099', course, s1, 400)
        db.session.commit()

        # Promote S1 → S2
        r1 = promote_students_to_new_session(s1.id, s2.id, db)
        assert r1['non_graduating'] == 1

        st2 = Student.query.filter_by(matric_number='FSC/CSC/20/099', session_id=s2.id).first()
        assert st2 is not None
        assert st2.level == 400
        assert st2.remarks == 'Non-Graduating'

        # In Session 2: student retakes and passes the carryover course
        pass_result = make_result(db, st2, course, s2, ca=25, exam=55)  # A
        # Clear the carryover
        co.is_cleared = True
        co.cleared_session_id = s2.id
        co.cleared_result_id = pass_result.id
        db.session.commit()

        # Promote S2 → S3: now no outstanding carryovers, should graduate
        r2 = promote_students_to_new_session(s2.id, s3.id, db)
        assert 'FSC/CSC/20/099' in r2['graduated'], \
            'After clearing all carryovers, student should graduate'
        assert r2['non_graduating'] == 0

        # Must NOT appear in session 3
        st3 = Student.query.filter_by(matric_number='FSC/CSC/20/099', session_id=s3.id).first()
        assert st3 is None

    def test_non_graduating_persists_if_carryover_not_cleared(self, db):
        """If carryover is NOT cleared, student remains non-graduating every session."""
        s1 = make_session(db, '2023/2024')
        s2 = make_session(db, '2024/2025')
        s3 = make_session(db, '2025/2026')

        course = make_course(db, 'CSC303B', 300, 'Computer Science')
        make_student(db, 'FSC/CSC/20/100', 400, 'Computer Science', s1.id)
        make_carryover(db, 'FSC/CSC/20/100', course, s1, 300)
        db.session.commit()

        # S1 → S2: non-graduating
        r1 = promote_students_to_new_session(s1.id, s2.id, db)
        assert r1['non_graduating'] == 1

        # S2 → S3: still non-graduating (carryover still uncleared)
        r2 = promote_students_to_new_session(s2.id, s3.id, db)
        assert r2['non_graduating'] == 1

        # Appears in both S2 and S3 as non-graduating
        st_s3 = Student.query.filter_by(matric_number='FSC/CSC/20/100', session_id=s3.id).first()
        assert st_s3.level == 400
        assert st_s3.remarks == 'Non-Graduating'


class TestStudentModelProperties:
    """Test the Student model helper properties."""

    def test_is_non_graduating_true(self, db):
        s = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/20/200', 400, 'Computer Science', s.id, remarks='Non-Graduating')
        db.session.commit()
        assert st.is_non_graduating is True
        assert st.is_graduated is False

    def test_is_non_graduating_false_for_normal(self, db):
        s = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/20/201', 200, 'Computer Science', s.id)
        db.session.commit()
        assert st.is_non_graduating is False
        assert st.is_graduated is False

    def test_is_graduated_true(self, db):
        s = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/20/202', 400, 'Computer Science', s.id, remarks='Graduated')
        db.session.commit()
        assert st.is_graduated is True
        assert st.is_non_graduating is False

    def test_remarks_none_for_regular_student(self, db):
        s = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/20/203', 100, 'Computer Science', s.id)
        db.session.commit()
        assert st.remarks is None


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_no_students_returns_zero_counts(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        assert result['promoted'] == 0
        assert result['non_graduating'] == 0
        assert result['graduated'] == []
        assert result['skipped'] == 0

    def test_inactive_students_are_not_promoted(self, db):
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        st = make_student(db, 'FSC/CSC/21/099', 100, 'Computer Science', s1.id)
        st.is_active = False
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        new_st = Student.query.filter_by(session_id=s2.id).first()
        assert new_st is None
        assert result['promoted'] == 0

    def test_same_session_raises_no_error_but_returns_zero(self, db):
        """Promoting from/to same session: all students are 'skipped'."""
        s1 = make_session(db, '2024/2025')
        make_student(db, 'FSC/CSC/21/098', 100, 'Computer Science', s1.id)
        db.session.commit()

        # Pre-insert the student in the SAME session (simulating "already there")
        # Since make_student already did that, trying to promote s1→s1 should skip
        result = promote_students_to_new_session(s1.id, s1.id, db)
        # The student is in s1, so promoting s1→s1 finds them already there → skipped
        assert result['skipped'] == 1
        assert result['promoted'] == 0

    def test_multiple_programs_promoted_independently(self, db):
        """Students from different programmes are all promoted."""
        s1 = make_session(db, '2024/2025')
        s2 = make_session(db, '2025/2026')
        make_student(db, 'FSC/CSC/21/080', 100, 'Computer Science', s1.id)
        make_student(db, 'FSC/CBS/21/080', 100, 'Cyber Security', s1.id)
        make_student(db, 'FSC/SWE/21/080', 100, 'Software Engineering', s1.id)
        db.session.commit()

        result = promote_students_to_new_session(s1.id, s2.id, db)

        assert result['promoted'] == 3
        for matric in ['FSC/CSC/21/080', 'FSC/CBS/21/080', 'FSC/SWE/21/080']:
            st = Student.query.filter_by(matric_number=matric, session_id=s2.id).first()
            assert st.level == 200
