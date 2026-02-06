from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.students import students_bp
from app.routes.courses import courses_bp
from app.routes.results import results_bp
from app.routes.reports import reports_bp
from app.routes.settings import settings_bp

__all__ = [
    'auth_bp',
    'dashboard_bp',
    'students_bp',
    'courses_bp',
    'results_bp',
    'reports_bp',
    'settings_bp'
]
