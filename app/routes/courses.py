from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Course
from config import Config

from app.utils import get_accessible_filters

courses_bp = Blueprint('courses', __name__)


@courses_bp.route('/')
@login_required
def index():
    """List all courses"""
    page = request.args.get('page', 1, type=int)
    level_filter = request.args.get('level', type=int)
    program_filter = request.args.get('program', '')
    semester_filter = request.args.get('semester', type=int)
    
    query = Course.query.filter_by(is_active=True)
    
    # Apply access restrictions
    level_access, program_access = get_accessible_filters()
    if level_access:
        query = query.filter_by(level=level_access)
    if program_access:
        query = query.filter_by(program=program_access)
    
    # Apply user filters
    if level_filter and not level_access:
        query = query.filter_by(level=level_filter)
    if program_filter and not program_access:
        query = query.filter_by(program=program_filter)
    if semester_filter:
        query = query.filter_by(semester=semester_filter)
    
    courses = query.order_by(Course.level, Course.semester, Course.course_code).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('courses/index.html',
                           courses=courses,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           semesters=Config.SEMESTERS,
                           course_status=Config.COURSE_STATUS,
                           level_filter=level_filter,
                           program_filter=program_filter,
                           semester_filter=semester_filter,
                           level_access=level_access,
                           program_access=program_access)


