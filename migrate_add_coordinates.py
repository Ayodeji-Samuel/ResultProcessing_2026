"""
Database migration: Add latitude and longitude to ResultAlteration table
Run this script to add GPS coordinate tracking to result alterations
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Adding GPS Coordinates to Result Alterations")
    print("=" * 60)
    
    try:
        # Check if columns already exist
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('result_alterations')]
        
        needs_latitude = 'latitude' not in columns
        needs_longitude = 'longitude' not in columns
        
        if not needs_latitude and not needs_longitude:
            print("✓ Latitude and longitude columns already exist!")
            print("=" * 60)
            exit(0)
        
        # Add latitude column if needed
        if needs_latitude:
            print("Adding latitude column...")
            db.session.execute(text(
                "ALTER TABLE result_alterations ADD COLUMN latitude FLOAT"
            ))
            print("✓ Latitude column added")
        
        # Add longitude column if needed
        if needs_longitude:
            print("Adding longitude column...")
            db.session.execute(text(
                "ALTER TABLE result_alterations ADD COLUMN longitude FLOAT"
            ))
            print("✓ Longitude column added")
        
        db.session.commit()
        
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nThe result alteration system will now capture:")
        print("  ✓ Device Type (Desktop, Mobile, Tablet)")
        print("  ✓ Browser (with version)")
        print("  ✓ Operating System (with version)")
        print("  ✓ Location (City, Region, Country)")
        print("  ✓ GPS Coordinates (Latitude & Longitude) [NEW]")
        print("\nYou can view precise locations on Google Maps!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        db.session.rollback()
        print("\nIf you see an error about columns already existing, that's OK!")
        print("The migration has already been applied.")
