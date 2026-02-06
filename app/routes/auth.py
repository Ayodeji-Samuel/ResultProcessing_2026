from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import json
import secrets
import re
import requests
from user_agents import parse as parse_ua
from app import db
from app.models import User, AuditLog, ResultAlteration
from app.forms import LoginForm, RegistrationForm, ChangePasswordForm, EditUserForm, ForceChangePasswordForm
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Import default location configuration
try:
    from app.location_config import DEFAULT_LOCATION
except ImportError:
    # Fallback if config file doesn't exist
    DEFAULT_LOCATION = {
        'name': 'Local Machine (Campus Network)',
        'latitude': 9.0765,
        'longitude': 7.3986
    }


def get_location_from_ip(ip_address):
    """Get approximate location and coordinates from IP address using free geolocation API"""
    if not ip_address or ip_address in ['127.0.0.1', 'localhost', '::1']:
        # For localhost, use university's default location from config
        return (
            DEFAULT_LOCATION.get('name', 'Local Machine (Campus Network)'),
            DEFAULT_LOCATION.get('latitude'),
            DEFAULT_LOCATION.get('longitude')
        )
    
    try:
        # Using ip-api.com (free, no API key required, 45 requests/minute)
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                country = data.get('country', '')
                latitude = data.get('lat')
                longitude = data.get('lon')
                
                location_parts = [p for p in [city, region, country] if p]
                location = ', '.join(location_parts) if location_parts else 'Unknown'
                return location, latitude, longitude
    except Exception as e:
        print(f"Error getting location for IP {ip_address}: {e}")
    
    return 'Unknown', None, None


def parse_user_agent(user_agent_string):
    """Parse user agent to extract device info using user-agents library"""
    if not user_agent_string:
        return 'Unknown', 'Unknown', 'Unknown'
    
    try:
        user_agent = parse_ua(user_agent_string)
        
        # Get device type
        if user_agent.is_mobile:
            device_type = f'Mobile ({user_agent.device.family})'
        elif user_agent.is_tablet:
            device_type = f'Tablet ({user_agent.device.family})'
        elif user_agent.is_pc:
            device_type = 'Desktop'
        elif user_agent.is_bot:
            device_type = 'Bot'
        else:
            device_type = 'Unknown'
        
        # Get browser with version
        browser = user_agent.browser.family
        if user_agent.browser.version_string:
            browser = f"{browser} {user_agent.browser.version_string}"
        
        # Get OS with version
        os = user_agent.os.family
        if user_agent.os.version_string:
            os = f"{os} {user_agent.os.version_string}"
        
        return device_type, browser, os
    except Exception as e:
        print(f"Error parsing user agent: {e}")
        return 'Unknown', 'Unknown', 'Unknown'


def hod_required(f):
    """Decorator to require HoD role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'hod':
            flash('Access denied. This feature is only accessible by the Head of Department.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require Admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. This feature is only accessible by System Administrators.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def admin_or_hod_required(f):
    """Decorator to require Admin or HoD role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'hod']:
            flash('Access denied. This feature is only accessible by Administrators or Head of Department.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def log_audit(user_id, action, action_category='GENERAL', resource=None, resource_id=None, 
              details=None, old_values=None, new_values=None, status='success'):
    """Enhanced audit logging with full tracking"""
    # Get user agent - try both methods
    user_agent_str = request.headers.get('User-Agent', '')
    if not user_agent_str and request.user_agent:
        user_agent_str = request.user_agent.string or ''
    
    device_type, browser, os = parse_user_agent(user_agent_str)
    
    # Get IP address (handle proxy/load balancer)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    
    # Get username
    username = None
    if user_id:
        user = User.query.get(user_id)
        if user:
            username = user.username
    
    audit = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        action_category=action_category,
        resource=resource,
        resource_id=resource_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent_str[:512] if user_agent_str else None,
        device_type=device_type,
        browser=browser,
        operating_system=os,
        session_id=session.get('_id', secrets.token_hex(16)),
        status=status
    )
    db.session.add(audit)
    db.session.commit()


