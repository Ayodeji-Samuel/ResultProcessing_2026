#!/usr/bin/env python3
"""
Migration: add ``remarks`` column to the ``students`` table.

The column stores promotion/graduation status:
  - NULL           → normal student
  - 'Non-Graduating' → 400L student carried forward because of outstanding carryovers
  - 'Graduated'    → (informational; such rows are not normally created)

Run once on an existing database:
    python migrate_add_student_remarks.py

Safe to run multiple times — skips the ALTER if the column already exists.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text, inspect as sa_inspect


def run():
    app = create_app('default')
    with app.app_context():
        inspector = sa_inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('students')]

        if 'remarks' in columns:
            print('✅  Column students.remarks already exists — nothing to do.')
            return

        dialect = db.engine.dialect.name
        if dialect == 'sqlite':
            sql = 'ALTER TABLE students ADD COLUMN remarks VARCHAR(64)'
        else:
            # MySQL / PostgreSQL
            sql = 'ALTER TABLE students ADD COLUMN remarks VARCHAR(64) NULL'

        with db.engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

        print('✅  Column students.remarks added successfully.')


if __name__ == '__main__':
    run()
