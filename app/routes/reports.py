from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, send_file, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Student, Course, Result, AcademicSession, Carryover, User
from app.utils import (
    generate_spreadsheet_pdf, generate_student_result_pdf,
    calculate_gpa, get_credit_units_summary, format_score_grade,
    get_accessible_filters
)
from config import Config
from io import BytesIO

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard"""
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    level_access, program_access = get_accessible_filters()
    
    return render_template('reports/index.html',
                           current_session=current_session,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           semesters=Config.SEMESTERS,
                           level_access=level_access,
                           program_access=program_access)


@reports_bp.route('/spreadsheet', methods=['GET', 'POST'])
@login_required
def spreadsheet():
    """Generate examination record spreadsheet"""
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    if not current_session:
        flash('Please set a current academic session first.', 'warning')
        return redirect(url_for('dashboard.sessions'))
    
    level_access, program_access = get_accessible_filters()
    
    if request.method == 'POST':
        level = request.form.get('level', type=int)
        program = request.form.get('program', '')
        semester = request.form.get('semester', '')  # '1', '2', or 'both'
        
        # Validate access
        if level_access and level != level_access:
            flash('Access denied.', 'danger')
            return redirect(url_for('reports.spreadsheet'))
        if program_access and program != program_access:
            flash('Access denied.', 'danger')
            return redirect(url_for('reports.spreadsheet'))
        
        if not all([level, program, semester]):
            flash('Please select level, program, and semester.', 'danger')
            return redirect(url_for('reports.spreadsheet'))
        
        # Get students
        students = Student.query.filter_by(
            level=level,
            program=program,
            session_id=current_session.id
        ).order_by(Student.matric_number).all()
        
        if not students:
            flash('No students found for the selected criteria.', 'warning')
            return redirect(url_for('reports.spreadsheet'))
        
        # Get courses for first semester
        first_sem_courses = []
        second_sem_courses = []
        
        # Get first semester courses if semester is '1' or 'both'
        if semester in ['1', 'both']:
            first_sem_courses = Course.query.filter_by(
                level=level,
                program=program,
                semester=1,
                is_active=True
            ).order_by(Course.course_code).all()
        
        # Get second semester courses if semester is '2' or 'both'
        if semester in ['2', 'both']:
            second_sem_courses = Course.query.filter_by(
                level=level,
                program=program,
                semester=2,
                is_active=True
            ).order_by(Course.course_code).all()
        
        if not first_sem_courses and not second_sem_courses:
            flash('No courses found for the selected criteria.', 'warning')
            return redirect(url_for('reports.spreadsheet'))
        
        # Build student result data
        students_data = []
        
        for student in students:
            student_row = {
                'matric_number': student.matric_number,
                'name': student.full_name,
                'gender': student.gender,
                'first_semester': {},
                'second_semester': {},
                'first_semester_summary': {'passed_units': 0, 'failed_units': 0, 'total_units': 0, 'gpa': 0},
                'second_semester_summary': {'passed_units': 0, 'failed_units': 0, 'total_units': 0, 'gpa': 0},
                'session_summary': {'passed_units': 0, 'failed_units': 0, 'total_units': 0, 'cgpa': 0}
            }
            
            # Initialize result lists
            first_sem_results = []
            second_sem_results = []
            
            # First semester results
            if first_sem_courses:
                for course in first_sem_courses:
                    result = Result.query.filter_by(
                        student_id=student.id,
                        course_id=course.id,
                        session_id=current_session.id
                    ).first()
                    
                    if result:
                        student_row['first_semester'][course.course_code] = format_score_grade(
                            result.total_score, result.grade
                        )
                        first_sem_results.append(result)
                    else:
                        student_row['first_semester'][course.course_code] = '-'
                
                if first_sem_results:
                    summary = get_credit_units_summary(first_sem_results)
                    student_row['first_semester_summary'] = {
                        'passed_units': summary['passed'],
                        'failed_units': summary['failed'],
                        'total_units': summary['total'],
                        'gpa': calculate_gpa(first_sem_results)
                    }
            
            # Second semester results
            if second_sem_courses:
                for course in second_sem_courses:
                    result = Result.query.filter_by(
                        student_id=student.id,
                        course_id=course.id,
                        session_id=current_session.id
                    ).first()
                    
                    if result:
                        student_row['second_semester'][course.course_code] = format_score_grade(
                            result.total_score, result.grade
                        )
                        second_sem_results.append(result)
                    else:
                        student_row['second_semester'][course.course_code] = '-'
                
                if second_sem_results:
                    summary = get_credit_units_summary(second_sem_results)
                    student_row['second_semester_summary'] = {
                        'passed_units': summary['passed'],
                        'failed_units': summary['failed'],
                        'total_units': summary['total'],
                        'gpa': calculate_gpa(second_sem_results)
                    }
            
            # Calculate session summary if both semesters requested
            if semester == 'both' and (first_sem_results or second_sem_results):
                all_sem_results = first_sem_results + second_sem_results
                if all_sem_results:
                    session_summary = get_credit_units_summary(all_sem_results)
                    student_row['session_summary'] = {
                        'passed_units': session_summary['passed'],
                        'failed_units': session_summary['failed'],
                        'total_units': session_summary['total'],
                        'cgpa': calculate_gpa(all_sem_results)
                    }
            
            # Get active carryovers for remark
            active_carryovers = Carryover.query.filter_by(
                student_matric=student.matric_number,
                is_cleared=False
            ).all()
            
            if active_carryovers:
                # Format: "CO: CSC101, MTH201, PHY102"
                carryover_codes = []
                for co in active_carryovers:
                    if co.course:
                        carryover_codes.append(co.course.course_code)
                student_row['remark'] = "CO: " + ", ".join(carryover_codes) if carryover_codes else "Proceed"
            else:
                student_row['remark'] = "Proceed"
            
            students_data.append(student_row)
        
        # Preview or download
        action = request.form.get('action', 'preview')
        
        # Prepare course data for template/PDF
        first_courses_data = [{
            'code': c.course_code,
            'title': c.course_title,
            'status': c.status,
            'credit_unit': c.credit_unit
        } for c in first_sem_courses]
        
        second_courses_data = [{
            'code': c.course_code,
            'title': c.course_title,
            'status': c.status,
            'credit_unit': c.credit_unit
        } for c in second_sem_courses]
        
        if action == 'download':
            # Get dean name from form
            dean_name = request.form.get('dean_name', '').strip()
            if not dean_name:
                flash('Please enter the Dean\'s name.', 'danger')
                return redirect(url_for('reports.spreadsheet'))
            
            # Get Course Adviser (level adviser for this level and program)
            level_adviser = User.query.filter_by(
                role='level_adviser',
                level=level,
                program=program
            ).first()
            course_adviser_name = level_adviser.full_name if level_adviser else current_user.full_name
            
            # Get HOD name (user with role 'hod')
            hod = User.query.filter_by(role='hod').first()
            hod_name = hod.full_name if hod else 'N/A'
            
            # Generate PDF
            data = {
                'students': students_data,
                'first_semester_courses': first_courses_data,
                'second_semester_courses': second_courses_data,
                'level': level,
                'program': program,
                'semester': semester,
                'session': current_session.session_name
            }
            
            config = {
                'university_name': Config.UNIVERSITY_NAME,
                'faculty_name': Config.FACULTY_NAME,
                'department_name': Config.DEPARTMENT_NAME
            }
            
            signatories = {
                'course_adviser': course_adviser_name,
                'hod': hod_name,
                'dean': dean_name
            }
            
            # Get font size from form (default 10, minimum 10)
            font_size = request.form.get('font_size', type=int, default=10)
            font_size = max(10, font_size)  # Ensure minimum of 10
            
            pdf_buffer = generate_spreadsheet_pdf(data, config, signatories, font_size=font_size)
            
            filename = f"results_{program.replace(' ', '_')}_{level}_{semester}_{current_session.session_name.replace('/', '-')}.pdf"
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        else:
            # Preview - prepare data for template
            if semester == 'both':
                # For combined semesters, pass students_data directly
                # Calculate average CGPA for stats
                total_cgpa = 0
                students_with_cgpa = 0
                
                for student_data in students_data:
                    cgpa = student_data.get('session_summary', {}).get('cgpa', 0)
                    if cgpa > 0:
                        total_cgpa += cgpa
                        students_with_cgpa += 1
                
                average_cgpa = total_cgpa / students_with_cgpa if students_with_cgpa > 0 else 0
                
                # Calculate total credits (first + second semester)
                total_credits = sum(c.credit_unit for c in first_sem_courses) + sum(c.credit_unit for c in second_sem_courses)
                
                return render_template('reports/spreadsheet_preview.html',
                                       students=students_data,
                                       first_semester_courses=first_courses_data,
                                       second_semester_courses=second_courses_data,
                                       level=level,
                                       program=program,
                                       semester=semester,
                                       session=current_session,
                                       current_session=current_session,
                                       total_credits=total_credits,
                                       average_gpa=average_cgpa,
                                       config={
                                           'university_name': Config.UNIVERSITY_NAME,
                                           'faculty_name': Config.FACULTY_NAME,
                                           'department_name': Config.DEPARTMENT_NAME
                                       })
            else:
                # Single semester preview
                # Combine courses based on semester selection
                if semester == '1':
                    # Show only first semester
                    courses = first_sem_courses
                    courses_data = first_courses_data
                elif semester == '2':
                    # Show only second semester
                    courses = second_sem_courses
                    courses_data = second_courses_data
                
                # Calculate total credits
                total_credits = sum(c.credit_unit for c in courses)
                
                # Build student_data for template with detailed results
                student_data = []
                total_gpa = 0
                students_with_gpa = 0
                
                for student in students:
                    student_courses = [c for c in courses]
                    results_dict = {}
                    all_results = []
                    
                    for course in student_courses:
                        result = Result.query.filter_by(
                            student_id=student.id,
                            course_id=course.id,
                            session_id=current_session.id
                        ).first()
                        if result:
                            results_dict[course.id] = result
                            all_results.append(result)
                    
                    # Calculate student's GPA
                    if all_results:
                        summary = get_credit_units_summary(all_results)
                        gpa = calculate_gpa(all_results)
                        tcu = summary['total']
                        cup = summary['passed']  # Credit Unit Passed
                        cuf = summary['failed']  # Credit Unit Failed
                        tgp = sum(r.grade_point * r.course.credit_unit for r in all_results if r.grade_point is not None)
                    else:
                        gpa = 0
                        tcu = 0
                        cup = 0
                        cuf = 0
                        tgp = 0
                    
                    # Get active carryovers for remark
                    active_carryovers = Carryover.query.filter_by(
                        student_matric=student.matric_number,
                        is_cleared=False
                    ).all()
                    
                    if active_carryovers:
                        # Format: "CO: CSC101, MTH201, PHY102"
                        carryover_codes = []
                        for co in active_carryovers:
                            if co.course:
                                carryover_codes.append(co.course.course_code)
                        remark = "CO: " + ", ".join(carryover_codes) if carryover_codes else "Proceed"
                    else:
                        remark = "Proceed"
                    
                    student_data.append({
                        'student': student,
                        'results': results_dict,
                        'gpa': gpa,
                        'tcu': tcu,
                        'cup': cup,
                        'cuf': cuf,
                        'tgp': tgp,
                        'remark': remark
                    })
                    
                    if gpa > 0:
                        total_gpa += gpa
                        students_with_gpa += 1
                
                # Calculate average GPA
                average_gpa = total_gpa / students_with_gpa if students_with_gpa > 0 else 0
                
                return render_template('reports/spreadsheet_preview.html',
                                       students=students_data,
                                       student_data=student_data,
                                       courses=courses,
                                       first_semester_courses=first_courses_data,
                                       second_semester_courses=second_courses_data,
                                       level=level,
                                       program=program,
                                       semester=semester,
                                       session=current_session,
                                       current_session=current_session,
                                       total_credits=total_credits,
                                       average_gpa=average_gpa,
                                       config={
                                           'university_name': Config.UNIVERSITY_NAME,
                                           'faculty_name': Config.FACULTY_NAME,
                                           'department_name': Config.DEPARTMENT_NAME
                                       })
    
    # Get all academic sessions for dropdown
    sessions = AcademicSession.query.order_by(AcademicSession.session_name.desc()).all()
    
    return render_template('reports/spreadsheet.html',
                           current_session=current_session,
                           sessions=sessions,
                           levels=Config.LEVELS,
                           programs=Config.PROGRAMS,
                           level_access=level_access,
                           program_access=program_access)


@reports_bp.route('/student/<int:student_id>')
@login_required
def student_result(student_id):
    """View individual student result"""
    student = Student.query.get_or_404(student_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and student.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    if program_access and student.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    
    # Get first semester results
    first_sem_results = Result.query.join(Course).filter(
        Result.student_id == student_id,
        Result.session_id == current_session.id if current_session else True,
        Course.semester == 1
    ).all()
    
    # Get second semester results
    second_sem_results = Result.query.join(Course).filter(
        Result.student_id == student_id,
        Result.session_id == current_session.id if current_session else True,
        Course.semester == 2
    ).all()
    
    # Calculate summaries
    first_sem_summary = get_credit_units_summary(first_sem_results) if first_sem_results else None
    second_sem_summary = get_credit_units_summary(second_sem_results) if second_sem_results else None
    
    if first_sem_summary:
        first_sem_summary['gpa'] = calculate_gpa(first_sem_results)
    if second_sem_summary:
        second_sem_summary['gpa'] = calculate_gpa(second_sem_results)
    
    # Cumulative
    all_results = first_sem_results + second_sem_results
    cumulative = get_credit_units_summary(all_results) if all_results else None
    if cumulative:
        cumulative['cgpa'] = calculate_gpa(all_results)
    
    return render_template('reports/student_result_view.html',
                           student=student,
                           first_semester_results=first_sem_results,
                           second_semester_results=second_sem_results,
                           first_semester_summary=first_sem_summary,
                           second_semester_summary=second_sem_summary,
                           cumulative=cumulative,
                           current_session=current_session)


@reports_bp.route('/student/<int:student_id>/pdf')
@login_required
def student_result_pdf(student_id):
    """Download individual student result as PDF"""
    student = Student.query.get_or_404(student_id)
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    semester_filter = request.args.get('semester', 'all').lower()
    
    # Check access
    level_access, program_access = get_accessible_filters()
    if level_access and student.level != level_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    if program_access and student.program != program_access:
        flash('Access denied.', 'danger')
        return redirect(url_for('students.index'))
    
    # Get results
    first_sem_results = Result.query.join(Course).filter(
        Result.student_id == student_id,
        Result.session_id == current_session.id if current_session else True,
        Course.semester == 1
    ).all()
    
    second_sem_results = Result.query.join(Course).filter(
        Result.student_id == student_id,
        Result.session_id == current_session.id if current_session else True,
        Course.semester == 2
    ).all()

    # Apply semester filter (optional)
    if semester_filter in ['1', 'first', 'first_semester']:
        second_sem_results = []
        summary_title = 'FIRST SEMESTER SUMMARY'
        gpa_label = 'GPA'
    elif semester_filter in ['2', 'second', 'second_semester']:
        first_sem_results = []
        summary_title = 'SECOND SEMESTER SUMMARY'
        gpa_label = 'GPA'
    else:
        summary_title = 'CUMULATIVE SUMMARY'
        gpa_label = 'Cumulative GPA'
    
    # Build result data
    first_sem_data = [{
        'course_code': r.course.course_code,
        'course_title': r.course.course_title,
        'credit_unit': r.course.credit_unit,
        'total_score': r.total_score,
        'grade': r.grade,
        'grade_point': r.grade_point
    } for r in first_sem_results]
    
    second_sem_data = [{
        'course_code': r.course.course_code,
        'course_title': r.course.course_title,
        'credit_unit': r.course.credit_unit,
        'total_score': r.total_score,
        'grade': r.grade,
        'grade_point': r.grade_point
    } for r in second_sem_results]
    
    # Summaries
    first_summary = get_credit_units_summary(first_sem_results) if first_sem_results else {}
    second_summary = get_credit_units_summary(second_sem_results) if second_sem_results else {}
    
    if first_summary:
        first_summary['gpa'] = calculate_gpa(first_sem_results)
    if second_summary:
        second_summary['gpa'] = calculate_gpa(second_sem_results)
    
    all_results = first_sem_results + second_sem_results
    cumulative = get_credit_units_summary(all_results) if all_results else {}
    if cumulative:
        cumulative['cgpa'] = calculate_gpa(all_results)
    
    student_data = {
        'matric_number': student.matric_number,
        'name': student.full_name,
        'gender': student.gender,
        'program': student.program,
        'level': student.level
    }
    
    results_data = {
        'session': current_session.session_name if current_session else 'N/A',
        'first_semester': first_sem_data,
        'second_semester': second_sem_data,
        'first_semester_summary': first_summary,
        'second_semester_summary': second_summary,
        'cumulative': cumulative,
        'summary_title': summary_title,
        'gpa_label': gpa_label,
        'summary_gpa': calculate_gpa(all_results) if all_results else 0.0
    }
    
    config = {
        'university_name': Config.UNIVERSITY_NAME,
        'faculty_name': Config.FACULTY_NAME,
        'department_name': Config.DEPARTMENT_NAME
    }
    
    pdf_buffer = generate_student_result_pdf(student_data, results_data, config)
    
    filename = f"result_{student.matric_number.replace('/', '-')}_{current_session.session_name.replace('/', '-') if current_session else 'all'}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@reports_bp.route('/search')
@login_required
def search_student():
    """Search for student to view results"""
    search = request.args.get('q', '').strip()
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    students = []
    if search:
        query = Student.query.filter(
            db.or_(
                Student.matric_number.ilike(f'%{search}%'),
                Student.surname.ilike(f'%{search}%'),
                Student.first_name.ilike(f'%{search}%')
            )
        )
        
        # Apply access restrictions
        level_access, program_access = get_accessible_filters()
        if level_access:
            query = query.filter_by(level=level_access)
        if program_access:
            query = query.filter_by(program=program_access)
        
        if current_session:
            query = query.filter_by(session_id=current_session.id)
        
        students = query.order_by(Student.matric_number).limit(50).all()
    
    return render_template('reports/search.html',
                           students=students,
                           search=search,
                           current_session=current_session)


@reports_bp.route('/api/spreadsheet_summary')
@login_required
def get_spreadsheet_summary():
    """Get summary data for spreadsheet filters (AJAX endpoint)"""
    program = request.args.get('program')
    level = request.args.get('level')
    semester = request.args.get('semester')
    session_id = request.args.get('session_id')
    
    if not all([program, level, semester, session_id]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    # Get level and program access
    level_access, program_access = get_accessible_filters()
    
    # Apply access restrictions
    if level_access and int(level) != level_access:
        return jsonify({'error': 'Access denied'}), 403
    
    if program_access and program != program_access:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get courses for this program, level, and semester
    # Handle semester: '1', '2', or 'both'
    if semester == 'both':
        # Get both first and second semester courses
        courses = Course.query.filter_by(
            program=program,
            level=int(level)
        ).filter(Course.semester.in_([1, 2])).all()
    else:
        # Get specific semester courses
        courses = Course.query.filter_by(
            program=program,
            level=int(level),
            semester=int(semester)
        ).all()
    
    # Get students for this program and level
    students = Student.query.filter_by(
        program=program,
        level=int(level)
    ).all()
    
    # Count results
    total_results = 0
    if students and courses:
        total_results = Result.query.filter(
            Result.student_id.in_([s.id for s in students]),
            Result.course_id.in_([c.id for c in courses]),
            Result.session_id == int(session_id)
        ).count()
    
    # Calculate total credit units
    total_units = sum(c.credit_unit for c in courses)
    
    return jsonify({
        'students': len(students),
        'courses': len(courses),
        'results': total_results,
        'total_units': total_units
    })