def log_result_alteration(result_id, student, course, session_name, alteration_type, 
                          old_result=None, new_result=None, reason=None):
    """Log result alteration for admin oversight"""
    from app.models import Result, Student, Course
    
    # Get user agent - try both methods
    user_agent_str = request.headers.get('User-Agent', '')
    if not user_agent_str and request.user_agent:
        user_agent_str = request.user_agent.string or ''
    
    device_type, browser, os = parse_user_agent(user_agent_str)
    
    # Get IP address (handle proxy/load balancer)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    
    # Get location and coordinates from IP
    location, latitude, longitude = get_location_from_ip(ip_address)
    
    # Try to get computer username from various headers
    device_username = (
        request.headers.get('X-Computer-Name') or
        request.headers.get('X-Device-Name') or
        request.environ.get('COMPUTERNAME') or
        request.environ.get('USERNAME') or
        'Unknown'
    )
    
    alteration = ResultAlteration(
        result_id=result_id,
        student_matric=student.matric_number,
        student_name=student.full_name,
        course_code=course.course_code,
        course_title=course.course_title,
        session_name=session_name,
        altered_by_id=current_user.id,
        altered_by_name=current_user.full_name,
        altered_by_role=current_user.role,
        alteration_type=alteration_type,
        old_ca_score=old_result.ca_score if old_result else None,
        new_ca_score=new_result.ca_score if new_result else None,
        old_exam_score=old_result.exam_score if old_result else None,
        new_exam_score=new_result.exam_score if new_result else None,
        old_total_score=old_result.total_score if old_result else None,
        new_total_score=new_result.total_score if new_result else None,
        old_grade=old_result.grade if old_result else None,
        new_grade=new_result.grade if new_result else None,
        ip_address=ip_address,
        user_agent=user_agent_str[:512] if user_agent_str else None,
        device_type=device_type,
        browser=browser,
        operating_system=os,
        device_username=device_username[:128] if device_username else None,
        location=location,
        latitude=latitude,
        longitude=longitude,
        reason=reason
    )
    db.session.add(alteration)
    db.session.commit()


