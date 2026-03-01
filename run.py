#!/usr/bin/env python
"""Result Processing System - Application Entry Point."""

import os
from app import create_app, db
from app.models import AcademicSession, GradingSystem

# Create the Flask application
app = create_app(os.environ.get('FLASK_CONFIG', 'default'))


def initialize_database():
    """Initialize the database with default data."""
    with app.app_context():
        # Create all database tables
        db.create_all()
            
        # Check if academic session exists
        session = AcademicSession.query.first()
        if not session:
            print("Creating default academic session...")
            session = AcademicSession(
                session_name='2025/2026',
                is_current=True
            )
            db.session.add(session)
            
        # Check if grading system exists
        grading = GradingSystem.query.first()
        if not grading:
            print("Creating default grading system...")
            default_grades = [
                {'grade': 'A', 'min_score': 70, 'max_score': 100, 'grade_point': 5.0, 'description': 'Excellent'},
                {'grade': 'B', 'min_score': 60, 'max_score': 69, 'grade_point': 4.0, 'description': 'Very Good'},
                {'grade': 'C', 'min_score': 50, 'max_score': 59, 'grade_point': 3.0, 'description': 'Good'},
                {'grade': 'D', 'min_score': 45, 'max_score': 49, 'grade_point': 2.0, 'description': 'Fair'},
                {'grade': 'E', 'min_score': 40, 'max_score': 44, 'grade_point': 1.0, 'description': 'Pass'},
                {'grade': 'F', 'min_score': 0, 'max_score': 39, 'grade_point': 0.0, 'description': 'Fail'},
            ]
            
            for degree in ['BSc', 'PGD', 'MSc', 'PhD']:
                for g in default_grades:
                    grade = GradingSystem(
                        degree_type=degree,
                        grade=g['grade'],
                        min_score=g['min_score'],
                        max_score=g['max_score'],
                        grade_point=g['grade_point'],
                        description=g['description']
                    )
                    db.session.add(grade)
        
        db.session.commit()
        print("Database initialized successfully!")


if __name__ == '__main__':
    # Initialize database with default data
    initialize_database()
    
    # Print startup information
    print("\n" + "=" * 60)
    print("RESULT PROCESSING SYSTEM")
    print("=" * 60)
    print(f"\nServer starting at: http://127.0.0.1:5000")
    print(f"\nSecurity Features:")
    print(f"  - Account locks after 3 failed login attempts")
    print(f"  - Only HoD can create user accounts")
    print(f"  - Users must change password on first login")
    print(f"  - Full audit trail for HoD monitoring")
    print("=" * 60 + "\n")
    
    # Run the Flask development server
    app.run(
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=int(os.environ.get('FLASK_PORT', '5000')),
        debug=app.config.get('DEBUG', False)
    )
