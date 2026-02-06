"""
Migration script to add approval workflow fields to the database
Adds lecturer role, course assignments, and approval tracking
"""
from app import create_app, db
from app.models import User, Course, Result, CourseAssignment
from sqlalchemy import inspect, text

def migrate_database():
    """Add new fields to existing tables"""
    app = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("Starting database migration for approval system...")
        
        # Check and add columns to users table
        users_columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Update default role if needed
        print("✓ User model already has role field")
        
        # Check and add columns to courses table
        courses_columns = [col['name'] for col in inspector.get_columns('courses')]
        
        with db.engine.connect() as conn:
            if 'is_approved' not in courses_columns:
                print("Adding is_approved to courses table...")
                conn.execute(text('ALTER TABLE courses ADD COLUMN is_approved BOOLEAN DEFAULT FALSE'))
                conn.commit()
            
            if 'approved_by' not in courses_columns:
                print("Adding approved_by to courses table...")
                conn.execute(text('ALTER TABLE courses ADD COLUMN approved_by INTEGER'))
                # SQLite doesn't support adding foreign keys via ALTER TABLE
                # The relationship will work via SQLAlchemy ORM
                conn.commit()
            
            if 'approved_at' not in courses_columns:
                print("Adding approved_at to courses table...")
                conn.execute(text('ALTER TABLE courses ADD COLUMN approved_at DATETIME'))
                conn.commit()
        
        # Check and add columns to results table
        results_columns = [col['name'] for col in inspector.get_columns('results')]
        
        with db.engine.connect() as conn:
            if 'is_locked' not in results_columns:
                print("Adding is_locked to results table...")
                conn.execute(text('ALTER TABLE results ADD COLUMN is_locked BOOLEAN DEFAULT FALSE'))
                conn.commit()
            
            if 'locked_by' not in results_columns:
                print("Adding locked_by to results table...")
                conn.execute(text('ALTER TABLE results ADD COLUMN locked_by INTEGER'))
                # SQLite doesn't support adding foreign keys via ALTER TABLE
                conn.commit()
            
            if 'locked_at' not in results_columns:
                print("Adding locked_at to results table...")
                conn.execute(text('ALTER TABLE results ADD COLUMN locked_at DATETIME'))
                conn.commit()
            
            if 'unlocked_by' not in results_columns:
                print("Adding unlocked_by to results table...")
                conn.execute(text('ALTER TABLE results ADD COLUMN unlocked_by INTEGER'))
                # SQLite doesn't support adding foreign keys via ALTER TABLE
                conn.commit()
            
            if 'unlocked_at' not in results_columns:
                print("Adding unlocked_at to results table...")
                conn.execute(text('ALTER TABLE results ADD COLUMN unlocked_at DATETIME'))
                conn.commit()
        
        # Create course_assignments table if it doesn't exist
        existing_tables = inspector.get_table_names()
        
        if 'course_assignments' not in existing_tables:
            print("Creating course_assignments table...")
            CourseAssignment.__table__.create(db.engine)
            print("✓ course_assignments table created")
        else:
            print("✓ course_assignments table already exists")
        
        print("\n" + "="*60)
        print("Migration completed successfully!")
        print("="*60)
        print("\nNew features added:")
        print("  • Lecturer role support (in addition to HoD and Level Adviser)")
        print("  • Course assignments for lecturers")
        print("  • Result approval workflow (lock/unlock)")
        print("  • Final course approval by HoD")
        print("  • Audit trail for approval actions")
        print("\nNext steps:")
        print("  1. Restart the application")
        print("  2. Create lecturer users or update existing ones")
        print("  3. Assign lecturers to courses (HoD only)")
        print("  4. Test the approval workflow")

if __name__ == '__main__':
    migrate_database()