def generate_password():
    """Generate a secure random password"""
    import string
    chars = string.ascii_letters + string.digits + '@$!%*?&'
    password = ''.join(secrets.choice(chars) for _ in range(12))
    # Ensure it has all required character types
    password = (secrets.choice(string.ascii_uppercase) +
                secrets.choice(string.ascii_lowercase) +
                secrets.choice(string.digits) +
                secrets.choice('@$!%*?&') +
                password[:8])
    return password


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with enhanced security"""
    if current_user.is_authenticated:
        if current_user.must_change_password:
            return redirect(url_for('auth.force_change_password'))
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Username is the university email
        user = User.query.filter_by(username=form.username.data.lower().strip()).first()
        
        if user is None:
            flash('Invalid credentials. Please check your university email and password.', 'danger')
            log_audit(None, 'FAILED_LOGIN', 'AUTH', details=f'Invalid username attempt: {form.username.data}', status='failed')
            return render_template('auth/login.html', form=form)
        
        # Check if account is permanently locked by HoD
        if user.is_locked:
            flash('Your account has been locked due to security concerns. Please contact the Head of Department to unlock your account.', 'danger')
            log_audit(user.id, 'LOCKED_LOGIN_ATTEMPT', 'AUTH', 
                     details='Attempted login on HoD-locked account', status='blocked')
            return render_template('auth/login.html', form=form)
        
        # Check if account is temporarily locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            flash('Your account has been locked due to too many failed login attempts. Please contact the Head of Department to unlock your account.', 'danger')
            log_audit(user.id, 'LOCKED_LOGIN_ATTEMPT', 'AUTH', 
                     details='Attempted login on temporarily locked account', status='blocked')
            return render_template('auth/login.html', form=form)
        
        # Check if account is active
        if not user.is_active:
            flash('Your account has been deactivated. Please contact the Head of Department.', 'danger')
            log_audit(user.id, 'INACTIVE_LOGIN_ATTEMPT', 'AUTH', 
                     details='Attempted login with inactive account', status='blocked')
            return render_template('auth/login.html', form=form)
        
        # Verify password
        if not user.check_password(form.password.data):
            user.failed_login_attempts += 1
            
            # Lock account after 3 failed attempts (HoD must unlock)
            if user.failed_login_attempts >= 3:
                user.is_locked = True
                user.locked_until = None  # Permanent lock until HoD unlocks
                db.session.commit()
                
                flash('Your account has been locked due to 3 failed login attempts. Please contact the Head of Department to unlock your account.', 'danger')
                log_audit(user.id, 'ACCOUNT_LOCKED', 'AUTH', 
                         details='Account locked after 3 failed password attempts', status='blocked')
            else:
                remaining = 3 - user.failed_login_attempts
                flash(f'Invalid password. {remaining} attempt(s) remaining before your account is locked.', 'danger')
                log_audit(user.id, 'FAILED_LOGIN', 'AUTH', 
                         details=f'Invalid password. Attempt {user.failed_login_attempts}/3', status='failed')
                db.session.commit()
            
            return render_template('auth/login.html', form=form)
        
        # Successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        # Get IP address (handle proxy/load balancer)
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address and ',' in ip_address:
            ip_address = ip_address.split(',')[0].strip()
        user.last_login_ip = ip_address
        user.last_login_device = request.user_agent.string[:256] if request.user_agent.string else None
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        log_audit(user.id, 'LOGIN', 'AUTH', details='Successful login')
        
        # Check if user must change password (first login)
        if user.must_change_password:
            flash('Welcome! You must change your password before continuing.', 'warning')
            return redirect(url_for('auth.force_change_password'))
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('dashboard.index')
        
        flash(f'Welcome back, {user.full_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/force-change-password', methods=['GET', 'POST'])
@login_required
def force_change_password():
    """Force password change on first login"""
    if not current_user.must_change_password:
        return redirect(url_for('dashboard.index'))
    
    form = ForceChangePasswordForm()
    
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        current_user.must_change_password = False
        db.session.commit()
        
        log_audit(current_user.id, 'FIRST_PASSWORD_CHANGE', 'AUTH', 
                 details='User changed password after first login')
        flash('Password changed successfully! Welcome to the system.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/force_change_password.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    log_audit(current_user.id, 'LOGOUT', 'AUTH', details='User logged out')
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@login_required
@admin_or_hod_required
def users():
    """List all users (Admin sees all, HoD cannot see admin accounts)"""
    if current_user.is_admin():
        # Admin sees everyone
        users = User.query.order_by(User.created_at.desc()).all()
    else:
        # HoD cannot see admin accounts
        users = User.query.filter(User.role != 'admin').order_by(User.created_at.desc()).all()
    
    log_audit(current_user.id, 'VIEW', 'USER', details='Viewed user list')
    return render_template('auth/users.html', users=users)


@auth_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_or_hod_required
def create_user():
    """Create new user (Admin and HoD) - Level advisers cannot self-register"""
    from config import Config
    
    form = RegistrationForm()
    form.program.choices = [('', 'Select Program')] + [(p, p) for p in Config.PROGRAMS]
    
    # HoD cannot create admin accounts - filter role choices
    if current_user.is_admin():
        form.role.choices = [
            ('lecturer', 'Lecturer'),
            ('level_adviser', 'Level Adviser'),
            ('hod', 'Head of Department'),
            ('admin', 'Administrator')
        ]
    else:
        # HoD can only create lecturer, level_adviser, and hod accounts
        form.role.choices = [
            ('lecturer', 'Lecturer'),
            ('level_adviser', 'Level Adviser'),
            ('hod', 'Head of Department')
        ]
    
    if form.validate_on_submit():
        # HoD cannot create admin accounts - extra validation
        if current_user.role == 'hod' and form.role.data == 'admin':
            flash('You do not have permission to create administrator accounts.', 'danger')
            return redirect(url_for('auth.users'))
        
        # Username must be university email
        email = form.username.data.lower().strip()
        
        # Generate temporary password
        temp_password = generate_password()
        
        # For lecturers, don't assign level/program (they get course assignments)
        # For level advisers, require level and program
        if form.role.data == 'lecturer':
            program = None
            level = None
        else:
            program = form.program.data if form.program.data else None
            level = int(form.level.data) if form.level.data else None
        
        user = User(
            username=email,  # University email is the username
            email=email,
            full_name=form.full_name.data,
            role=form.role.data,
            program=program,
            level=level,
            is_active=True,
            must_change_password=True,  # Force password change on first login
            created_by=current_user.id
        )
        user.set_password(temp_password)
        
        db.session.add(user)
        db.session.commit()
        
        log_audit(current_user.id, 'CREATE', 'USER', 'User', user.id, 
                 details=f'Created user account: {user.username}',
                 new_values={'username': user.username, 'role': user.role, 'program': user.program})
        
        flash(f'User account created successfully!', 'success')
        flash(f'Username (Email): {email}', 'info')
        flash(f'Temporary Password: {temp_password}', 'warning')
        flash('The user must change this password upon first login.', 'info')
        
        return redirect(url_for('auth.users'))
    
    return render_template('auth/create_user.html', form=form)


@auth_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_hod_required
def edit_user(user_id):
    """Edit user (Admin and HoD)"""
    from config import Config
    
    user = User.query.get_or_404(user_id)
    
    # HoD cannot edit Admin accounts
    if current_user.role == 'hod':
        if user.role == 'admin':
            flash('You cannot edit administrator accounts.', 'danger')
            return redirect(url_for('auth.users'))
    
    form = EditUserForm(obj=user)
    form.program.choices = [('', 'Select Program')] + [(p, p) for p in Config.PROGRAMS]
    
    # HoD cannot set role to admin - filter role choices
    if current_user.is_admin():
        form.role.choices = [
            ('lecturer', 'Lecturer'),
            ('level_adviser', 'Level Adviser'),
            ('hod', 'Head of Department'),
            ('admin', 'Administrator')
        ]
    else:
        # HoD can only assign lecturer, level_adviser, and hod roles
        form.role.choices = [
            ('lecturer', 'Lecturer'),
            ('level_adviser', 'Level Adviser'),
            ('hod', 'Head of Department')
        ]
    
    # Store old values for audit
    old_values = {
        'email': user.email,
        'full_name': user.full_name,
        'role': user.role,
        'program': user.program,
        'level': user.level,
        'is_active': user.is_active
    }
    
    if form.validate_on_submit():
        # HoD cannot change role to admin - extra validation
        if current_user.role == 'hod' and form.role.data == 'admin':
            flash('You do not have permission to assign administrator role.', 'danger')
            return redirect(url_for('auth.users'))
        
        user.email = form.email.data.lower().strip()
        user.full_name = form.full_name.data
        user.role = form.role.data
        
        # For lecturers, clear level and program (they get course assignments instead)
        # For level advisers and HoD, use the form values
        if form.role.data == 'lecturer':
            user.program = None
            user.level = None
        else:
            user.program = form.program.data if form.program.data else None
            user.level = int(form.level.data) if form.level.data else None
        
        user.is_active = form.is_active.data
        
        new_values = {
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
            'program': user.program,
            'level': user.level,
            'is_active': user.is_active
        }
        
        db.session.commit()
        
        log_audit(current_user.id, 'UPDATE', 'USER', 'User', user.id, 
                 details=f'Updated user: {user.username}',
                 old_values=old_values, new_values=new_values)
        
        flash(f'User {user.username} has been updated.', 'success')
        return redirect(url_for('auth.users'))
    
    # Pre-populate form
    form.level.data = str(user.level) if user.level else ''
    form.program.data = user.program if user.program else ''
    
    return render_template('auth/edit_user.html', form=form, user=user)


@auth_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@hod_required
def toggle_user_status(user_id):
    """Toggle user active status (HoD only)"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('auth.users'))
    
    if user.role == 'hod':
        flash('You cannot deactivate an HoD account.', 'danger')
        return redirect(url_for('auth.users'))
    
    old_status = user.is_active
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    log_audit(current_user.id, 'TOGGLE_STATUS', 'USER', 'User', user.id, 
             details=f'User {status}: {user.username}',
             old_values={'is_active': old_status}, new_values={'is_active': user.is_active})
    
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@login_required
@admin_or_hod_required
def unlock_user(user_id):
    """Unlock a locked user account (Admin and HoD)"""
    user = User.query.get_or_404(user_id)
    
    # HoD cannot unlock Admin accounts
    if current_user.role == 'hod' and user.role == 'admin':
        flash('You cannot unlock administrator accounts.', 'danger')
        return redirect(url_for('auth.users'))
    
    if not user.is_locked and not user.locked_until:
        flash(f'User {user.username} is not locked.', 'info')
        return redirect(url_for('auth.users'))
    
    user.is_locked = False
    user.locked_until = None
    user.failed_login_attempts = 0
    db.session.commit()
    
    log_audit(current_user.id, 'UNLOCK_ACCOUNT', 'USER', 'User', user.id, 
             details=f'Unlocked account for: {user.username}')
    
    flash(f'Account for {user.username} has been unlocked. They can now log in.', 'success')
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_or_hod_required
def reset_user_password(user_id):
    """Reset user password (Admin and HoD) - generates new temporary password"""
    user = User.query.get_or_404(user_id)
    
    # HoD cannot reset Admin or other HoD passwords
    if current_user.role == 'hod':
        if user.role in ['admin', 'hod'] and user.id != current_user.id:
            flash('You cannot reset administrator or other HoD passwords.', 'danger')
            return redirect(url_for('auth.users'))
    
    # Generate a new temporary password
    temp_password = generate_password()
    user.set_password(temp_password)
    user.failed_login_attempts = 0
    user.is_locked = False
    user.locked_until = None
    user.must_change_password = True
    
    db.session.commit()
    
    log_audit(current_user.id, 'RESET_PASSWORD', 'USER', 'User', user.id, 
             details=f'Password reset for: {user.username}')
    
    flash(f'Password for {user.username} has been reset.', 'success')
    flash(f'New Temporary Password: {temp_password}', 'warning')
    flash('The user must change this password upon next login.', 'info')
    
    return redirect(url_for('auth.users'))


