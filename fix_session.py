"""Fix current session"""
from app import create_app, db
from app.models import AcademicSession

app = create_app()

with app.app_context():
    print("Current sessions:")
    sessions = AcademicSession.query.all()
    for s in sessions:
        print(f"  {s.session_name} - Current: {s.is_current}")
    
    # Set 2025/2026 as current
    print("\nUpdating current session...")
    
    # Unset all current flags
    AcademicSession.query.update({AcademicSession.is_current: False})
    
    # Set 2025/2026 as current
    target = AcademicSession.query.filter_by(session_name='2025/2026').first()
    if target:
        target.is_current = True
        db.session.commit()
        print(f"✓ Set {target.session_name} as current session")
    else:
        print("✗ Session 2025/2026 not found")
    
    print("\nUpdated sessions:")
    sessions = AcademicSession.query.all()
    for s in sessions:
        print(f"  {s.session_name} - Current: {s.is_current}")
