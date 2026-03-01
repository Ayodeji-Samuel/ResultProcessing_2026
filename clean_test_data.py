"""Clean test/demo data before uploading real production data.

Safe defaults:
- Dry-run by default (no changes)
- Preserves grading/system settings
- Keeps active admin accounts by default

Examples:
    python clean_test_data.py --dry-run
    python clean_test_data.py --execute
    python clean_test_data.py --execute --delete-non-admin-users
    python clean_test_data.py --execute --delete-all-users
"""

import argparse
import os
from pathlib import Path

from app import create_app, db
from app.models import (
    AcademicSession,
    AttendanceToken,
    AuditLog,
    Carryover,
    Course,
    CourseAssignment,
    KnownAttendee,
    MeetingAttendee,
    MeetingMinutes,
    Result,
    ResultAlteration,
    Student,
    StudentAcademicHistory,
    UploadLog,
    User,
)


def count_rows(model):
    return model.query.count()


def clear_upload_files(upload_root):
    removed = 0
    upload_path = Path(upload_root)
    if not upload_path.exists():
        return removed

    for file_path in upload_path.rglob('*'):
        if file_path.is_file():
            file_path.unlink()
            removed += 1
    return removed


def print_summary():
    print('\nCurrent row counts:')
    print(f'  Users: {count_rows(User)}')
    print(f'  Academic Sessions: {count_rows(AcademicSession)}')
    print(f'  Students: {count_rows(Student)}')
    print(f'  Courses: {count_rows(Course)}')
    print(f'  Results: {count_rows(Result)}')
    print(f'  Result Alterations: {count_rows(ResultAlteration)}')
    print(f'  Audit Logs: {count_rows(AuditLog)}')
    print(f'  Upload Logs: {count_rows(UploadLog)}')
    print(f'  Course Assignments: {count_rows(CourseAssignment)}')
    print(f'  Carryovers: {count_rows(Carryover)}')
    print(f'  Student History: {count_rows(StudentAcademicHistory)}')
    print(f'  Minutes: {count_rows(MeetingMinutes)}')
    print(f'  Attendance Tokens: {count_rows(AttendanceToken)}')
    print(f'  Meeting Attendees: {count_rows(MeetingAttendee)}')
    print(f'  Known Attendees: {count_rows(KnownAttendee)}')


def execute_cleanup(delete_non_admin_users=False, delete_all_users=False):
    # Delete in FK-safe order
    ResultAlteration.query.delete(synchronize_session=False)
    AuditLog.query.delete(synchronize_session=False)
    UploadLog.query.delete(synchronize_session=False)

    MeetingAttendee.query.delete(synchronize_session=False)
    AttendanceToken.query.delete(synchronize_session=False)
    MeetingMinutes.query.delete(synchronize_session=False)
    KnownAttendee.query.delete(synchronize_session=False)

    Carryover.query.delete(synchronize_session=False)
    StudentAcademicHistory.query.delete(synchronize_session=False)
    Result.query.delete(synchronize_session=False)
    CourseAssignment.query.delete(synchronize_session=False)

    Student.query.delete(synchronize_session=False)
    Course.query.delete(synchronize_session=False)

    # Sessions can be considered test data too; recreate one baseline current session
    current_session = (
        db.session.query(AcademicSession.session_name)
        .filter(AcademicSession.is_current.is_(True))
        .first()
    )
    session_name = current_session[0] if current_session else '2026/2027'
    AcademicSession.query.delete(synchronize_session=False)
    db.session.add(AcademicSession(session_name=session_name, is_current=True))

    if delete_all_users:
        User.query.delete(synchronize_session=False)
    elif delete_non_admin_users:
        User.query.filter(User.role != 'admin').delete(synchronize_session=False)

    db.session.commit()


def parse_args():
    parser = argparse.ArgumentParser(description='Clean test/demo data from the database')
    parser.add_argument('--dry-run', action='store_true', help='Show what will be deleted (default behavior if --execute is omitted)')
    parser.add_argument('--execute', action='store_true', help='Actually perform deletion')
    parser.add_argument('--delete-non-admin-users', action='store_true', help='Delete all users except admins')
    parser.add_argument('--delete-all-users', action='store_true', help='Delete all users including admins')
    parser.add_argument('--clean-uploads', action='store_true', help='Delete files from uploads folder')
    return parser.parse_args()


def main():
    args = parse_args()
    app = create_app(os.environ.get('FLASK_CONFIG', 'default'))

    with app.app_context():
        print_summary()

        if not args.execute:
            print('\nDry-run complete. No data was deleted.')
            print('Run with --execute to apply cleanup.')
            return

        if args.delete_all_users and args.delete_non_admin_users:
            raise ValueError('Use either --delete-all-users or --delete-non-admin-users, not both.')

        execute_cleanup(
            delete_non_admin_users=args.delete_non_admin_users,
            delete_all_users=args.delete_all_users,
        )

        removed_files = 0
        if args.clean_uploads:
            removed_files = clear_upload_files(app.config['UPLOAD_FOLDER'])

        print('\n✅ Cleanup completed successfully.')
        if args.clean_uploads:
            print(f'Uploads cleaned: {removed_files} file(s) removed.')
        print_summary()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'❌ {exc}')
        raise SystemExit(1)
