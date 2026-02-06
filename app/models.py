from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)  # University email
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='lecturer')  # admin, hod, level_adviser, lecturer
    program = db.Column(db.String(64))  # Assigned program
    level = db.Column(db.Integer)  # Assigned level (100, 200, 300, 400)
    is_active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)  # Locked by HoD/Admin after 3 failed attempts
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    must_change_password = db.Column(db.Boolean, default=True)  # Force password change on first login
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))  # IP address of last login
    last_login_device = db.Column(db.String(256))  # User agent of last login
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # HoD/Admin who created this account
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_account_locked(self):
        """Check if account is locked (either by HoD/Admin or temporarily)"""
        if self.is_locked:
            return True
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def is_admin(self):
        """Check if user is Admin (highest level access)"""
        return self.role == 'admin'
    
    def is_hod(self):
        """Check if user is HoD (Head of Department)"""
        return self.role == 'hod'
    
    def is_level_adviser(self):
        """Check if user is Level Adviser"""
        return self.role == 'level_adviser'
    
    def is_lecturer(self):
        """Check if user is Lecturer (includes HoD and Level Adviser, but not Admin)"""
        return self.role in ['lecturer', 'level_adviser', 'hod']
    
    def can_approve_results(self):
        """Check if user can give final approval (HoD and Admin)"""
        return self.role in ['hod', 'admin']
    
    def can_access_result_alterations(self):
        """Check if user can view result alteration logs (Admin only)"""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'


class AcademicSession(db.Model):
    """Academic session/year"""
    __tablename__ = 'academic_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(20), unique=True, nullable=False)  # e.g., "2025/2026"
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='session', lazy='dynamic')
    results = db.relationship('Result', backref='session', lazy='dynamic')


class Student(db.Model):
    """Student records"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    matric_number = db.Column(db.String(20), nullable=False, index=True)
    surname = db.Column(db.String(64), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    other_names = db.Column(db.String(64))
    gender = db.Column(db.String(1))  # M or F
    program = db.Column(db.String(64), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 100, 200, 300, 400
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    results = db.relationship('Result', backref='student', lazy='dynamic')
    
    # Unique constraint for matric_number per session
    __table_args__ = (
        db.UniqueConstraint('matric_number', 'session_id', name='unique_matric_session'),
    )
    
    @property
    def full_name(self):
        """Returns full name with surname first"""
        names = [self.surname.upper()]
        if self.first_name:
            names.append(self.first_name.title())
        if self.other_names:
            names.append(self.other_names.title())
        return ' '.join(names)
    
    def __repr__(self):
        return f'<Student {self.matric_number}>'


class Course(db.Model):
    """Course information"""
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(10), nullable=False, index=True)
    course_title = db.Column(db.String(128), nullable=False)
    credit_unit = db.Column(db.Integer, nullable=False)
    semester = db.Column(db.Integer, nullable=False)  # 1 or 2
    level = db.Column(db.Integer, nullable=False)  # 100, 200, 300, 400
    program = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='C')  # C, R, E
    degree_type = db.Column(db.String(10), default='BSc')  # BSc, PGD, MSc, PhD
    is_active = db.Column(db.Boolean, default=True)
    is_approved = db.Column(db.Boolean, default=False)  # Final HoD approval
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # HoD who approved
    approved_at = db.Column(db.DateTime)  # When approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    results = db.relationship('Result', backref='course', lazy='dynamic')
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    # Unique constraint for course_code per program and level
    __table_args__ = (
        db.UniqueConstraint('course_code', 'program', 'level', name='unique_course_program_level'),
    )
    
    def __repr__(self):
        return f'<Course {self.course_code}>'


class CourseAssignment(db.Model):
    """Lecturer assignment to courses - for regular lecturers"""
    __tablename__ = 'course_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # HoD who assigned
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    lecturer = db.relationship('User', foreign_keys=[user_id], backref='course_assignments')
    course = db.relationship('Course', backref='assignments')
    session = db.relationship('AcademicSession', backref='course_assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', 'session_id', name='unique_lecturer_course_session'),
    )
    
    def __repr__(self):
        return f'<CourseAssignment User:{self.user_id} Course:{self.course_id}>'


class Result(db.Model):
    """Student results/scores"""
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    ca_score = db.Column(db.Float, nullable=False)  # Continuous Assessment (30%)
    exam_score = db.Column(db.Float, nullable=False)  # Exam score (70%)
    total_score = db.Column(db.Float, nullable=False)  # CA + Exam
    grade = db.Column(db.String(2), nullable=False)
    grade_point = db.Column(db.Integer, nullable=False)
    is_carryover = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)  # Locked after lecturer approval
    locked_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Lecturer who locked
    locked_at = db.Column(db.DateTime)  # When locked
    unlocked_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # HoD who unlocked
    unlocked_at = db.Column(db.DateTime)  # When unlocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_id', 'session_id', name='unique_student_course_session'),
    )
    
    def __repr__(self):
        return f'<Result {self.student_id} - {self.course_id}>'


class GradingSystem(db.Model):
    """Configurable grading system for different degree types"""
    __tablename__ = 'grading_systems'
    
    id = db.Column(db.Integer, primary_key=True)
    degree_type = db.Column(db.String(10), nullable=False)  # BSc, PGD, MSc, PhD
    grade = db.Column(db.String(2), nullable=False)  # A, B, C, D, E, F
    min_score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    grade_point = db.Column(db.Integer, nullable=False)  # 5, 4, 3, 2, 1, 0
    description = db.Column(db.String(64))  # Excellent, Very Good, Good, Fair, Pass, Fail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('degree_type', 'grade', name='unique_degree_grade'),
    )
    
    def __repr__(self):
        return f'<GradingSystem {self.degree_type} - {self.grade}>'


class SystemSetting(db.Model):
    """System-wide settings"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.String(256))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSetting {self.key}>'


