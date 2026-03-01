"""Secure admin account management CLI.

Usage examples:
    python create_admin.py create --username admin@school.edu --full-name "System Admin" --generate-password
    python create_admin.py create --username admin@school.edu --full-name "System Admin" --password-env ADMIN_PASSWORD
    python create_admin.py promote --username user@school.edu
    python create_admin.py deactivate --username old-admin@school.edu
"""

import argparse
import getpass
import os
import re
import secrets
import string
import sys

from app import create_app, db
from app.models import User


PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{10,}$')


def normalize_username(value):
    return value.strip().lower()


def validate_password_strength(password):
    return bool(PASSWORD_PATTERN.match(password or ''))


def generate_strong_password(length=16):
    if length < 12:
        length = 12
    alphabet = string.ascii_letters + string.digits + '@$!%*?&'
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('@$!%*?&')
    ]
    remainder = [secrets.choice(alphabet) for _ in range(length - len(required))]
    password_chars = required + remainder
    secrets.SystemRandom().shuffle(password_chars)
    return ''.join(password_chars)


def resolve_password(args):
    provided_count = sum([
        bool(args.password),
        bool(args.password_env),
        bool(args.generate_password)
    ])
    if provided_count > 1:
        raise ValueError('Use only one of --password, --password-env, or --generate-password.')

    if args.password:
        password = args.password
        generated = False
    elif args.password_env:
        password = os.environ.get(args.password_env)
        if not password:
            raise ValueError(f'Environment variable {args.password_env} is empty or undefined.')
        generated = False
    elif args.generate_password:
        password = generate_strong_password()
        generated = True
    else:
        if not sys.stdin.isatty():
            raise ValueError('No interactive terminal available. Use --password-env or --generate-password.')
        first = getpass.getpass('Admin password: ')
        second = getpass.getpass('Confirm admin password: ')
        if first != second:
            raise ValueError('Passwords do not match.')
        password = first
        generated = False

    if not validate_password_strength(password):
        raise ValueError('Password must be at least 10 chars and include uppercase, lowercase, number, and @$!%*?&.')
    return password, generated


def require_bootstrap_token(token_value):
    expected = os.environ.get('ADMIN_BOOTSTRAP_TOKEN')
    if expected and token_value != expected:
        raise PermissionError('Invalid bootstrap token. Set --bootstrap-token to match ADMIN_BOOTSTRAP_TOKEN.')


def create_admin(args):
    require_bootstrap_token(args.bootstrap_token)
    username = normalize_username(args.username)
    password, generated = resolve_password(args)

    user = User.query.filter_by(username=username).first()
    created = False

    if user and user.role != 'admin' and not args.promote_existing:
        raise ValueError('User exists with non-admin role. Use --promote-existing to upgrade this account.')

    if not user:
        user = User(
            username=username,
            email=username,
            full_name=args.full_name.strip(),
            role='admin',
            is_active=True,
            must_change_password=not args.no_force_password_change,
            is_locked=False,
            failed_login_attempts=0,
            locked_until=None
        )
        db.session.add(user)
        created = True
    else:
        user.full_name = args.full_name.strip() or user.full_name
        user.role = 'admin'
        user.is_active = True
        user.is_locked = False
        user.failed_login_attempts = 0
        user.locked_until = None
        if not args.no_force_password_change:
            user.must_change_password = True

    user.set_password(password)
    db.session.commit()

    print('\n✅ Admin account ready')
    print(f'Username: {username}')
    print(f'Action: {"created" if created else "updated/promoted"}')
    print(f'Must change password on login: {user.must_change_password}')
    if generated:
        print(f'Temporary Password: {password}')
        print('⚠️ Save this password securely now; it will not be shown again.')


def promote_admin(args):
    require_bootstrap_token(args.bootstrap_token)
    username = normalize_username(args.username)
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ValueError('User not found. Use create command to create a new admin account.')

    old_role = user.role
    user.role = 'admin'
    user.is_active = True
    user.is_locked = False
    user.failed_login_attempts = 0
    user.locked_until = None
    db.session.commit()
    print(f'✅ Promoted {username} from {old_role} to admin.')


def deactivate_admin(args):
    require_bootstrap_token(args.bootstrap_token)
    username = normalize_username(args.username)
    user = User.query.filter_by(username=username, role='admin').first()
    if not user:
        raise ValueError('Admin user not found.')

    active_admins = User.query.filter_by(role='admin', is_active=True).count()
    if user.is_active and active_admins <= 1:
        raise ValueError('Cannot deactivate the last active admin account.')

    user.is_active = False
    db.session.commit()
    print(f'✅ Deactivated admin account: {username}')


def list_admins(_args):
    admins = User.query.filter_by(role='admin').order_by(User.created_at.desc()).all()
    if not admins:
        print('No admin accounts found.')
        return
    print('\nAdmin accounts:')
    for account in admins:
        print(f'- {account.username} | active={account.is_active} | must_change_password={account.must_change_password}')


def build_parser():
    parser = argparse.ArgumentParser(description='Secure admin account management tool')
    subparsers = parser.add_subparsers(dest='command', required=True)

    create_parser = subparsers.add_parser('create', help='Create or update an admin account')
    create_parser.add_argument('--username', required=True, help='Admin username/email')
    create_parser.add_argument('--full-name', required=True, help='Admin full name')
    create_parser.add_argument('--password', help='Admin password (avoid shell history; prefer --password-env)')
    create_parser.add_argument('--password-env', help='Environment variable containing admin password')
    create_parser.add_argument('--generate-password', action='store_true', help='Generate temporary password')
    create_parser.add_argument('--promote-existing', action='store_true', help='Promote an existing non-admin user')
    create_parser.add_argument('--no-force-password-change', action='store_true', help='Do not force first-login password change')
    create_parser.add_argument('--bootstrap-token', help='Bootstrap token (matches ADMIN_BOOTSTRAP_TOKEN when set)')

    promote_parser = subparsers.add_parser('promote', help='Promote existing user to admin')
    promote_parser.add_argument('--username', required=True, help='Existing username/email')
    promote_parser.add_argument('--bootstrap-token', help='Bootstrap token (matches ADMIN_BOOTSTRAP_TOKEN when set)')

    deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate an admin account')
    deactivate_parser.add_argument('--username', required=True, help='Admin username/email')
    deactivate_parser.add_argument('--bootstrap-token', help='Bootstrap token (matches ADMIN_BOOTSTRAP_TOKEN when set)')

    subparsers.add_parser('list', help='List current admin accounts')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    app = create_app(os.environ.get('FLASK_CONFIG', 'default'))
    with app.app_context():
        if args.command == 'create':
            create_admin(args)
        elif args.command == 'promote':
            promote_admin(args)
        elif args.command == 'deactivate':
            deactivate_admin(args)
        elif args.command == 'list':
            list_admins(args)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'❌ {exc}')
        raise SystemExit(1)
