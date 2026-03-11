"""
Migration: widen course_code column from VARCHAR(10) to VARCHAR(20).

Background
----------
Course codes such as 'EDSU-CSC219' (11 characters) exceed the original
VARCHAR(10) limit and caused a DataError on MySQL/MariaDB.  This migration
widens the column to VARCHAR(20) in both affected tables:

  * courses.course_code
  * result_alterations.course_code

The script is safe to run multiple times — it checks the current column width
before issuing any ALTER TABLE and skips tables/columns that are already wide
enough.  Works with SQLite (development) and MySQL/MariaDB (production).

Usage
-----
    python migrate_course_code_varchar20.py
"""

import os
from sqlalchemy import inspect, text
from app import create_app, db

app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


# ─── helpers ─────────────────────────────────────────────────────────────────

def _dialect():
    return db.engine.dialect.name  # 'sqlite', 'mysql', 'postgresql', …


def _current_length(inspector, table, column):
    """Return the current VARCHAR length for *column* in *table*, or None."""
    for col in inspector.get_columns(table):
        if col['name'] == column:
            t = col['type']
            # SQLAlchemy reflects max length as .length for VARCHAR types
            return getattr(t, 'length', None)
    return None


def _alter_varchar(conn, table, column, new_length, nullable):
    """Issue the correct ALTER TABLE syntax for the current dialect."""
    dialect = _dialect()
    null_clause = 'NULL' if nullable else 'NOT NULL'

    if dialect == 'sqlite':
        # SQLite doesn't support ALTER COLUMN — but since VARCHAR limits are
        # not enforced by SQLite anyway, the only thing that matters is that
        # the model definition is updated (already done).  Log and skip.
        print(f"  [SQLite] No DDL needed — SQLite ignores VARCHAR width limits.")
    elif dialect in ('mysql', 'mariadb'):
        conn.execute(text(
            f'ALTER TABLE `{table}` MODIFY COLUMN `{column}` VARCHAR({new_length}) {null_clause}'
        ))
        conn.commit()
    elif dialect == 'postgresql':
        conn.execute(text(
            f'ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR({new_length})'
        ))
        conn.commit()
    else:
        # Generic ANSI SQL — may not work on all engines
        conn.execute(text(
            f'ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR({new_length})'
        ))
        conn.commit()


# ─── migration ────────────────────────────────────────────────────────────────

TARGET_LENGTH = 20

COLUMNS_TO_WIDEN = [
    # (table_name, column_name, nullable)
    ('courses',            'course_code', False),
    ('result_alterations', 'course_code', False),
]


def migrate():
    with app.app_context():
        print(f"Migration: widen course_code to VARCHAR({TARGET_LENGTH})")
        print(f"Dialect : {_dialect()}")
        print()

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        with db.engine.connect() as conn:
            for table, column, nullable in COLUMNS_TO_WIDEN:
                if table not in existing_tables:
                    print(f"  [SKIP] Table '{table}' does not exist yet.")
                    continue

                current = _current_length(inspector, table, column)

                if current is None:
                    print(f"  [SKIP] Column '{table}.{column}' not found.")
                    continue

                if current is not None and current >= TARGET_LENGTH:
                    print(
                        f"  [OK]   {table}.{column} is already VARCHAR({current}) "
                        f"— no change needed."
                    )
                    continue

                print(
                    f"  [ALTER] {table}.{column}: VARCHAR({current}) → VARCHAR({TARGET_LENGTH}) …",
                    end=' ',
                    flush=True,
                )
                _alter_varchar(conn, table, column, TARGET_LENGTH, nullable)
                print("done.")

        print()
        print("Migration complete.")


if __name__ == '__main__':
    migrate()
