import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production-2026'
    # Database URI. By default we use SQLite for development, but the
    # connection string can be overridden via the DATABASE_URL environment
    # variable (ideally set in a .env file). For production it is expected that
    # a real database such as MySQL/PostgreSQL will be used, e.g.:
    #
    #   DATABASE_URL=mysql+mysqldb://user:password@host:port/dbname
    #
    # Note: the package mysqlclient must be installed for the mysqldb driver.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'results.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configurations
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    LOGO_FOLDER = os.path.join(basedir, 'app', 'static', 'logos')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv'}
    ALLOWED_PAST_RESULT_EXTENSIONS = {'csv', 'pdf'}  # PDF allowed for past results upload
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Matric Number Formats (Edo State University Iyamho)
    # FSC/CSC/xxxxxxxx  - Computer Science
    # FSC/CBS/xxxxxxxx  - Cybersecurity
    # FSC/SWE/xxxxxxxx  - Software Engineering
    # FSC/CSC/CV/xxxxxxxx - Conversion students (Computer Science)
    # FSC/CBS/CV/xxxxxxxx - Conversion students (Cybersecurity)
    # FSC/SWE/CV/xxxxxxxx - Conversion students (Software Engineering)
    # xxxxxxxxxx (10+ digit) - JAMB Registration Number (for new students without matric)
    MATRIC_PREFIXES = {
        'Computer Science': 'FSC/CSC/',
        'Cyber Security': 'FSC/CBS/',
        'Software Engineering': 'FSC/SWE/',
    }
    MATRIC_CONVERSION_SUFFIX = 'CV/'  # e.g. FSC/CSC/CV/xxxxxxxx
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # CSRF token doesn't expire
    
    # Security settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_TIME = timedelta(minutes=15)
    
    # University Information
    UNIVERSITY_NAME = "Edo State University Iyamho"
    FACULTY_NAME = "Faculty of Science"
    DEPARTMENT_NAME = "Computer Science"
    
    # Available Programs
    PROGRAMS = [
        ('Computer Science', 'BSc Computer Science'),
        ('Cyber Security', 'BSc Cybersecurity'),
        ('Software Engineering', 'BSc Software Engineering'),
        ('PGD Computer Science', 'PGD Computer Science'),
        ('MSc Computer Science', 'MSc Computer Science'),
        ('PhD Computer Science', 'PhD Computer Science'),
    ]
    
    # Available Levels
    LEVELS = [100, 200, 300, 400]
    
    # Semesters
    SEMESTERS = [
        (1, 'First Semester'),
        (2, 'Second Semester'),
    ]
    
    # Course Status
    COURSE_STATUS = [
        ('C', 'Compulsory'),
        ('R', 'Required'),
        ('E', 'Elective'),
    ]
    
    # Degree Types and their grading systems
    DEGREE_TYPES = ['BSc', 'PGD', 'MSc', 'PhD']
    
    # User Roles
    ROLES = [
        ('hod', 'Head of Department'),
        ('level_adviser', 'Level Adviser'),
        ('lecturer', 'Lecturer'),
    ]


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
