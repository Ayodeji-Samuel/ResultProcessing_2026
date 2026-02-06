"""
Database migration script to add new features:
1. Add 'description' field to grading_systems table
2. Add 'gender' field to students table
3. Create result_alterations table for tracking result changes
4. Update User role to support 'admin' role

Run this script to update the database schema.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
import os

# Create a minimal app for migration
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'results.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_table_exists(table_name):
    """Check if a table exists"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()

def migrate_database():
    """Run database migrations"""
    
    with app.app_context():
        print("Starting database migration...")
        
        # 1. Add description field to grading_systems
        if not check_column_exists('grading_systems', 'description'):
            print("Adding 'description' column to grading_systems table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE grading_systems ADD COLUMN description VARCHAR(64)'))
                conn.commit()
            print("✓ Added 'description' column to grading_systems")
        else:
            print("✓ 'description' column already exists in grading_systems")
        
        # 2. Add gender field to students
        if not check_column_exists('students', 'gender'):
            print("Adding 'gender' column to students table...")
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE students ADD COLUMN gender VARCHAR(1)'))
                conn.commit()
            print("✓ Added 'gender' column to students")
        else:
            print("✓ 'gender' column already exists in students")
        
        # 3. Create result_alterations table
        if not check_table_exists('result_alterations'):
            print("Creating result_alterations table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE result_alterations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        result_id INTEGER NOT NULL,
                        student_matric VARCHAR(20) NOT NULL,
                        student_name VARCHAR(256),
                        course_code VARCHAR(10) NOT NULL,
                        course_title VARCHAR(128),
                        session_name VARCHAR(20),
                        altered_by_id INTEGER NOT NULL,
                        altered_by_name VARCHAR(128),
                        altered_by_role VARCHAR(20),
                        alteration_type VARCHAR(20) NOT NULL,
                        old_ca_score FLOAT,
                        new_ca_score FLOAT,
                        old_exam_score FLOAT,
                        new_exam_score FLOAT,
                        old_total_score FLOAT,
                        new_total_score FLOAT,
                        old_grade VARCHAR(2),
                        new_grade VARCHAR(2),
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(512),
                        device_type VARCHAR(32),
                        browser VARCHAR(64),
                        operating_system VARCHAR(64),
                        device_username VARCHAR(128),
                        location VARCHAR(128),
                        reason TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (result_id) REFERENCES results(id),
                        FOREIGN KEY (altered_by_id) REFERENCES users(id)
                    )
                """))
                conn.commit()
            print("✓ Created result_alterations table")
        else:
            print("✓ result_alterations table already exists")
        
        # 4. Update grading descriptions with default values
        print("Updating grading system descriptions with defaults...")
        grade_descriptions = {
            'A': 'Excellent',
            'B': 'Very Good',
            'C': 'Good',
            'D': 'Fair',
            'E': 'Pass',
            'F': 'Fail'
        }
        
        with db.engine.connect() as conn:
            for grade, desc in grade_descriptions.items():
                conn.execute(text("""
                    UPDATE grading_systems 
                    SET description = :desc 
                    WHERE grade = :grade AND (description IS NULL OR description = '')
                """), {'desc': desc, 'grade': grade})
            conn.commit()
        
        print("✓ Updated grading system descriptions")
        
        print("\n" + "="*60)
        print("Database migration completed successfully!")
        print("="*60)
        print("\nNew features added:")
        print("1. ✓ Grading system descriptions")
        print("2. ✓ Student gender field (for PDF Miss prefix)")
        print("3. ✓ Result alteration tracking table")
        print("4. ✓ Support for Admin role (use existing user table)")
        print("\nNotes:")
        print("- To create an Admin user, update a user's role to 'admin' in the database")
        print("- Admin has complete system access including HoD password reset")
        print("- Result alterations are now tracked for Admin oversight")
        print("- Female students will have '(Miss)' prefix in PDF reports")

if __name__ == '__main__':
    migrate_database()