class Carryover(db.Model):
    """Track carryover courses for students across sessions/levels"""
    __tablename__ = 'carryovers'
    
    id = db.Column(db.Integer, primary_key=True)
    student_matric = db.Column(db.String(20), nullable=False, index=True)  # Track by matric (persists across sessions)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    original_session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)  # When failed
    original_level = db.Column(db.Integer, nullable=False)  # Level when failed
    is_cleared = db.Column(db.Boolean, default=False)  # Cleared when passed
    cleared_session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'))  # When cleared
    cleared_result_id = db.Column(db.Integer, db.ForeignKey('results.id'))  # Result that cleared it
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', backref='carryovers')
    original_session = db.relationship('AcademicSession', foreign_keys=[original_session_id])
    cleared_session = db.relationship('AcademicSession', foreign_keys=[cleared_session_id])
    cleared_result = db.relationship('Result', backref='cleared_carryover')
    
    # Unique constraint to prevent duplicate carryover entries
    __table_args__ = (
        db.UniqueConstraint('student_matric', 'course_id', 'original_session_id', name='unique_carryover'),
    )
    
    def __repr__(self):
        return f'<Carryover {self.student_matric} - {self.course_id}>'


class StudentAcademicHistory(db.Model):
    """Track student progression across sessions and levels"""
    __tablename__ = 'student_academic_history'
    
    id = db.Column(db.Integer, primary_key=True)
    student_matric = db.Column(db.String(20), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('academic_sessions.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    program = db.Column(db.String(64), nullable=False)
    first_semester_gpa = db.Column(db.Float, default=0.0)
    second_semester_gpa = db.Column(db.Float, default=0.0)
    cgpa = db.Column(db.Float, default=0.0)
    total_units_registered = db.Column(db.Integer, default=0)
    total_units_passed = db.Column(db.Integer, default=0)
    total_units_failed = db.Column(db.Integer, default=0)
    remarks = db.Column(db.String(128))  # Pass, Probation, Withdrawal, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = db.relationship('AcademicSession', backref='academic_histories')
    
    __table_args__ = (
        db.UniqueConstraint('student_matric', 'session_id', name='unique_student_session_history'),
    )
    
    def __repr__(self):
        return f'<StudentAcademicHistory {self.student_matric} - {self.session_id}>'


class UploadLog(db.Model):
    """Log of all CSV uploads"""
    __tablename__ = 'upload_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_type = db.Column(db.String(20), nullable=False)  # students, results
    filename = db.Column(db.String(256), nullable=False)
    records_processed = db.Column(db.Integer, default=0)
    records_failed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='pending')  # pending, success, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='uploads')
    
    def __repr__(self):
        return f'<UploadLog {self.id}>'


class AuditLog(db.Model):
    """Comprehensive audit trail for security monitoring - HoD only access"""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(120))  # Store username in case user is deleted
    action = db.Column(db.String(64), nullable=False)  # LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.
    action_category = db.Column(db.String(32))  # AUTH, STUDENT, COURSE, RESULT, SETTINGS, etc.
    resource = db.Column(db.String(64))  # Table/Resource name
    resource_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)  # JSON of old values for updates
    new_values = db.Column(db.Text)  # JSON of new values for updates
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))  # Full user agent string
    device_type = db.Column(db.String(32))  # desktop, mobile, tablet
    browser = db.Column(db.String(64))
    operating_system = db.Column(db.String(64))
    location = db.Column(db.String(128))  # City/Country if available
    session_id = db.Column(db.String(64))  # Track session
    status = db.Column(db.String(16), default='success')  # success, failed, blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.id} - {self.action}>'


class ResultAlteration(db.Model):
    """Track all result alterations for admin oversight"""
    __tablename__ = 'result_alterations'
    
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id'), nullable=False)
    student_matric = db.Column(db.String(20), nullable=False, index=True)
    student_name = db.Column(db.String(256))
    course_code = db.Column(db.String(10), nullable=False)
    course_title = db.Column(db.String(128))
    session_name = db.Column(db.String(20))
    
    # Alteration details
    altered_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    altered_by_name = db.Column(db.String(128))
    altered_by_role = db.Column(db.String(20))
    alteration_type = db.Column(db.String(20), nullable=False)  # CREATE, UPDATE, DELETE
    
    # Old and new values
    old_ca_score = db.Column(db.Float)
    new_ca_score = db.Column(db.Float)
    old_exam_score = db.Column(db.Float)
    new_exam_score = db.Column(db.Float)
    old_total_score = db.Column(db.Float)
    new_total_score = db.Column(db.Float)
    old_grade = db.Column(db.String(2))
    new_grade = db.Column(db.String(2))
    
    # Device and location information
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(512))
    device_type = db.Column(db.String(32))
    browser = db.Column(db.String(64))
    operating_system = db.Column(db.String(64))
    device_username = db.Column(db.String(128))  # Computer username from request headers
    location = db.Column(db.String(128))
    latitude = db.Column(db.Float)  # GPS latitude coordinate
    longitude = db.Column(db.Float)  # GPS longitude coordinate
    
    # Reason for alteration
    reason = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    result = db.relationship('Result', backref='alterations')
    altered_by = db.relationship('User', foreign_keys=[altered_by_id])
    
    def __repr__(self):
        return f'<ResultAlteration {self.id} - {self.student_matric} - {self.course_code}>'
