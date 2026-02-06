from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp, Optional
from app.models import User


class LoginForm(FlaskForm):
    """Login form - username is university email"""
    username = StringField('University Email', validators=[
        DataRequired(message='University email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form (HoD only) - No self-registration allowed"""
    username = StringField('University Email (Username)', validators=[
        DataRequired(message='University email is required'),
        Email(message='Please enter a valid university email address')
    ])
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required'),
        Length(min=2, max=128, message='Full name must be between 2 and 128 characters')
    ])
    role = SelectField('Role', choices=[
        ('lecturer', 'Lecturer'),
        ('level_adviser', 'Level Adviser'),
        ('hod', 'Head of Department')
    ])
    program = SelectField('Program', choices=[])
    level = SelectField('Level', choices=[
        ('', 'Select Level'),
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level')
    ])
    submit = SubmitField('Create User Account')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.lower().strip()).first()
        if user:
            raise ValidationError('This email is already registered.')


class ForceChangePasswordForm(FlaskForm):
    """Force change password form for first login"""
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
               message='Password must contain uppercase, lowercase, number and special character (@$!%*?&)')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Set New Password')


class ChangePasswordForm(FlaskForm):
    """Change password form"""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
               message='Password must contain uppercase, lowercase, number and special character (@$!%*?&)')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')


class EditUserForm(FlaskForm):
    """Edit user form (HoD only)"""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required'),
        Length(min=2, max=128)
    ])
    role = SelectField('Role', choices=[
        ('lecturer', 'Lecturer'),
        ('level_adviser', 'Level Adviser'),
        ('hod', 'Head of Department')
    ])
    program = SelectField('Program', choices=[])
    level = SelectField('Level', choices=[
        ('', 'Select Level'),
        ('100', '100 Level'),
        ('200', '200 Level'),
        ('300', '300 Level'),
        ('400', '400 Level')
    ])
    is_active = BooleanField('Active')
    submit = SubmitField('Update User')