@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_or_hod_required
def delete_user(user_id):
    """Delete a user account (Admin and HoD)"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('auth.users'))
    
    # HoD cannot delete Admin or HoD accounts
    if current_user.role == 'hod' and user.role in ['admin', 'hod']:
        flash('You cannot delete administrator or HoD accounts.', 'danger')
        return redirect(url_for('auth.users'))
    
    # Admin cannot delete other Admin accounts (safety measure)
    if current_user.role == 'admin' and user.role == 'admin':
        flash('You cannot delete other administrator accounts.', 'danger')
        return redirect(url_for('auth.users'))
    
    username = user.username
    
    # Log before deletion
    log_audit(current_user.id, 'DELETE', 'USER', 'User', user.id, 
             details=f'Deleted user account: {username}',
             old_values={'username': username, 'email': user.email, 'role': user.role})
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted.', 'success')
    return redirect(url_for('auth.users'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change own password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            log_audit(current_user.id, 'FAILED_PASSWORD_CHANGE', 'AUTH', 
                     details='Incorrect current password provided', status='failed')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        log_audit(current_user.id, 'CHANGE_PASSWORD', 'AUTH', 'User', current_user.id, 
                 details='Password changed by user')
        flash('Your password has been changed successfully.', 'success')
        return redirect(url_for('dashboard.index'))
    
    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/profile')
@login_required
def profile():
    """View user profile"""
    log_audit(current_user.id, 'VIEW', 'USER', 'User', current_user.id, 
             details='Viewed own profile')
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/security-monitor')
@login_required
@admin_required
def security_monitor():
    """Security monitoring dashboard (Admin and HoD)"""
    # Get various statistics
    total_users = User.query.count()
    locked_users = User.query.filter(db.or_(User.is_locked == True, 
                                            db.and_(User.locked_until != None, 
                                                   User.locked_until > datetime.utcnow()))).count()
    active_users = User.query.filter_by(is_active=True).count()
    
    # Recent security events
    security_events = AuditLog.query.filter(
        AuditLog.action.in_(['FAILED_LOGIN', 'ACCOUNT_LOCKED', 'LOCKED_LOGIN_ATTEMPT', 
                             'UNLOCK_ACCOUNT', 'RESET_PASSWORD', 'DELETE'])
    ).order_by(AuditLog.created_at.desc()).limit(50).all()
    
    # Recent login activity
    login_activity = AuditLog.query.filter(
        AuditLog.action.in_(['LOGIN', 'LOGOUT', 'FAILED_LOGIN'])
    ).order_by(AuditLog.created_at.desc()).limit(100).all()
    
    # Locked accounts
    locked_accounts = User.query.filter(
        db.or_(User.is_locked == True, 
               db.and_(User.locked_until != None, User.locked_until > datetime.utcnow()))
    ).all()
    
    log_audit(current_user.id, 'VIEW', 'SECURITY', details='Viewed security monitor dashboard')
    
    return render_template('auth/security_monitor.html', 
                          total_users=total_users,
                          locked_users=locked_users,
                          active_users=active_users,
                          security_events=security_events,
                          login_activity=login_activity,
                          locked_accounts=locked_accounts)


@auth_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """View comprehensive audit logs (Admin and HoD)"""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    category_filter = request.args.get('category', '')
    user_filter = request.args.get('user', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = AuditLog.query
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    if category_filter:
        query = query.filter(AuditLog.action_category == category_filter)
    if user_filter:
        query = query.filter(AuditLog.username.ilike(f'%{user_filter}%'))
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get unique values for filters
    actions = db.session.query(AuditLog.action).distinct().all()
    categories = db.session.query(AuditLog.action_category).distinct().all()
    
    log_audit(current_user.id, 'VIEW', 'AUDIT', details='Viewed audit logs')
    
    return render_template('auth/audit_logs.html', logs=logs, 
                          actions=[a[0] for a in actions if a[0]],
                          categories=[c[0] for c in categories if c[0]],
                          current_filters={
                              'action': action_filter,
                              'category': category_filter,
                              'user': user_filter,
                              'status': status_filter,
                              'date_from': date_from,
                              'date_to': date_to
                          })


@auth_bp.route('/result-alterations')
@login_required
@admin_required
def result_alterations():
    """View result alteration logs (Admin only)"""
    page = request.args.get('page', 1, type=int)
    student_filter = request.args.get('student', '')
    course_filter = request.args.get('course', '')
    user_filter = request.args.get('user', '')
    alteration_type = request.args.get('type', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = ResultAlteration.query
    
    if student_filter:
        query = query.filter(db.or_(
            ResultAlteration.student_matric.ilike(f'%{student_filter}%'),
            ResultAlteration.student_name.ilike(f'%{student_filter}%')
        ))
    if course_filter:
        query = query.filter(db.or_(
            ResultAlteration.course_code.ilike(f'%{course_filter}%'),
            ResultAlteration.course_title.ilike(f'%{course_filter}%')
        ))
    if user_filter:
        query = query.filter(ResultAlteration.altered_by_name.ilike(f'%{user_filter}%'))
    if alteration_type:
        query = query.filter(ResultAlteration.alteration_type == alteration_type)
    if date_from:
        query = query.filter(ResultAlteration.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(ResultAlteration.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    alterations = query.order_by(ResultAlteration.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get unique values for filters
    types = db.session.query(ResultAlteration.alteration_type).distinct().all()
    
    # Get unique courses (code and title combined)
    courses = db.session.query(
        ResultAlteration.course_code,
        ResultAlteration.course_title
    ).distinct().order_by(ResultAlteration.course_code).all()
    course_list = [{'code': c[0], 'title': c[1]} for c in courses if c[0]]
    
    # Get unique users who have made alterations
    users = db.session.query(
        ResultAlteration.altered_by_name,
        ResultAlteration.altered_by_role
    ).distinct().order_by(ResultAlteration.altered_by_name).all()
    user_list = [{'name': u[0], 'role': u[1]} for u in users if u[0]]
    
    log_audit(current_user.id, 'VIEW', 'RESULT_ALTERATION', 
              details='Viewed result alteration logs')
    
    return render_template('auth/result_alterations.html', 
                          alterations=alterations,
                          alteration_types=[t[0] for t in types if t[0]],
                          courses=course_list,
                          users=user_list,
                          current_filters={
                              'student': student_filter,
                              'course': course_filter,
                              'user': user_filter,
                              'type': alteration_type,
                              'date_from': date_from,
                              'date_to': date_to
                          })
