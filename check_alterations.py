"""
Check the actual data in result_alterations table
"""
from app import create_app, db
from app.models import ResultAlteration

app = create_app()

with app.app_context():
    print("=" * 80)
    print("CHECKING RESULT ALTERATIONS IN DATABASE")
    print("=" * 80)
    
    alterations = ResultAlteration.query.order_by(ResultAlteration.created_at.desc()).limit(5).all()
    
    if not alterations:
        print("\n❌ No alterations found in database")
    else:
        print(f"\nFound {ResultAlteration.query.count()} total alterations")
        print("\nShowing latest 5 alterations:\n")
        
        for i, alt in enumerate(alterations, 1):
            print(f"\n{'='*80}")
            print(f"Alteration #{i} (ID: {alt.id})")
            print(f"{'='*80}")
            print(f"Student: {alt.student_name} ({alt.student_matric})")
            print(f"Course: {alt.course_code} - {alt.course_title}")
            print(f"Type: {alt.alteration_type}")
            print(f"Date: {alt.created_at}")
            print(f"\nDevice Information:")
            print(f"  IP Address: {alt.ip_address or '❌ NOT SET'}")
            print(f"  Device Type: {alt.device_type or '❌ NOT SET'}")
            print(f"  Browser: {alt.browser or '❌ NOT SET'}")
            print(f"  Operating System: {alt.operating_system or '❌ NOT SET'}")
            print(f"  Device Username: {alt.device_username or '❌ NOT SET'}")
            print(f"  Location: {alt.location or '❌ NOT SET'}")
            print(f"  Latitude: {alt.latitude if alt.latitude is not None else '❌ NOT SET'}")
            print(f"  Longitude: {alt.longitude if alt.longitude is not None else '❌ NOT SET'}")
            
            if alt.latitude and alt.longitude:
                print(f"  Google Maps: https://www.google.com/maps?q={alt.latitude},{alt.longitude}")
            
            print(f"\nUser Agent (first 100 chars):")
            print(f"  {(alt.user_agent[:100] if alt.user_agent else '❌ NOT SET')}")
    
    print(f"\n{'='*80}")
    print("CHECK COMPLETE")
    print(f"{'='*80}")
