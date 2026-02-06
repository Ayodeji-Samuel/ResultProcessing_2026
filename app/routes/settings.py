from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import GradingSystem, SystemSetting
from app.routes.auth import hod_required, admin_or_hod_required
from config import Config
import os

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
@login_required
@admin_or_hod_required
def index():
    """Settings dashboard"""
    from app.models import AcademicSession
    current_session = AcademicSession.query.filter_by(is_current=True).first()
    return render_template('settings/index.html', current_session=current_session)


@settings_bp.route('/grading')
@login_required
@admin_or_hod_required
def grading():
    """Manage grading systems"""
    grading_systems = GradingSystem.query.order_by(
        GradingSystem.degree_type, 
        GradingSystem.min_score.desc()
    ).all()
    
    # Group by degree type
    grouped = {}
    for gs in grading_systems:
        if gs.degree_type not in grouped:
            grouped[gs.degree_type] = []
        grouped[gs.degree_type].append(gs)
    
    return render_template('settings/grading.html',
                           grouped_grading=grouped,
                           degree_types=Config.DEGREE_TYPES)


@settings_bp.route('/grading/<degree_type>/edit', methods=['GET', 'POST'])
@login_required
@admin_or_hod_required
def edit_grading(degree_type):
    """Edit grading system for a degree type"""
    if degree_type not in Config.DEGREE_TYPES:
        flash('Invalid degree type.', 'danger')
        return redirect(url_for('settings.grading'))
    
    grades = GradingSystem.query.filter_by(degree_type=degree_type).order_by(
        GradingSystem.min_score.desc()
    ).all()
    
    if request.method == 'POST':
        # Get form data as lists
        grade_letters = request.form.getlist('grade[]')
        min_scores = request.form.getlist('min_score[]')
        max_scores = request.form.getlist('max_score[]')
        grade_points = request.form.getlist('grade_point[]')
        descriptions = request.form.getlist('description[]')
        
        # Process each grade
        for i, grade_letter in enumerate(grade_letters):
            # Find or create grade entry
            grade_obj = next((g for g in grades if g.grade == grade_letter), None)
            if grade_obj is None:
                grade_obj = GradingSystem(degree_type=degree_type, grade=grade_letter)
                db.session.add(grade_obj)
            
            # Update values
            grade_obj.min_score = int(min_scores[i])
            grade_obj.max_score = int(max_scores[i])
            grade_obj.grade_point = int(float(grade_points[i]))
            grade_obj.description = descriptions[i] if i < len(descriptions) else None
        
        db.session.commit()
        flash(f'Grading system for {degree_type} updated successfully.', 'success')
        return redirect(url_for('settings.grading'))
    
    # Convert grades list to dictionary for template
    grading_data = {g.grade: g for g in grades}
    
    return render_template('settings/edit_grading.html',
                           degree_type=degree_type,
                           grading_data=grading_data)


@settings_bp.route('/logo', methods=['GET', 'POST'])
@login_required
@admin_or_hod_required
def logo():
    """Manage university logo"""
    from flask import current_app
    
    logo_path = os.path.join(current_app.config['LOGO_FOLDER'], 'university_logo.jpg')
    logo_exists = os.path.exists(logo_path)
    
    if request.method == 'POST':
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                # Validate file type
                allowed = Config.ALLOWED_IMAGE_EXTENSIONS
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed:
                    # Save as PNG
                    file.save(logo_path)
                    flash('University logo uploaded successfully.', 'success')
                else:
                    flash('Invalid file type. Please upload PNG, JPG, or GIF.', 'danger')
        
        return redirect(url_for('settings.logo'))
    
    return render_template('settings/logo.html', logo_exists=logo_exists)


@settings_bp.route('/logo/delete', methods=['POST'])
@login_required
@admin_or_hod_required
def delete_logo():
    """Delete custom logo"""
    from flask import current_app
    
    logo_path = os.path.join(current_app.config['LOGO_FOLDER'], 'university_logo.jpg')
    if os.path.exists(logo_path):
        os.remove(logo_path)
        flash('Logo removed. Default logo will be used.', 'success')
    
    return redirect(url_for('settings.logo'))


@settings_bp.route('/system')
@login_required
@admin_or_hod_required
def system():
    """System settings"""
    settings = {s.key: s.value for s in SystemSetting.query.all()}
    
    return render_template('settings/system.html', settings=settings)


@settings_bp.route('/system/update', methods=['POST'])
@login_required
@admin_or_hod_required
def update_system():
    """Update system settings"""
    keys = ['university_name', 'faculty_name', 'department_name']
    
    for key in keys:
        value = request.form.get(key, '').strip()
        setting = SystemSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            db.session.add(setting)
    
    db.session.commit()
    flash('System settings updated.', 'success')
    return redirect(url_for('settings.system'))
