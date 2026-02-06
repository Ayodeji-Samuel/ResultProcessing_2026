from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config
import os

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOGO_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.students import students_bp
    from app.routes.courses import courses_bp
    from app.routes.results import results_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default HoD (Head of Department) user if none exists
        from app.models import User, GradingSystem
        if not User.query.filter_by(role='hod').first():
            hod = User(
                username='hod@university.edu.ng',
                email='hod@university.edu.ng',
                full_name='Head of Department',
                role='hod',
                is_active=True,
                must_change_password=False  # HoD doesn't need to change on first login
            )
            hod.set_password('HoD@2026!')
            db.session.add(hod)
            db.session.commit()
            print("Default HoD account created!")
            print("Username: hod@university.edu.ng")
            print("Password: HoD@2026!")
        
        # Create default grading systems if none exist
        if not GradingSystem.query.first():
            default_grades = [
                # BSc Grading
                ('BSc', 'A', 70, 100, 5),
                ('BSc', 'B', 60, 69, 4),
                ('BSc', 'C', 50, 59, 3),
                ('BSc', 'D', 45, 49, 2),
                ('BSc', 'E', 40, 44, 1),
                ('BSc', 'F', 0, 39, 0),
                # PGD Grading
                ('PGD', 'A', 70, 100, 5),
                ('PGD', 'B', 60, 69, 4),
                ('PGD', 'C', 50, 59, 3),
                ('PGD', 'D', 45, 49, 2),
                ('PGD', 'E', 40, 44, 1),
                ('PGD', 'F', 0, 39, 0),
                # MSc Grading
                ('MSc', 'A', 70, 100, 5),
                ('MSc', 'B', 60, 69, 4),
                ('MSc', 'C', 50, 59, 3),
                ('MSc', 'D', 45, 49, 2),
                ('MSc', 'E', 40, 44, 1),
                ('MSc', 'F', 0, 39, 0),
                # PhD Grading
                ('PhD', 'A', 70, 100, 5),
                ('PhD', 'B', 60, 69, 4),
                ('PhD', 'C', 50, 59, 3),
                ('PhD', 'D', 45, 49, 2),
                ('PhD', 'E', 40, 44, 1),
                ('PhD', 'F', 0, 39, 0),
            ]
            for degree, grade, min_score, max_score, points in default_grades:
                gs = GradingSystem(
                    degree_type=degree,
                    grade=grade,
                    min_score=min_score,
                    max_score=max_score,
                    grade_point=points
                )
                db.session.add(gs)
            db.session.commit()
    
    return app
