from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Student, Course, Result, AcademicSession, UploadLog, Carryover
from app.utils import (
    parse_results_csv, generate_sample_results_csv, allowed_file,
    get_grade_info, format_score_grade, process_carryovers_for_student,
    check_and_clear_carryovers, get_accessible_filters
)
from app.routes.auth import log_result_alteration
from config import Config

results_bp = Blueprint('results', __name__)


@results_bp.route('/')
@login_required
def index():
    """List uploaded results"""
    page = request.args.get('page', 1, type=int)
    matric_filter = request.args.get('matric', '')
    course_filter = request.args.get('course', '')
    level_filter = request.args.get('level', type=int)
    semester_filter = request.args.get('semester', type=int)
    
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    # Query results with joins
    query = Result.query.filter_by(session_id=current_session.id).join(
        Student
    ).join(Course)
    
    # Apply access restrictions
    level_access, program_access = get_accessible_filters()
    if level_access:
        query = query.filter(Course.level == level_access)
    if program_access:
        query = query.filter(Course.program == program_access)
    
    # Apply user filters
    if matric_filter:
        query = query.filter(Student.matric_number.ilike(f'%{matric_filter}%'))
    if course_filter:
        query = query.filter(Course.course_code.ilike(f'%{course_filter}%'))
    if level_filter:
        query = query.filter(Course.level == level_filter)
    if semester_filter:
        query = query.filter(Course.semester == semester_filter)
    
    # Get paginated results
    results = query.order_by(Student.matric_number, Course.course_code).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Calculate statistics
    all_results = Result.query.filter_by(session_id=current_session.id).all()
    stats = {
        'passed': len([r for r in all_results if r.grade != 'F']),
        'failed': len([r for r in all_results if r.grade == 'F'])
    }
    
    return render_template('results/index.html',
                           results=results,
                           stats=stats,
                           current_session=current_session,
                           levels=Config.LEVELS,
                           semesters=Config.SEMESTERS,
                           level_access=level_access,
                           program_access=program_access)


