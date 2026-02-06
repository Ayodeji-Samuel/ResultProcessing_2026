"""Grading utility functions"""
from app.models import GradingSystem
from flask_login import current_user


def get_accessible_filters():
    """
    Get filters based on user access level.
    
    Returns:
        tuple: (level_access, program_access)
            - None, None for HoD (no restrictions)
            - level, program for other roles
    """
    if current_user.role == 'hod':
        return None, None
    return current_user.level, current_user.program


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
