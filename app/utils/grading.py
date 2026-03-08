"""Grading utility functions"""
from app.models import GradingSystem
from flask_login import current_user


def get_accessible_filters():
    """
    Get filters based on user access level.

    Returns:
        tuple: (level_access, program_access)
            - None, None for HoD / Admin (no restrictions)
            - level, [programs] for Level Adviser (one or more programs)
            - None, None for Lecturer (access via course assignments)
    """
    if current_user.role == 'hod':
        return None, None
    if current_user.role == 'level_adviser':
        programs = current_user.get_adviser_programs()  # always a list
        level = current_user.get_adviser_level()
        return level, (programs if programs else None)
    # Lecturer (or any other role) – no blanket level/program restriction
    return None, None


def get_grade_info(score, degree_type='BSc'):
    """
    Get grade and grade point for a given score and degree type.
    
    Args:
        score: The total score (0-100)
        degree_type: The degree type (BSc, PGD, MSc, PhD)
    
    Returns:
        tuple: (grade, grade_point) e.g., ('A', 5)
    """
    grading = GradingSystem.query.filter_by(degree_type=degree_type).all()
    
    # If no custom grading exists, use default
    if not grading:
        if score >= 70:
            return ('A', 5)
        elif score >= 60:
            return ('B', 4)
        elif score >= 50:
            return ('C', 3)
        elif score >= 45:
            return ('D', 2)
        elif score >= 40:
            return ('E', 1)
        else:
            return ('F', 0)
    
    # Use custom grading from database
    for grade in grading:
        if grade.min_score <= score <= grade.max_score:
            return (grade.grade, grade.grade_point)
    
    # Default fallback
    return ('F', 0)


def calculate_gpa(results):
    """
    Calculate GPA from a list of results.
    
    Args:
        results: List of Result objects with grade_point and course.credit_unit
    
    Returns:
        float: The calculated GPA (0.00 - 5.00)
    """
    if not results:
        return 0.0
    
    total_quality_points = 0
    total_credit_units = 0
    
    for result in results:
        credit_unit = result.course.credit_unit
        grade_point = result.grade_point
        
        total_quality_points += grade_point * credit_unit
        total_credit_units += credit_unit
    
    if total_credit_units == 0:
        return 0.0
    
    gpa = total_quality_points / total_credit_units
    return round(gpa, 2)


def calculate_cgpa(all_results):
    """
    Calculate Cumulative GPA from all results across semesters.
    
    Args:
        all_results: List of all Result objects
    
    Returns:
        float: The calculated CGPA (0.00 - 5.00)
    """
    return calculate_gpa(all_results)


def get_credit_units_summary(results):
    """
    Get summary of credit units passed and failed.
    
    Args:
        results: List of Result objects
    
    Returns:
        dict: {
            'passed': total credit units passed,
            'failed': total credit units failed,
            'total': total credit units
        }
    """
    passed = 0
    failed = 0
    
    for result in results:
        credit_unit = result.course.credit_unit
        # F grade (0 points) is considered failed
        if result.grade_point > 0:
            passed += credit_unit
        else:
            failed += credit_unit
    
    return {
        'passed': passed,
        'failed': failed,
        'total': passed + failed
    }


def get_class_of_degree(cgpa):
    """
    Get the class of degree based on CGPA.
    
    Args:
        cgpa: The cumulative GPA
    
    Returns:
        str: The class of degree
    """
    if cgpa >= 4.50:
        return 'First Class Honours'
    elif cgpa >= 3.50:
        return 'Second Class Honours (Upper Division)'
    elif cgpa >= 2.40:
        return 'Second Class Honours (Lower Division)'
    elif cgpa >= 1.50:
        return 'Third Class Honours'
    elif cgpa >= 1.00:
        return 'Pass'
    else:
        return 'Fail'


def format_score_grade(total_score, grade):
    """
    Format the score and grade for display in spreadsheet.
    
    Args:
        total_score: The total score
        grade: The grade letter
    
    Returns:
        str: Formatted string like "70A"
    """
    return f"{int(total_score)}{grade}"


def is_pass_grade(grade):
    """
    Check if a grade is a passing grade.
    
    Args:
        grade: The grade letter (A, B, C, D, E, F)
    
    Returns:
        bool: True if passing grade, False otherwise
    """
    return grade != 'F'


