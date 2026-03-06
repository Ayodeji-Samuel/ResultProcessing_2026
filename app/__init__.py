from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config
import mimetypes
import os
import time

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# ── Register font MIME types that may be absent on minimal Linux installations
# (DigitalOcean, Render, Railway …) so that remixicon and other web-font files
# are served with the correct Content-Type header.  Browsers strictly validate
# font MIME types and silently discard resources served as octet-stream.
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/woff',  '.woff')
mimetypes.add_type('font/ttf',   '.ttf')
mimetypes.add_type('font/otf',   '.otf')


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
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
    from app.routes.minutes import minutes_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(results_bp, url_prefix='/results')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(minutes_bp, url_prefix='/minutes')

    # Landing page — root URL (public)
    from flask import render_template, redirect, url_for

    @app.route('/')
    def landing():
        return render_template('landing.html')

    @app.route('/landing')
    def landing_redirect():
        return redirect(url_for('landing'), 301)

    # Create database tables.
    # On local MySQL (e.g. Laragon) a concurrent DDL statement on an existing
    # table causes error 1684 during db.create_all()'s table inspection.
    # To avoid this, we check whether all tables already exist first and only
    # call create_all() when genuinely needed (e.g. first-run / new table added).
    with app.app_context():
        from sqlalchemy import inspect as _sa_inspect
        _inspector = _sa_inspect(db.engine)
        _existing = set(_inspector.get_table_names())
        _model_tables = set(db.metadata.tables.keys())
        _missing = _model_tables - _existing

        if _missing:
            # Some tables are absent — create them (retry on transient error 1684)
            for _attempt in range(6):
                try:
                    db.create_all()
                    break
                except Exception as _e:
                    if '1684' in str(_e) and _attempt < 5:
                        time.sleep(3)
                        continue
                    raise
        # else: all tables exist — skip create_all entirely (avoids error 1684)
        
        from app.models import GradingSystem
        
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
                ('MSc', 'F', 0, 49, 0),
                # PhD Grading
                ('PhD', 'A', 70, 100, 5),
                ('PhD', 'B', 60, 69, 4),
                ('PhD', 'F', 0, 59, 0),
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
