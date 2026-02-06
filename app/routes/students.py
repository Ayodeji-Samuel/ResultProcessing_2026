from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from app import db
from app.models import Student, AcademicSession, UploadLog, Result, Course, Carryover, StudentAcademicHistory
from app.utils import parse_student_csv, generate_sample_student_csv, allowed_file, calculate_gpa, get_credit_units_summary, get_accessible_filters
from config import Config

students_bp = Blueprint('students', __name__)


@students_bp.route('/')
@login_required
def index():
    """List all students"""
    page = request.args.get('page', 1, type=int)
    level_filter = request.args.get('level', type=int)
    program_filter = request.args.get('program', '')
    search = request.args.get('search', '').strip()
    
    # Get current session
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    query = Student.query
    
    # Apply session filter
    if current_session:
        query = query.filter_by(session_id=current_session.id)
    
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
    
    # Search
    if search:
        query = query.filter(
            db.or_(
                Student.matric_number.ilike(f'%{search}%'),
                Student.surname.ilike(f'%{search}%'),
                Student.first_name.ilike(f'%{search}%')
            )
        )
    
    # Order and paginate
    students = query.order_by(Student.matric_number).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('students/index.html',
                           students=students,
                           current_session=current_session,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           level_filter=level_filter,
                           program_filter=program_filter,
                           search=search,
                           level_access=level_access,
                           program_access=program_access)