def validate_scores(ca_score, exam_score):
    """
    Validate CA and Exam scores.
    
    Args:
        ca_score: Continuous Assessment score (0-30)
        exam_score: Exam score (0-70)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    errors = []
    
    try:
        ca = float(ca_score)
        if ca < 0 or ca > 30:
            errors.append('CA score must be between 0 and 30')
    except (ValueError, TypeError):
        errors.append('CA score must be a number')
    
    try:
        exam = float(exam_score)
        if exam < 0 or exam > 70:
            errors.append('Exam score must be between 0 and 70')
    except (ValueError, TypeError):
        errors.append('Exam score must be a number')
    
    if errors:
        return (False, '; '.join(errors))
    
    return (True, None)


def process_carryovers_for_student(student_matric, session_id, db):
    """
    Process failed courses and create carryover records for a student.
    Called after results are uploaded.
    
    Args:
        student_matric: The student's matric number
        session_id: The current session ID
        db: Database session
    """
    from app.models import Student, Result, Carryover, Course
    
    # Get all students with this matric number in the given session
    students = Student.query.filter_by(matric_number=student_matric, session_id=session_id).all()
    
    for student in students:
        # Get all failed results for this student in this session
        failed_results = Result.query.filter_by(
            student_id=student.id,
            session_id=session_id
        ).filter(Result.grade == 'F').all()
        
        for result in failed_results:
            # Check if carryover already exists
            existing = Carryover.query.filter_by(
                student_matric=student_matric,
                course_id=result.course_id,
                original_session_id=session_id
            ).first()
            
            if not existing:
                # Create new carryover record
                carryover = Carryover(
                    student_matric=student_matric,
                    course_id=result.course_id,
                    original_session_id=session_id,
                    original_level=student.level,
                    is_cleared=False
                )
                db.session.add(carryover)
    
    db.session.commit()


def check_and_clear_carryovers(student_matric, course_id, session_id, result_id, db):
    """
    Check if a newly uploaded result clears any carryover.
    
    Args:
        student_matric: The student's matric number
        course_id: The course ID
        session_id: The session when the result was uploaded
        result_id: The result ID that might clear the carryover
        db: Database session
    """
    from app.models import Carryover, Result
    
    # Get the result
    result = Result.query.get(result_id)
    if not result or result.grade == 'F':
        return  # No clearing if failed again
    
    # Find any uncleared carryover for this course
    carryover = Carryover.query.filter_by(
        student_matric=student_matric,
        course_id=course_id,
        is_cleared=False
    ).first()
    
    if carryover:
        # Clear the carryover
        carryover.is_cleared = True
        carryover.cleared_session_id = session_id
        carryover.cleared_result_id = result_id
        db.session.commit()


def get_outstanding_carryovers(student_matric):
    """
    Get all outstanding (uncleared) carryovers for a student.
    
    Args:
        student_matric: The student's matric number
    
    Returns:
        list: List of Carryover objects
    """
    from app.models import Carryover
    
    return Carryover.query.filter_by(
        student_matric=student_matric,
        is_cleared=False
    ).all()


def validate_carryover_registration(student_matric, registered_course_ids):
    """
    Validate that a student has registered all their outstanding carryover courses.
    
    Args:
        student_matric: The student's matric number
        registered_course_ids: List of course IDs the student is registered for
    
    Returns:
        tuple: (is_valid, missing_carryovers)
            - is_valid: True if all carryovers are registered
            - missing_carryovers: List of unregistered carryover courses
    """
    from app.models import Carryover
    
    outstanding = Carryover.query.filter_by(
        student_matric=student_matric,
        is_cleared=False
    ).all()
    
    missing = []
    for carryover in outstanding:
        if carryover.course_id not in registered_course_ids:
            missing.append(carryover)
    
    return (len(missing) == 0, missing)


def check_carryover_has_score(student_matric, session_id):
    """
    Check if all carryover courses have been taken (have scores) in the current session.
    
    Args:
        student_matric: The student's matric number
        session_id: The current session ID
    
    Returns:
        tuple: (all_taken, untaken_carryovers)
            - all_taken: True if all carryovers have scores
            - untaken_carryovers: List of carryovers without scores
    """
    from app.models import Carryover, Student, Result
    
    # Get outstanding carryovers
    outstanding = Carryover.query.filter_by(
        student_matric=student_matric,
        is_cleared=False
    ).all()
    
    if not outstanding:
        return (True, [])
    
    # Get the student in current session
    student = Student.query.filter_by(
        matric_number=student_matric,
        session_id=session_id
    ).first()
    
    if not student:
        return (False, outstanding)  # Student not registered in current session
    
    untaken = []
    for carryover in outstanding:
        # Check if there's a result for this carryover course
        result = Result.query.filter_by(
            student_id=student.id,
            course_id=carryover.course_id,
            session_id=session_id
        ).first()
        
        if not result:
            untaken.append(carryover)
    
    return (len(untaken) == 0, untaken)


def get_carryover_students_for_level(level, program, session_id):
    """
    Find students from higher levels who have results for courses at the given
    level/program in the given session.  These are carryover students who should
    appear on the lower-level spreadsheet.

    Args:
        level: The target level (e.g. 100)
        program: The programme name
        session_id: The current academic session ID

    Returns:
        list[Student]: Student objects from higher levels with results at this level
    """
    from app.models import Student, Result, Course
    from app import db

    # Sub-query: course IDs at the target level/program
    target_course_ids = db.session.query(Course.id).filter(
        Course.level == level,
        Course.program == program,
        Course.is_active == True
    ).subquery()

    # Find distinct student IDs from higher levels who have results for these courses
    carryover_student_ids = (
        db.session.query(Result.student_id)
        .join(Student, Result.student_id == Student.id)
        .filter(
            Result.course_id.in_(db.session.query(target_course_ids.c.id)),
            Result.session_id == session_id,
            Student.session_id == session_id,
            Student.level > level,
        )
        .distinct()
        .all()
    )
    carryover_ids = [sid[0] for sid in carryover_student_ids]

    if not carryover_ids:
        return []

    return (
        Student.query
        .filter(Student.id.in_(carryover_ids))
        .order_by(Student.matric_number)
        .all()
    )


def get_required_courses_for_level_program(level, program, semester=None):
    """
    Return all active courses that must be taken for a given level/program.

    Args:
        level: The level (100, 200, 300, 400)
        program: The programme name
        semester: Optional semester filter (1 or 2). If None, return both.

    Returns:
        list[Course]: List of Course objects
    """
    from app.models import Course

    q = Course.query.filter_by(level=level, program=program, is_active=True)
    if semester is not None:
        q = q.filter_by(semester=semester)
    return q.order_by(Course.semester, Course.course_code).all()


def scan_and_create_past_carryovers(session_id=None):
    """
    Scan existing results and create missing Carryover records for:
      1. Any student who has a failing grade (F) and no corresponding Carryover entry.
      2. Any student at a higher level who took a lower-level course (mark as carryover).

    Designed to back-fill carryover tracking for results that were uploaded
    before the tracking system was in place.

    Args:
        session_id: If provided, only scan results from this session.
                    If None, scan ALL sessions.

    Returns:
        dict: {'created_from_failures': int, 'flagged_carryover_results': int}
    """
    from app.models import Student, Result, Course, Carryover
    from app import db

    filters = []
    if session_id is not None:
        filters.append(Result.session_id == session_id)

    # ------------------------------------------------------------------
    # 1. Create Carryover records for failed results
    # ------------------------------------------------------------------
    failed_rows = (
        db.session.query(Result, Student, Course)
        .join(Student, Result.student_id == Student.id)
        .join(Course, Result.course_id == Course.id)
        .filter(Result.grade == 'F', *filters)
        .all()
    )

    created_failures = 0
    for result, student, course in failed_rows:
        existing = Carryover.query.filter_by(
            student_matric=student.matric_number,
            course_id=course.id,
            original_session_id=result.session_id,
        ).first()
        if not existing:
            co = Carryover(
                student_matric=student.matric_number,
                course_id=course.id,
                original_session_id=result.session_id,
                original_level=student.level,
                is_cleared=False,
            )
            db.session.add(co)
            created_failures += 1

    # ------------------------------------------------------------------
    # 2. Check if any of those carryovers were passed in a later session
    # ------------------------------------------------------------------
    # Flush so the new records are visible in queries
    db.session.flush()

    uncleared = Carryover.query.filter_by(is_cleared=False).all()
    cleared_count = 0
    for co in uncleared:
        # Find a passing result for this student + course in ANY session
        passing = (
            db.session.query(Result)
            .join(Student, Result.student_id == Student.id)
            .filter(
                Student.matric_number == co.student_matric,
                Result.course_id == co.course_id,
                Result.grade != 'F',
            )
            .order_by(Result.session_id.desc())
            .first()
        )
        if passing:
            co.is_cleared = True
            co.cleared_session_id = passing.session_id
            co.cleared_result_id = passing.id
            cleared_count += 1

    # ------------------------------------------------------------------
    # 3. Flag Result.is_carryover for higher-level students taking
    #    lower-level courses
    # ------------------------------------------------------------------
    all_results = (
        db.session.query(Result, Student, Course)
        .join(Student, Result.student_id == Student.id)
        .join(Course, Result.course_id == Course.id)
        .filter(*filters)
        .all()
    )

    flagged = 0
    for result, student, course in all_results:
        if student.level > course.level and not result.is_carryover:
            result.is_carryover = True
            flagged += 1

    db.session.commit()
    return {
        'created_from_failures': created_failures,
        'cleared': cleared_count,
        'flagged_carryover_results': flagged,
    }


def promote_students_to_new_session(from_session_id, to_session_id, db):
    """
    Promote all active students from one academic session into the next.

    Level progression rules
    -----------------------
    * 100L → 200L
    * 200L → 300L
    * 300L → 400L
    * 400L with **no outstanding carryovers** → Graduated
      (no Student row is created in to_session; matric number is returned in
      the 'graduated' list so the caller can display/log them)
    * 400L with **outstanding uncleared carryovers** → stays at 400L in the
      new session with ``Student.remarks = 'Non-Graduating'``

    The function is **idempotent**: if a student's matric number already
    exists in to_session it is skipped and counted in 'skipped'.

    A ``StudentAcademicHistory`` snapshot is written for each student's
    from_session data (GPA, credit units, standing) before the new row is
    created — skipped if a history record for that session already exists.

    Parameters
    ----------
    from_session_id : int
        PK of the AcademicSession students will be promoted FROM.
    to_session_id : int
        PK of the AcademicSession students will be promoted INTO.
    db : flask_sqlalchemy.SQLAlchemy
        The db extension object (passed in so this function has no
        circular-import dependency on ``app``).

    Returns
    -------
    dict
        {
            'promoted'      : int,        # moved up one level (100→200, 200→300, 300→400)
            'non_graduating': int,        # 400L students with carryovers kept at 400L
            'graduated'     : list[str],  # matric numbers of cleanly graduating 400L students
            'skipped'       : int,        # students already present in to_session
        }
    """
    from app.models import (
        Student, Carryover, Result, StudentAcademicHistory
    )

    students = Student.query.filter_by(
        session_id=from_session_id,
        is_active=True
    ).all()

    promoted = 0
    non_graduating = 0
    graduated = []
    skipped = 0

    for student in students:
        # ── Idempotency check ──────────────────────────────────────────────
        already_exists = Student.query.filter_by(
            matric_number=student.matric_number,
            session_id=to_session_id
        ).first()
        if already_exists:
            skipped += 1
            continue

        # ── Academic history snapshot for from_session ────────────────────
        if not StudentAcademicHistory.query.filter_by(
            student_matric=student.matric_number,
            session_id=from_session_id
        ).first():
            all_results = Result.query.filter_by(
                student_id=student.id,
                session_id=from_session_id
            ).all()
            first_sem = [r for r in all_results if r.course.semester == 1]
            second_sem = [r for r in all_results if r.course.semester == 2]
            f1_gpa = calculate_gpa(first_sem)
            f2_gpa = calculate_gpa(second_sem)
            overall_gpa = calculate_gpa(all_results)
            summary = (
                get_credit_units_summary(all_results)
                if all_results
                else {'passed': 0, 'failed': 0, 'total': 0}
            )

            if summary['total'] == 0:
                hist_remarks = 'No Results'
            elif overall_gpa >= 1.50:
                hist_remarks = 'Good Standing'
            elif overall_gpa >= 1.00:
                hist_remarks = 'Probation'
            else:
                hist_remarks = 'At Risk'

            db.session.add(StudentAcademicHistory(
                student_matric=student.matric_number,
                session_id=from_session_id,
                level=student.level,
                program=student.program,
                first_semester_gpa=f1_gpa,
                second_semester_gpa=f2_gpa,
                cgpa=overall_gpa,
                total_units_registered=summary['total'],
                total_units_passed=summary['passed'],
                total_units_failed=summary['failed'],
                remarks=hist_remarks,
            ))

        # ── Determine new level & remarks ─────────────────────────────────
        if student.level < 400:
            # Normal level progression
            new_level = student.level + 100
            new_remarks = None
            promoted += 1

        else:
            # Maximum level (400L) — check for outstanding carryovers
            outstanding_count = Carryover.query.filter_by(
                student_matric=student.matric_number,
                is_cleared=False
            ).count()

            if outstanding_count > 0:
                # Cannot graduate — remain at 400L as non-graduating
                new_level = 400
                new_remarks = 'Non-Graduating'
                non_graduating += 1
            else:
                # Clean graduation — do not create a row in the new session
                graduated.append(student.matric_number)
                continue  # skip Student creation

        # ── Create new Student record in to_session ───────────────────────
        db.session.add(Student(
            matric_number=student.matric_number,
            surname=student.surname,
            first_name=student.first_name,
            other_names=student.other_names,
            gender=student.gender,
            program=student.program,
            level=new_level,
            session_id=to_session_id,
            is_active=True,
            remarks=new_remarks,
        ))

    db.session.commit()
    return {
        'promoted': promoted,
        'non_graduating': non_graduating,
        'graduated': graduated,
        'skipped': skipped,
    }
