"""
Fix admin user credentials
"""
from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Find the admin user
    admin = User.query.filter_by(role='admin').first()
    
    if admin:
        print("="*60)
        print("Current Admin User:")
        print("="*60)
        print(f"ID: {admin.id}")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")
        print(f"Full Name: {admin.full_name}")
        print()
        
        # Fix the username
        if '/' in admin.username:
            print("⚠️  Username contains '/' character!")
            print(f"   Current: {admin.username}")
            print()
            
            new_username = input("Enter corrected username (or press Enter to keep): ").strip()
            
            if new_username:
                admin.username = new_username.lower()
                admin.email = new_username.lower()
                db.session.commit()
                print()
                print("✅ Username updated successfully!")
                print(f"   New Username: {admin.username}")
            else:
                print()
                print("ℹ️  Username unchanged. Use this to login:")
                print(f"   Username: {admin.username}")
        else:
            print("✅ Username looks good!")
            print(f"   Login with: {admin.username}")
        
        # Offer to reset password
        print()
        reset = input("Reset password? (yes/no): ").strip().lower()
        
        if reset == 'yes':
            import secrets
            import string
            
            chars = string.ascii_letters + string.digits + '@$!%*?&'
            temp_password = ''.join(secrets.choice(chars) for _ in range(12))
            temp_password = (secrets.choice(string.ascii_uppercase) +
                            secrets.choice(string.ascii_lowercase) +
                            secrets.choice(string.digits) +
                            secrets.choice('@$!%*?&') +
                            temp_password[:8])
            
            admin.set_password(temp_password)
            admin.must_change_password = True
            db.session.commit()
            
            print()
            print("="*60)
            print("✅ Password reset successfully!")
            print("="*60)
            print(f"Username: {admin.username}")
            print(f"New Temporary Password: {temp_password}")
            print("="*60)
            print("⚠️  Must change password on first login")
    else:
        print("❌ No admin user found!")
        print()
        print("Run: python create_admin.py to create one")
