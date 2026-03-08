from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Student, Course, Result, AcademicSession, User
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard view"""
    # Get current session
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    
    # Statistics
    stats = {}
    
    if current_user.role == 'hod':
        # HoD sees all data
        stats['total_students'] = Student.query.count()
        stats['total_courses'] = Course.query.filter_by(is_active=True).count()
        stats['total_results'] = Result.query.count()
        stats['total_users'] = User.query.filter_by(is_active=True).count()
        
        # Students by program
        students_by_program = db.session.query(
            Student.program, func.count(Student.id)
        ).group_by(Student.program).all()
        
        # Students by level
        students_by_level = db.session.query(
            Student.level, func.count(Student.id)
        ).group_by(Student.level).order_by(Student.level).all()
        
        # Recent uploads
        from app.models import UploadLog
        recent_uploads = UploadLog.query.order_by(
            UploadLog.created_at.desc()
        ).limit(10).all()
        
    else:
        # Level adviser sees only their assigned level and program
        student_query = Student.query
        course_query = Course.query.filter_by(is_active=True)
        
        if current_user.level:
            student_query = student_query.filter_by(level=current_user.level)
            course_query = course_query.filter_by(level=current_user.level)
        
        if current_user.program:
            student_query = student_query.filter_by(program=current_user.program)
            course_query = course_query.filter_by(program=current_user.program)
        
        stats['total_students'] = student_query.count()
        stats['total_courses'] = course_query.count()
        
        # Get results for assigned students
        student_ids = [s.id for s in student_query.all()]
        stats['total_results'] = Result.query.filter(
            Result.student_id.in_(student_ids)
        ).count() if student_ids else 0
        
        students_by_program = []
        students_by_level = []
        recent_uploads = []
    
    return render_template('dashboard/index.html',
                           stats=stats,
                           current_session=current_session,
                           students_by_program=students_by_program if current_user.role == 'hod' else [],
                           students_by_level=students_by_level if current_user.role == 'hod' else [],
                           recent_uploads=recent_uploads if current_user.role == 'hod' else [])


@dashboard_bp.route('/sessions')
@login_required
def sessions():
    """Manage academic sessions"""
    sessions = AcademicSession.query.order_by(AcademicSession.session_name.desc()).all()
    return render_template('dashboard/sessions.html', sessions=sessions)


@dashboard_bp.route('/sessions/new', methods=['POST'])
@login_required
def create_session():
    """Create new academic session"""
    session_name = request.form.get('session_name', '').strip()
    
    if not session_name:
        flash('Session name is required.', 'danger')
        return redirect(url_for('dashboard.sessions'))
    
    # Validate format (e.g., 2025/2026)
    import re
    if not re.match(r'^\d{4}/\d{4}$', session_name):
        flash('Invalid session format. Use format: 2025/2026', 'danger')
        return redirect(url_for('dashboard.sessions'))
    
    # Check if exists
    if AcademicSession.query.filter_by(session_name=session_name).first():
        flash('This session already exists.', 'danger')
        return redirect(url_for('dashboard.sessions'))
    
    session = AcademicSession(session_name=session_name)
    db.session.add(session)
    db.session.commit()
    
    flash(f'Academic session {session_name} created successfully.', 'success')
    return redirect(url_for('dashboard.sessions'))


@dashboard_bp.route('/sessions/<int:session_id>/set-current', methods=['POST'])
@login_required
def set_current_session(session_id):
    """Set session as current"""
    # Remove current flag from all sessions
    AcademicSession.query.update({AcademicSession.is_current: False})
    
    # Set selected session as current
    session = AcademicSession.query.get_or_404(session_id)
    session.is_current = True
    db.session.commit()
    
    flash(f'{session.session_name} is now the current session.', 'success')
    return redirect(url_for('dashboard.sessions'))


@dashboard_bp.route('/sessions/promote', methods=['POST'])
@login_required
def promote_students():
    """Promote all students in from_session into to_session.

    Rules
    -----
    * 100L → 200L, 200L → 300L, 300L → 400L
    * 400L + no outstanding carryovers → Graduated (no new row created)
    * 400L + outstanding carryovers  → 400L in new session,
      Student.remarks = 'Non-Graduating'

    Access: HoD only.
    """
    if current_user.role not in ('hod', 'admin'):
        flash('Only the Head of Department or Admin can promote students.', 'danger')
        return redirect(url_for('dashboard.sessions'))

    from_session_id = request.form.get('from_session_id', type=int)
    to_session_id   = request.form.get('to_session_id',   type=int)

    if not from_session_id or not to_session_id:
        flash('Both source and target sessions are required.', 'danger')
        return redirect(url_for('dashboard.sessions'))

    if from_session_id == to_session_id:
        flash('Source and target sessions must be different.', 'danger')
        return redirect(url_for('dashboard.sessions'))

    from_session = AcademicSession.query.get(from_session_id)
    to_session   = AcademicSession.query.get(to_session_id)

    if not from_session or not to_session:
        flash('One or both sessions not found.', 'danger')
        return redirect(url_for('dashboard.sessions'))

    from app.utils.grading import promote_students_to_new_session

    result = promote_students_to_new_session(from_session_id, to_session_id, db)

    parts = []
    if result['promoted']:
        parts.append(f"{result['promoted']} student(s) promoted")
    if result['non_graduating']:
        parts.append(
            f"{result['non_graduating']} final-year non-graduating student(s) "
            f"carried forward at 400L"
        )
    if result['graduated']:
        parts.append(
            f"{len(result['graduated'])} student(s) graduated "
            f"({', '.join(result['graduated'][:5])}"
            f"{'...' if len(result['graduated']) > 5 else ''})"
        )
    if result['skipped']:
        parts.append(f"{result['skipped']} already in target session (skipped)")
    if not any([result['promoted'], result['non_graduating'],
                result['graduated'], result['skipped']]):
        parts.append('No students found in the source session')

    flash('. '.join(parts) + '.', 'success')

    from app.models import AuditLog
    db.session.add(AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action='PROMOTE_STUDENTS',
        action_category='STUDENT',
        resource='AcademicSession',
        resource_id=to_session_id,
        details=(
            f'Promoted students from {from_session.session_name} to '
            f'{to_session.session_name}: '
            f"promoted={result['promoted']}, "
            f"non_graduating={result['non_graduating']}, "
            f"graduated={len(result['graduated'])}, "
            f"skipped={result['skipped']}"
        ),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='success',
    ))
    db.session.commit()

    return redirect(url_for('dashboard.sessions'))


@dashboard_bp.route('/sessions/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete academic session"""
    if current_user.role != 'hod':
        flash('Only the Head of Department can delete sessions.', 'danger')
        return redirect(url_for('dashboard.sessions'))
    
    session = AcademicSession.query.get_or_404(session_id)
    
    # Check if session has data
    if session.students.count() > 0 or session.results.count() > 0:
        flash('Cannot delete session with existing data.', 'danger')
        return redirect(url_for('dashboard.sessions'))
    
    db.session.delete(session)
    db.session.commit()
    
    flash(f'Session {session.session_name} deleted.', 'success')
    return redirect(url_for('dashboard.sessions'))