@courses_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    """Add new course"""
    if request.method == 'POST':
        course_code = request.form.get('course_code', '').strip().upper()
        course_title = request.form.get('course_title', '').strip()
        credit_unit = request.form.get('credit_unit', type=int)
        semester = request.form.get('semester', type=int)
        level = request.form.get('level', type=int)
        program = request.form.get('program', '')
        status = request.form.get('status', 'C')
        degree_type = request.form.get('degree_type', 'BSc')
        
        # Validate access
        level_access, program_access = get_accessible_filters()
        if level_access and level != level_access:
            flash('You can only add courses for your assigned level.', 'danger')
            return redirect(url_for('courses.create'))
        if program_access and program != program_access:
            flash('You can only add courses for your assigned program.', 'danger')
            return redirect(url_for('courses.create'))
        
        # Validate required fields
        if not all([course_code, course_title, credit_unit, semester, level, program]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('courses.create'))
        
        # Check duplicate
        existing = Course.query.filter_by(
            course_code=course_code,
            program=program,
            level=level
        ).first()
        
        if existing:
            flash('A course with this code already exists for this program and level.', 'danger')
            return redirect(url_for('courses.create'))
        
        course = Course(
            course_code=course_code,
            course_title=course_title,
            credit_unit=credit_unit,
            semester=semester,
            level=level,
            program=program,
            status=status,
            degree_type=degree_type
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Course {course_code} added successfully.', 'success')
        return redirect(url_for('courses.index'))
    
    level_access, program_access = get_accessible_filters()
    
    return render_template('courses/create.html',
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           semesters=Config.SEMESTERS,
                           course_status=Config.COURSE_STATUS,
                           degree_types=Config.DEGREE_TYPES,
                           level_access=level_access,
                           program_access=program_access)


@courses_bp.route('/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(course_id):
    """Edit course"""
    course = Course.query.get_or_404(course_id)
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('courses.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('courses.index'))
    
    if request.method == 'POST':
        course.course_code = request.form.get('course_code', '').strip().upper()
        course.course_title = request.form.get('course_title', '').strip()
        course.credit_unit = request.form.get('credit_unit', type=int)
        course.semester = request.form.get('semester', type=int)
        course.status = request.form.get('status', 'C')
        course.degree_type = request.form.get('degree_type', 'BSc')
        
        # Don't allow changing level/program if has results
        if course.results.count() == 0:
            new_level = request.form.get('level', type=int)
            new_program = request.form.get('program', '')
            
            if level_access and new_level != level_access:
                flash('You cannot change course to a different level.', 'danger')
                return redirect(url_for('courses.edit', course_id=course_id))
            if program_access and new_program != program_access:
                flash('You cannot change course to a different program.', 'danger')
                return redirect(url_for('courses.edit', course_id=course_id))
            
            course.level = new_level
            course.program = new_program
        
        db.session.commit()
        
        flash('Course updated successfully.', 'success')
        return redirect(url_for('courses.index'))
    
    return render_template('courses/edit.html',
                           course=course,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           semesters=Config.SEMESTERS,
                           course_status=Config.COURSE_STATUS,
                           degree_types=Config.DEGREE_TYPES,
                           level_access=level_access,
                           program_access=program_access)


@courses_bp.route('/<int:course_id>/delete', methods=['POST'])
@login_required
def delete(course_id):
    """Delete course"""
    course = Course.query.get_or_404(course_id)
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('courses.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('courses.index'))
    
    # Check if course has results
    if course.results.count() > 0:
        flash('Cannot delete course with existing results. Delete results first.', 'danger')
        return redirect(url_for('courses.index'))
    
    code = course.course_code
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course {code} deleted.', 'success')
    return redirect(url_for('courses.index'))


@courses_bp.route('/batch', methods=['GET', 'POST'])
@login_required
def batch_create():
    """Add multiple courses at once"""
    if request.method == 'POST':
        level = request.form.get('level', type=int)
        program = request.form.get('program', '')
        degree_type = request.form.get('degree_type', 'BSc')
        
        # Validate access
        level_access, program_access = get_accessible_filters()
        if level_access and level != level_access:
            flash('You can only add courses for your assigned level.', 'danger')
            return redirect(url_for('courses.batch_create'))
        if program_access and program != program_access:
            flash('You can only add courses for your assigned program.', 'danger')
            return redirect(url_for('courses.batch_create'))
        
        # Process courses from form
        courses_data = request.form.get('courses_data', '')
        lines = courses_data.strip().split('\n')
        
        added = 0
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # Expected format: CODE,Title,Units,Semester,Status
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 4:
                errors.append(f'Line {line_num}: Invalid format')
                continue
            
            try:
                course_code = parts[0].upper()
                course_title = parts[1]
                credit_unit = int(parts[2])
                semester = int(parts[3])
                status = parts[4].upper() if len(parts) > 4 else 'C'
                
                # Validate
                if credit_unit < 1 or credit_unit > 6:
                    errors.append(f'Line {line_num}: Invalid credit unit')
                    continue
                if semester not in [1, 2]:
                    errors.append(f'Line {line_num}: Invalid semester')
                    continue
                if status not in ['C', 'R', 'E']:
                    status = 'C'
                
                # Check duplicate
                existing = Course.query.filter_by(
                    course_code=course_code,
                    program=program,
                    level=level
                ).first()
                
                if existing:
                    errors.append(f'Line {line_num}: Course {course_code} already exists')
                    continue
                
                course = Course(
                    course_code=course_code,
                    course_title=course_title,
                    credit_unit=credit_unit,
                    semester=semester,
                    level=level,
                    program=program,
                    status=status,
                    degree_type=degree_type
                )
                db.session.add(course)
                added += 1
                
            except Exception as e:
                errors.append(f'Line {line_num}: {str(e)}')
        
        db.session.commit()
        
        flash(f'{added} courses added successfully.', 'success')
        if errors:
            flash(f'Errors: {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}', 'warning')
        
        return redirect(url_for('courses.index'))
    
    level_access, program_access = get_accessible_filters()
    
    return render_template('courses/batch.html',
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           degree_types=Config.DEGREE_TYPES,
                           level_access=level_access,
                           program_access=program_access)


@courses_bp.route('/<int:course_id>/assign-lecturer', methods=['GET', 'POST'])
@login_required
def assign_lecturer(course_id):
    """Assign a lecturer to a course (HoD only)"""
    if not current_user.is_hod():
        flash('Only HoD can assign lecturers to courses.', 'danger')
        return redirect(url_for('courses.index'))
    
    from app.models import CourseAssignment, AcademicSession, User
    
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('courses.index'))
    
    if request.method == 'POST':
        lecturer_id = request.form.get('lecturer_id', type=int)
        
        if not lecturer_id:
            flash('Please select a lecturer.', 'danger')
            return redirect(url_for('courses.assign_lecturer', course_id=course_id))
        
        lecturer = User.query.get_or_404(lecturer_id)
        
        # Check if already assigned
        existing = CourseAssignment.query.filter_by(
            user_id=lecturer_id,
            course_id=course_id,
            session_id=current_session.id,
            is_active=True
        ).first()
        
        if existing:
            flash(f'{lecturer.full_name} is already assigned to this course.', 'warning')
            return redirect(url_for('courses.assign_lecturer', course_id=course_id))
        
        # Create assignment
        assignment = CourseAssignment(
            user_id=lecturer_id,
            course_id=course_id,
            session_id=current_session.id,
            assigned_by=current_user.id
        )
        db.session.add(assignment)
        db.session.commit()
        
        flash(f'{lecturer.full_name} has been assigned to {course.course_code}.', 'success')
        return redirect(url_for('courses.view_course_assignments', course_id=course_id))
    
    # Get all lecturers (including level advisers, excluding HoD can also assign)
    lecturers = User.query.filter(
        User.is_active == True,
        User.role.in_(['lecturer', 'level_adviser', 'hod'])
    ).order_by(User.full_name).all()
    
    # Get current assignments
    assignments = CourseAssignment.query.filter_by(
        course_id=course_id,
        session_id=current_session.id,
        is_active=True
    ).all()
    
    assigned_ids = [a.user_id for a in assignments]
    
    return render_template('courses/assign_lecturer.html',
                           course=course,
                           lecturers=lecturers,
                           assignments=assignments,
                           assigned_ids=assigned_ids,
                           current_session=current_session)


@courses_bp.route('/<int:course_id>/assignments')
@login_required
def view_course_assignments(course_id):
    """View lecturer assignments for a course"""
    if not current_user.is_hod():
        flash('Only HoD can view course assignments.', 'danger')
        return redirect(url_for('courses.index'))
    
    from app.models import CourseAssignment, AcademicSession
    
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('courses.index'))
    
    assignments = CourseAssignment.query.filter_by(
        course_id=course_id,
        session_id=current_session.id,
        is_active=True
    ).all()
    
    return render_template('courses/assignments.html',
                           course=course,
                           assignments=assignments,
                           current_session=current_session)


@courses_bp.route('/assignment/<int:assignment_id>/remove', methods=['POST'])
@login_required
def remove_assignment(assignment_id):
    """Remove a lecturer assignment (HoD only)"""
    if not current_user.is_hod():
        flash('Only HoD can remove lecturer assignments.', 'danger')
        return redirect(url_for('courses.index'))
    
    from app.models import CourseAssignment
    
    assignment = CourseAssignment.query.get_or_404(assignment_id)
    course_id = assignment.course_id
    
    assignment.is_active = False
    db.session.commit()
    
    flash('Lecturer assignment removed.', 'success')
    return redirect(url_for('courses.view_course_assignments', course_id=course_id))
