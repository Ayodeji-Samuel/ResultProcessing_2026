"""
Create or promote a user to Admin role
"""
from app import create_app, db
from app.models import User

def create_admin():
    app = create_app()
    
    with app.app_context():
        print("="*60)
        print("Admin User Management")
        print("="*60)
        print()
        
        # List existing users
        users = User.query.all()
        print("Existing Users:")
        print("-" * 60)
        for u in users:
            print(f"ID: {u.id:3} | Username: {u.username:30} | Role: {u.role:15} | Name: {u.full_name}")
        print()
        
        if not users:
            print("No users found in the database!")
            print("Please create a user through the application first.")
            return
        
        # Ask which user to promote to admin
        print("Choose an option:")
        print("1. Promote existing user to Admin")
        print("2. Create new Admin user")
        print()
        
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == '1':
            user_id = input("Enter user ID to promote to Admin: ").strip()
            try:
                user_id = int(user_id)
                user = User.query.get(user_id)
                
                if not user:
                    print(f"❌ User with ID {user_id} not found!")
                    return
                
                print()
                print(f"Promoting user: {user.full_name} ({user.username})")
                print(f"Current role: {user.role}")
                print()
                confirm = input("Confirm promotion to Admin? (yes/no): ").strip().lower()
                
                if confirm == 'yes':
                    old_role = user.role
                    user.role = 'admin'
                    db.session.commit()
                    print()
                    print("✅ User successfully promoted to Admin!")
                    print(f"   {user.full_name} ({user.username})")
                    print(f"   Role changed from '{old_role}' to 'admin'")
                    print()
                    print("The user now has:")
                    print("   ✓ Complete system access")
                    print("   ✓ Can reset HoD passwords")
                    print("   ✓ Access to result alteration logs")
                    print("   ✓ All HoD permissions")
                else:
                    print("❌ Promotion cancelled")
                    
            except ValueError:
                print("❌ Invalid user ID!")
                
        elif choice == '2':
            print()
            print("Create New Admin User")
            print("-" * 60)
            username = input("Email/Username: ").strip().lower()
            full_name = input("Full Name: ").strip()
            
            # Check if username exists
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"❌ User with username '{username}' already exists!")
                return
            
            # Generate temporary password
            import secrets
            import string
            chars = string.ascii_letters + string.digits + '@$!%*?&'
            temp_password = ''.join(secrets.choice(chars) for _ in range(12))
            # Ensure it has all required character types
            temp_password = (secrets.choice(string.ascii_uppercase) +
                            secrets.choice(string.ascii_lowercase) +
                            secrets.choice(string.digits) +
                            secrets.choice('@$!%*?&') +
                            temp_password[:8])
            
            # Create admin user
            admin = User(
                username=username,
                email=username,
                full_name=full_name,
                role='admin',
                is_active=True,
                must_change_password=True
            )
            admin.set_password(temp_password)
            
            db.session.add(admin)
            db.session.commit()
            
            print()
            print("✅ Admin user created successfully!")
            print()
            print("=" * 60)
            print("IMPORTANT - Save these credentials:")
            print("=" * 60)
            print(f"Username: {username}")
            print(f"Temporary Password: {temp_password}")
            print("=" * 60)
            print()
            print("⚠️  The user MUST change this password on first login.")
            print()
            
        else:
            print("❌ Invalid choice!")

if __name__ == '__main__':
    create_admin()