@students_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload student records from CSV"""
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    if request.method == 'POST':
        # Get form data
        level = request.form.get('level', type=int)
        program = request.form.get('program', '')
        file = request.files.get('file')
        
        # Validate access
        level_access, program_access = get_accessible_filters()
        if level_access and level != level_access:
            flash('You can only upload students for your assigned level.', 'danger')
            return redirect(url_for('students.upload'))
        if program_access and program != program_access:
            flash('You can only upload students for your assigned program.', 'danger')
            return redirect(url_for('students.upload'))
        
        if not level or not program:
            flash('Level and Program are required.', 'danger')
            return redirect(url_for('students.upload'))
        
        if not file or file.filename == '':
            flash('Please select a CSV file.', 'danger')
            return redirect(url_for('students.upload'))
        
        if not allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(url_for('students.upload'))
        
        # Parse CSV
        file_content = file.read()
        records, errors = parse_student_csv(file_content)
        
        if not records:
            flash(f'No valid records found. Errors: {"; ".join(errors)}', 'danger')
            return redirect(url_for('students.upload'))
        
        # Process records
        added = 0
        updated = 0
        failed = 0
        
        for record in records:
            try:
                # Check if student exists
                existing = Student.query.filter_by(
                    matric_number=record['matric_number'],
                    session_id=current_session.id
                ).first()
                
                if existing:
                    # Update existing
                    existing.surname = record['surname']
                    existing.first_name = record['first_name']
                    existing.other_names = record['other_names']
                    existing.gender = record.get('gender')
                    existing.level = level
                    existing.program = program
                    updated += 1
                else:
                    # Create new
                    student = Student(
                        matric_number=record['matric_number'],
                        surname=record['surname'],
                        first_name=record['first_name'],
                        other_names=record['other_names'],
                        gender=record.get('gender'),
                        level=level,
                        program=program,
                        session_id=current_session.id
                    )
                    db.session.add(student)
                    added += 1
                    
            except Exception as e:
                failed += 1
                errors.append(f"{record['matric_number']}: {str(e)}")
        
        db.session.commit()
        
        # Log upload
        log = UploadLog(
            user_id=current_user.id,
            upload_type='students',
            filename=file.filename,
            records_processed=added + updated,
            records_failed=failed,
            status='success' if failed == 0 else 'partial',
            error_message='; '.join(errors) if errors else None
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Upload complete: {added} added, {updated} updated, {failed} failed.', 
              'success' if failed == 0 else 'warning')
        
        if errors:
            flash(f'Errors: {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}', 'warning')
        
        return redirect(url_for('students.index'))
    
    # GET request
    level_access, program_access = get_accessible_filters()
    
    return render_template('students/upload.html',
                           current_session=current_session,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           level_access=level_access,
                           program_access=program_access)


@students_bp.route('/sample-csv')
@login_required
def sample_csv():
    """Download sample student CSV"""
    csv_content = generate_sample_student_csv()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_students.csv'}
    )


@students_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create():
    """Add single student"""
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    if request.method == 'POST':
        matric_number = request.form.get('matric_number', '').strip().upper()
        surname = request.form.get('surname', '').strip().upper()
        first_name = request.form.get('first_name', '').strip().title()
        other_names = request.form.get('other_names', '').strip().title()
        gender = request.form.get('gender', '').strip().upper()
        level = request.form.get('level', type=int)
        program = request.form.get('program', '')
        
        # Validate access
        level_access, program_access = get_accessible_filters()
        if level_access and level != level_access:
            flash('You can only add students for your assigned level.', 'danger')
            return redirect(url_for('students.create'))
        if program_access and program != program_access:
            flash('You can only add students for your assigned program.', 'danger')
            return redirect(url_for('students.create'))
        
        # Validate required fields
        if not all([matric_number, surname, first_name, level, program]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('students.create'))
        
        # Check duplicate
        existing = Student.query.filter_by(
            matric_number=matric_number,
            session_id=current_session.id
        ).first()
        
        if existing:
            flash('A student with this matric number already exists.', 'danger')
            return redirect(url_for('students.create'))
        
        student = Student(
            matric_number=matric_number,
            surname=surname,
            first_name=first_name,
            other_names=other_names or None,
            gender=gender if gender in ['M', 'F'] else None,
            level=level,
            program=program,
            session_id=current_session.id
        )
        
        db.session.add(student)
        db.session.commit()
        
        flash(f'Student {matric_number} added successfully.', 'success')
        return redirect(url_for('students.index'))
    
    level_access, program_access = get_accessible_filters()
    
    return render_template('students/create.html',
                           current_session=current_session,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           level_access=level_access,
                           program_access=program_access)


@students_bp.route('/<int:student_id>')
@login_required
def view(student_id):
    """View student details with comprehensive academic history"""
    student = Student.query.get_or_404(student_id)
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and student.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    if program_access and student.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    
    # Get current session
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    # Get all students with same matric across all sessions (for history tracking)
    all_student_records = Student.query.filter_by(
        matric_number=student.matric_number
    ).join(AcademicSession).order_by(AcademicSession.session_name).all()
    
    # Build comprehensive academic history
    academic_history = []
    cumulative_results = []
    
    for student_record in all_student_records:
        session = student_record.session
        results = student_record.results.filter_by(session_id=student_record.session_id).all()
        
        # Separate by semester
        first_sem_results = [r for r in results if r.course.semester == 1]
        second_sem_results = [r for r in results if r.course.semester == 2]
        
        # Calculate semester GPAs
        first_sem_gpa = calculate_gpa(first_sem_results) if first_sem_results else 0.0
        second_sem_gpa = calculate_gpa(second_sem_results) if second_sem_results else 0.0
        
        # Credit unit summaries
        first_sem_summary = get_credit_units_summary(first_sem_results) if first_sem_results else {'passed': 0, 'failed': 0, 'total': 0}
        second_sem_summary = get_credit_units_summary(second_sem_results) if second_sem_results else {'passed': 0, 'failed': 0, 'total': 0}
        
        # Combined session summary
        all_results = first_sem_results + second_sem_results
        session_summary = get_credit_units_summary(all_results) if all_results else {'passed': 0, 'failed': 0, 'total': 0}
        session_gpa = calculate_gpa(all_results) if all_results else 0.0
        
        # Add to cumulative for CGPA
        cumulative_results.extend(all_results)
        cgpa = calculate_gpa(cumulative_results) if cumulative_results else 0.0
        
        # Determine academic standing
        if session_summary['total'] > 0:
            if cgpa >= 1.50:
                remarks = 'Good Standing'
            elif cgpa >= 1.00:
                remarks = 'Probation'
            else:
                remarks = 'At Risk'
        else:
            remarks = 'No Results'
        
        # Get failed courses (carryovers) for this session
        failed_courses = [r for r in all_results if r.grade == 'F']
        
        academic_history.append({
            'student_record': student_record,
            'session': session,
            'level': student_record.level,
            'first_semester': {
                'results': first_sem_results,
                'gpa': first_sem_gpa,
                'summary': first_sem_summary
            },
            'second_semester': {
                'results': second_sem_results,
                'gpa': second_sem_gpa,
                'summary': second_sem_summary
            },
            'session_gpa': session_gpa,
            'cgpa': cgpa,
            'session_summary': session_summary,
            'remarks': remarks,
            'failed_courses': failed_courses,
            'is_current': session.is_current
        })
    
    # Get all carryover courses for this student
    carryovers = Carryover.query.filter_by(
        student_matric=student.matric_number
    ).order_by(Carryover.created_at).all()
    
    # Separate outstanding and cleared carryovers
    outstanding_carryovers = [c for c in carryovers if not c.is_cleared]
    cleared_carryovers = [c for c in carryovers if c.is_cleared]
    
    # Get current session results
    current_results = student.results.all() if student else []
    
    # Calculate overall statistics
    total_units_registered = sum(h['session_summary']['total'] for h in academic_history)
    total_units_passed = sum(h['session_summary']['passed'] for h in academic_history)
    total_units_failed = sum(h['session_summary']['failed'] for h in academic_history)
    overall_cgpa = calculate_gpa(cumulative_results) if cumulative_results else 0.0
    
    return render_template('students/view.html', 
                           student=student, 
                           results=current_results,
                           academic_history=academic_history,
                           carryovers=carryovers,
                           outstanding_carryovers=outstanding_carryovers,
                           cleared_carryovers=cleared_carryovers,
                           total_units_registered=total_units_registered,
                           total_units_passed=total_units_passed,
                           total_units_failed=total_units_failed,
                           overall_cgpa=overall_cgpa,
                           current_session=current_session)


@students_bp.route('/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(student_id):
    """Edit student"""
    student = Student.query.get_or_404(student_id)
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and student.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    if program_access and student.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    
    if request.method == 'POST':
        student.matric_number = request.form.get('matric_number', '').strip().upper()
        student.surname = request.form.get('surname', '').strip().upper()
        student.first_name = request.form.get('first_name', '').strip().title()
        student.other_names = request.form.get('other_names', '').strip().title() or None
        gender = request.form.get('gender', '').strip().upper()
        student.gender = gender if gender in ['M', 'F'] else None
        
        new_level = request.form.get('level', type=int)
        new_program = request.form.get('program', '')
        
        # Validate access for new values
        if level_access and new_level != level_access:
            flash('You cannot change student to a different level.', 'danger')
            return redirect(url_for('students.edit', student_id=student_id))
        if program_access and new_program != program_access:
            flash('You cannot change student to a different program.', 'danger')
            return redirect(url_for('students.edit', student_id=student_id))
        
        student.level = new_level
        student.program = new_program
        
        db.session.commit()
        
        flash('Student updated successfully.', 'success')
        return redirect(url_for('students.view', student_id=student_id))
    
    return render_template('students/edit.html',
                           student=student,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           level_access=level_access,
                           program_access=program_access)


@students_bp.route('/<int:student_id>/delete', methods=['POST'])
@login_required
def delete(student_id):
    """Delete student"""
    student = Student.query.get_or_404(student_id)
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and student.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    if program_access and student.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    
    # Check if student has results
    if student.results.count() > 0:
        flash('Cannot delete student with existing results. Delete results first.', 'danger')
        return redirect(url_for('students.view', student_id=student_id))
    
    matric = student.matric_number
    db.session.delete(student)
    db.session.commit()
    
    flash(f'Student {matric} deleted.', 'success')
    return redirect(url_for('students.index'))
