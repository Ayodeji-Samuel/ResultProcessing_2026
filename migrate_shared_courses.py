"""
Database migration: create the course_programs table for shared-course support.

A course (identified by course_code + level) can now be shared across multiple
programs.  The extra programs beyond the course's primary `program` field are
stored in this table.

Run once:
    python migrate_shared_courses.py
"""

import os
from sqlalchemy import inspect, text
from app import create_app, db

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


def check_table_exists(table_name):
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def migrate():
    with app.app_context():
        print("Starting migration: course_programs table...")

        if check_table_exists('course_programs'):
            print("✓ Table 'course_programs' already exists — skipping creation.")
        else:
            print("Creating 'course_programs' table...")
            with db.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE course_programs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        course_id INTEGER NOT NULL REFERENCES courses(id),
                        program VARCHAR(64) NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (course_id, program)
                    )
                """))
                conn.commit()
            print("✓ Table 'course_programs' created successfully.")

        print("\nMigration complete.")


if __name__ == '__main__':
    migrate()