@results_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload results from CSV for a specific course"""
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    # Get available courses
    course_query = Course.query.filter_by(is_active=True)
    level_access, program_access = get_accessible_filters()
    
    if level_access:
        course_query = course_query.filter_by(level=level_access)
    if program_access:
        course_query = course_query.filter_by(program=program_access)
    
    courses = course_query.order_by(Course.level, Course.semester, Course.course_code).all()
    
    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        file = request.files.get('file')
        
        if not course_id:
            flash('Please select a course.', 'danger')
            return redirect(url_for('results.upload'))
        
        course = Course.query.get_or_404(course_id)
        
        # Verify access
        if level_access and course.level != level_access:
            flash('Access denied.', 'danger')
            return redirect(url_for('results.upload'))
        if program_access and course.program != program_access:
            flash('Access denied.', 'danger')
            return redirect(url_for('results.upload'))
        
        # Check if results are locked
        locked_count = Result.query.filter_by(
            course_id=course_id,
            session_id=current_session.id,
            is_locked=True
        ).count()
        
        if locked_count > 0 and not current_user.is_hod():
            flash(f'Results for {course.course_code} are locked. Only HoD can unlock them.', 'danger')
            return redirect(url_for('results.upload'))
        
        if not file or file.filename == '':
            flash('Please select a CSV file.', 'danger')
            return redirect(url_for('results.upload'))
        
        if not allowed_file(file.filename, Config.ALLOWED_EXTENSIONS):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(url_for('results.upload'))
        
        # Parse CSV
        file_content = file.read()
        records, errors = parse_results_csv(file_content)
        
        if not records:
            flash(f'No valid records found. Errors: {"; ".join(errors)}', 'danger')
            return redirect(url_for('results.upload'))
        
        # Get degree type from course
        degree_type = course.degree_type or 'BSc'
        
        # Process records
        added = 0
        updated = 0
        failed = 0
        not_found = []
        
        for record in records:
            try:
                # Find student
                student = Student.query.filter_by(
                    matric_number=record['matric_number'],
                    session_id=current_session.id,
                    level=course.level,
                    program=course.program
                ).first()
                
                if not student:
                    not_found.append(record['matric_number'])
                    failed += 1
                    continue
                
                # Calculate grade
                total_score = record['total_score']
                grade, grade_point = get_grade_info(total_score, degree_type)
                
                # Check if this is a carryover course for the student
                is_carryover = Carryover.query.filter_by(
                    student_matric=student.matric_number,
                    course_id=course.id,
                    is_cleared=False
                ).first() is not None
                
                # Check if result exists
                existing = Result.query.filter_by(
                    student_id=student.id,
                    course_id=course.id,
                    session_id=current_session.id
                ).first()
                
                if existing:
                    # Store old values before updating
                    old_ca = existing.ca_score
                    old_exam = existing.exam_score
                    old_total = existing.total_score
                    old_grade = existing.grade
                    
                    existing.ca_score = record['ca_score']
                    existing.exam_score = record['exam_score']
                    existing.total_score = total_score
                    existing.grade = grade
                    existing.grade_point = grade_point
                    existing.is_carryover = is_carryover
                    existing.uploaded_by = current_user.id
                    result_id = existing.id
                    
                    # Log the alteration if values changed
                    if (old_ca != record['ca_score'] or old_exam != record['exam_score'] or 
                        old_total != total_score or old_grade != grade):
                        from types import SimpleNamespace
                        old_result_obj = SimpleNamespace(ca_score=old_ca, exam_score=old_exam,
                                                        total_score=old_total, grade=old_grade)
                        new_result_obj = SimpleNamespace(ca_score=record['ca_score'], exam_score=record['exam_score'],
                                                        total_score=total_score, grade=grade)
                        
                        log_result_alteration(
                            result_id=result_id,
                            student=student,
                            course=course,
                            session_name=current_session.session_name,
                            alteration_type='UPDATE',
                            old_result=old_result_obj,
                            new_result=new_result_obj,
                            reason='CSV upload update'
                        )
                    
                    updated += 1
                else:
                    result = Result(
                        student_id=student.id,
                        course_id=course.id,
                        session_id=current_session.id,
                        ca_score=record['ca_score'],
                        exam_score=record['exam_score'],
                        total_score=total_score,
                        grade=grade,
                        grade_point=grade_point,
                        is_carryover=is_carryover,
                        uploaded_by=current_user.id
                    )
                    db.session.add(result)
                    db.session.flush()  # Get the result ID
                    result_id = result.id
                    
                    # Log new result creation
                    from types import SimpleNamespace
                    new_result_obj = SimpleNamespace(ca_score=record['ca_score'], exam_score=record['exam_score'],
                                                    total_score=total_score, grade=grade)
                    
                    log_result_alteration(
                        result_id=result_id,
                        student=student,
                        course=course,
                        session_name=current_session.session_name,
                        alteration_type='CREATE',
                        old_result=None,
                        new_result=new_result_obj,
                        reason='CSV upload creation'
                    )
                    
                    added += 1
                
                # Check if this result clears a carryover
                if grade != 'F' and is_carryover:
                    check_and_clear_carryovers(
                        student.matric_number, 
                        course.id, 
                        current_session.id, 
                        result_id, 
                        db
                    )
                    
            except Exception as e:
                failed += 1
                errors.append(f"{record['matric_number']}: {str(e)}")
        
        db.session.commit()
        
        # Process carryovers for all students who had results uploaded
        # This creates carryover records for any new failures
        processed_matrics = set()
        for record in records:
            matric = record['matric_number']
            if matric not in processed_matrics and matric not in not_found:
                process_carryovers_for_student(matric, current_session.id, db)
                processed_matrics.add(matric)
        
        # Log upload
        log = UploadLog(
            user_id=current_user.id,
            upload_type='results',
            filename=f"{course.course_code}_{file.filename}",
            records_processed=added + updated,
            records_failed=failed,
            status='success' if failed == 0 else 'partial',
            error_message='; '.join(errors) if errors else None
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Results upload for {course.course_code}: {added} added, {updated} updated, {failed} failed.', 
              'success' if failed == 0 else 'warning')
        
        if not_found:
            flash(f'Students not found: {", ".join(not_found[:10])}{"..." if len(not_found) > 10 else ""}', 'warning')
        
        return redirect(url_for('results.view_course', course_id=course_id))
    
    return render_template('results/upload.html',
                           current_session=current_session,
                           courses=courses)


@results_bp.route('/sample-csv')
@login_required
def sample_csv():
    """Download sample results CSV"""
    csv_content = generate_sample_results_csv()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_results.csv'}
    )


@results_bp.route('/course/<int:course_id>')
@login_required
def view_course(course_id):
    """View all results for a course"""
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    
    # Get results for this course
    results = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id if current_session else None
    ).join(Student).order_by(Student.matric_number).all()
    
    # Calculate statistics
    if results:
        scores = [r.total_score for r in results]
        stats = {
            'total': len(results),
            'passed': len([r for r in results if r.grade != 'F']),
            'failed': len([r for r in results if r.grade == 'F']),
            'average': sum(scores) / len(scores),
            'highest': max(scores),
            'lowest': min(scores)
        }
        stats['pass_rate'] = (stats['passed'] / stats['total']) * 100
    else:
        stats = None
    
    return render_template('results/view_course.html',
                           course=course,
                           results=results,
                           stats=stats,
                           current_session=current_session)


@results_bp.route('/entry/<int:course_id>', methods=['GET', 'POST'])
@login_required
def manual_entry(course_id):
    """Manual result entry for a course - Clean reimplementation"""
    
    # 1. Get course and validate
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    # 2. Check access permissions
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if results are locked
    locked_count = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id,
        is_locked=True
    ).count()
    
    if locked_count > 0 and not current_user.is_hod():
        flash(f'Results for {course.course_code} are locked. Only HoD can unlock them.', 'danger')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    # 3. Get students for this course (matching level and program)
    students = Student.query.filter_by(
        level=course.level,
        program=course.program,
        session_id=current_session.id
    ).order_by(Student.matric_number).all()
    
    # 4. Build lookup dictionaries for existing data
    existing_results = {
        r.student_id: r for r in Result.query.filter_by(
            course_id=course_id,
            session_id=current_session.id
        ).all()
    }
    
    # Get carryover status - students who failed this course previously
    carryover_matrics = {
        c.student_matric for c in Carryover.query.filter_by(
            course_id=course_id,
            is_cleared=False
        ).all()
    }
    carryover_status = {
        s.id: s.matric_number in carryover_matrics for s in students
    }
    
    # 5. Handle POST - Save results
    if request.method == 'POST':
        degree_type = course.degree_type or 'BSc'
        added_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        processed_students = []
        
        for student in students:
            # Get form values
            ca_raw = request.form.get(f'ca_{student.id}', '').strip()
            exam_raw = request.form.get(f'exam_{student.id}', '').strip()
            
            # Skip if both fields are empty
            if ca_raw == '' and exam_raw == '':
                skipped_count += 1
                continue
            
            # Parse and validate scores
            try:
                ca_score = float(ca_raw) if ca_raw else 0.0
                exam_score = float(exam_raw) if exam_raw else 0.0
                
                # Validate ranges
                if not (0 <= ca_score <= 30):
                    errors.append(f"{student.matric_number}: CA score must be 0-30")
                    continue
                if not (0 <= exam_score <= 70):
                    errors.append(f"{student.matric_number}: Exam score must be 0-70")
                    continue
                    
            except ValueError:
                errors.append(f"{student.matric_number}: Invalid score format")
                continue
            
            # Calculate total and grade
            total_score = round(ca_score + exam_score, 1)
            grade, grade_point = get_grade_info(total_score, degree_type)
            is_carryover = carryover_status.get(student.id, False)
            
            # Update or create result
            existing = existing_results.get(student.id)
            
            if existing:
                # Store old values before updating
                old_ca = existing.ca_score
                old_exam = existing.exam_score
                old_total = existing.total_score
                old_grade = existing.grade
                
                # Update existing result
                existing.ca_score = ca_score
                existing.exam_score = exam_score
                existing.total_score = total_score
                existing.grade = grade
                existing.grade_point = grade_point
                existing.is_carryover = is_carryover
                existing.uploaded_by = current_user.id
                result_id = existing.id
                
                # Log the alteration if values changed
                if (old_ca != ca_score or old_exam != exam_score or 
                    old_total != total_score or old_grade != grade):
                    # Create temporary result objects for logging
                    from types import SimpleNamespace
                    old_result_obj = SimpleNamespace(ca_score=old_ca, exam_score=old_exam, 
                                                     total_score=old_total, grade=old_grade)
                    new_result_obj = SimpleNamespace(ca_score=ca_score, exam_score=exam_score, 
                                                     total_score=total_score, grade=grade)
                    
                    log_result_alteration(
                        result_id=result_id,
                        student=student,
                        course=course,
                        session_name=current_session.session_name,
                        alteration_type='UPDATE',
                        old_result=old_result_obj,
                        new_result=new_result_obj,
                        reason='Manual entry update'
                    )
                
                updated_count += 1
            else:
                # Create new result
                new_result = Result(
                    student_id=student.id,
                    course_id=course_id,
                    session_id=current_session.id,
                    ca_score=ca_score,
                    exam_score=exam_score,
                    total_score=total_score,
                    grade=grade,
                    grade_point=grade_point,
                    is_carryover=is_carryover,
                    uploaded_by=current_user.id
                )
                db.session.add(new_result)
                db.session.flush()
                result_id = new_result.id
                
                # Log new result creation
                from types import SimpleNamespace
                new_result_obj = SimpleNamespace(ca_score=ca_score, exam_score=exam_score, 
                                                total_score=total_score, grade=grade)
                
                log_result_alteration(
                    result_id=result_id,
                    student=student,
                    course=course,
                    session_name=current_session.session_name,
                    alteration_type='CREATE',
                    old_result=None,
                    new_result=new_result_obj,
                    reason='Manual entry creation'
                )
                
                added_count += 1
            
            # Handle carryover clearing if passed
            if is_carryover and grade != 'F':
                check_and_clear_carryovers(
                    student.matric_number,
                    course_id,
                    current_session.id,
                    result_id,
                    db
                )
            elif is_carryover and grade == 'F':
                # Re-activate carryover if result changed back to F
                carryover = Carryover.query.filter_by(
                    student_matric=student.matric_number,
                    course_id=course_id
                ).first()
                if carryover and carryover.is_cleared:
                    carryover.is_cleared = False
                    carryover.cleared_session_id = None
                    carryover.cleared_result_id = None
            
            processed_students.append(student.matric_number)
        
        # Commit all changes
        try:
            db.session.commit()
            
            # Process carryovers for any new failures
            for matric in processed_students:
                process_carryovers_for_student(matric, current_session.id, db)
            
            success_msg = f'Results saved: {added_count} added, {updated_count} updated.'
            if errors:
                success_msg += f' {len(errors)} errors.'
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': success_msg,
                    'added': added_count,
                    'updated': updated_count,
                    'errors': errors
                })
            
            flash(success_msg, 'success' if not errors else 'warning')
            if errors:
                flash(f'Errors: {"; ".join(errors[:5])}{"..." if len(errors) > 5 else ""}', 'danger')
            
            return redirect(url_for('results.view_course', course_id=course_id))
            
        except Exception as e:
            db.session.rollback()
            error_msg = f'Error saving results: {str(e)}'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 500
            
            flash(error_msg, 'danger')
    
    # 6. Render template
    return render_template('results/manual_entry.html',
                           course=course,
                           students=students,
                           existing_results=existing_results,
                           carryover_status=carryover_status,
                           current_session=current_session)


@results_bp.route('/delete/<int:result_id>', methods=['POST'])
@login_required
def delete_result(result_id):
    """Delete a single result"""
    result = Result.query.get_or_404(result_id)
    course = result.course
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if result is locked
    if result.is_locked and not current_user.is_hod():
        flash('This result is locked and cannot be deleted. Contact HoD.', 'danger')
        return redirect(url_for('results.view_course', course_id=result.course_id))
    
    course_id = result.course_id
    db.session.delete(result)
    db.session.commit()
    
    flash('Result deleted.', 'success')
    return redirect(url_for('results.view_course', course_id=course_id))


@results_bp.route('/edit/<int:result_id>', methods=['POST'])
@login_required
def edit_result(result_id):
    """Edit a single result"""
    result = Result.query.get_or_404(result_id)
    course = result.course
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if result is locked
    if result.is_locked and not current_user.is_hod():
        flash('This result is locked and cannot be edited. Contact HoD.', 'danger')
        return redirect(url_for('results.view_course', course_id=result.course_id))
    
    # Get form values
    ca_score = request.form.get('ca_score', '').strip()
    exam_score = request.form.get('exam_score', '').strip()
    
    try:
        # Parse scores
        ca_score = float(ca_score) if ca_score else 0.0
        exam_score = float(exam_score) if exam_score else 0.0
        
        # Validate ranges
        if not (0 <= ca_score <= 30):
            flash('CA score must be between 0 and 30.', 'danger')
            return redirect(url_for('results.view_course', course_id=result.course_id))
        if not (0 <= exam_score <= 70):
            flash('Exam score must be between 0 and 70.', 'danger')
            return redirect(url_for('results.view_course', course_id=result.course_id))
        
        # Update result
        result.ca_score = ca_score
        result.exam_score = exam_score
        result.total_score = round(ca_score + exam_score, 1)
        
        # Get degree type and calculate grade
        degree_type = course.degree_type or 'BSc'
        old_grade = result.grade
        result.grade, result.grade_point = get_grade_info(result.total_score, degree_type)
        
        # Update modifier
        result.uploaded_by = current_user.id
        
        # Handle carryover updates
        student = result.student
        if result.is_carryover:
            if result.grade != 'F' and old_grade == 'F':
                # Changed from F to passing - clear carryover
                check_and_clear_carryovers(
                    student.matric_number,
                    course.id,
                    result.session_id,
                    result.id,
                    db
                )
            elif result.grade == 'F' and old_grade != 'F':
                # Changed from passing to F - re-activate carryover
                carryover = Carryover.query.filter_by(
                    student_matric=student.matric_number,
                    course_id=course.id
                ).first()
                if carryover and carryover.is_cleared:
                    carryover.is_cleared = False
                    carryover.cleared_session_id = None
                    carryover.cleared_result_id = None
        
        db.session.commit()
        flash('Result updated successfully.', 'success')
        
    except (ValueError, TypeError) as e:
        flash('Invalid score format.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating result: {str(e)}', 'danger')
    
    return redirect(url_for('results.view_course', course_id=result.course_id))


@results_bp.route('/course/<int:course_id>/clear', methods=['POST'])
@login_required
def clear_course_results(course_id):
    """Clear all results for a course"""
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and course.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    if program_access and course.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if any results are locked
    locked_count = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id if current_session else None,
        is_locked=True
    ).count()
    
    if locked_count > 0 and not current_user.is_hod():
        flash('Some results are locked. Only HoD can clear locked results.', 'danger')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    # Delete results
    deleted = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id if current_session else None
    ).delete()
    
    db.session.commit()
    
    flash(f'{deleted} results cleared for {course.course_code}.', 'success')
    return redirect(url_for('results.index'))


@results_bp.route('/course/<int:course_id>/approve', methods=['POST'])
@login_required
def approve_course_results(course_id):
    """Lecturer approves their course results - locks them from further editing"""
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('No active session.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if user can approve (must be assigned to this course or be level adviser/HoD)
    can_approve = False
    if current_user.is_hod() or current_user.is_level_adviser():
        # HoD and Level Adviser can approve any course in their scope
        level_access, program_access = get_accessible_filters()
        if not level_access or course.level == level_access:
            if not program_access or course.program == program_access:
                can_approve = True
    else:
        # Regular lecturer must be assigned to the course
        from app.models import CourseAssignment
        assignment = CourseAssignment.query.filter_by(
            user_id=current_user.id,
            course_id=course_id,
            session_id=current_session.id,
            is_active=True
        ).first()
        can_approve = assignment is not None
    
    if not can_approve:
        flash('You are not authorized to approve this course.', 'danger')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    # Check if there are results to approve
    results_count = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id
    ).count()
    
    if results_count == 0:
        flash('No results to approve for this course.', 'warning')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    # Lock all results for this course
    results = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id
    ).all()
    
    for result in results:
        if not result.is_locked:
            result.is_locked = True
            result.locked_by = current_user.id
            result.locked_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log the action
    from app.models import AuditLog
    log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action='APPROVE_RESULTS',
        action_category='RESULT',
        resource='Course',
        resource_id=course_id,
        details=f'Approved {results_count} results for {course.course_code}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='success'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Successfully approved {results_count} results for {course.course_code}. Results are now locked.', 'success')
    return redirect(url_for('results.view_course', course_id=course_id))


@results_bp.route('/course/<int:course_id>/unlock', methods=['POST'])
@login_required
def unlock_course_results(course_id):
    """HoD unlocks course results for editing after approval"""
    if not current_user.is_hod():
        flash('Only HoD can unlock approved results.', 'danger')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('No active session.', 'danger')
        return redirect(url_for('results.index'))
    
    # Unlock all locked results for this course
    results = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id,
        is_locked=True
    ).all()
    
    if not results:
        flash('No locked results found for this course.', 'warning')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    for result in results:
        result.is_locked = False
        result.unlocked_by = current_user.id
        result.unlocked_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log the action
    from app.models import AuditLog
    log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action='UNLOCK_RESULTS',
        action_category='RESULT',
        resource='Course',
        resource_id=course_id,
        details=f'Unlocked {len(results)} results for {course.course_code}',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='success'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Successfully unlocked {len(results)} results for {course.course_code}.', 'success')
    return redirect(url_for('results.view_course', course_id=course_id))


@results_bp.route('/course/<int:course_id>/final-approve', methods=['POST'])
@login_required
def final_approve_course(course_id):
    """HoD gives final approval to course after departmental board meeting"""
    if not current_user.is_hod():
        flash('Only HoD can give final approval.', 'danger')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    course = Course.query.get_or_404(course_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('No active session.', 'danger')
        return redirect(url_for('results.index'))
    
    # Check if all results are locked (approved by lecturers)
    total_results = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id
    ).count()
    
    locked_results = Result.query.filter_by(
        course_id=course_id,
        session_id=current_session.id,
        is_locked=True
    ).count()
    
    if total_results == 0:
        flash('No results found for this course.', 'warning')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    if locked_results < total_results:
        flash(f'Cannot give final approval. Only {locked_results} out of {total_results} results are approved by lecturers.', 'warning')
        return redirect(url_for('results.view_course', course_id=course_id))
    
    # Give final approval to course
    course.is_approved = True
    course.approved_by = current_user.id
    course.approved_at = datetime.utcnow()
    
    db.session.commit()
    
    # Log the action
    from app.models import AuditLog
    log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action='FINAL_APPROVE_COURSE',
        action_category='COURSE',
        resource='Course',
        resource_id=course_id,
        details=f'Final approval given for {course.course_code} with {total_results} results',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='success'
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Final approval given for {course.course_code}. Course results are now officially approved.', 'success')
    return redirect(url_for('results.view_course', course_id=course_id))

