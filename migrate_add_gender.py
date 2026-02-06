"""
Migration script to add gender field to students table
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Adding gender column to students table...")
    
    try:
        # Check if column already exists
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM pragma_table_info('students') 
            WHERE name='gender'
        """))
        column_exists = result.scalar() > 0
        
        if column_exists:
            print("✓ Gender column already exists!")
        else:
            # Add gender column (M or F)
            db.session.execute(text("""
                ALTER TABLE students 
                ADD COLUMN gender VARCHAR(1)
            """))
            db.session.commit()
            print("✓ Gender column added successfully!")
        
        # Show current schema
        print("\nCurrent students table schema:")
        result = db.session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='students'"))
        schema = result.scalar()
        print(schema)
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        db.session.rollback()
