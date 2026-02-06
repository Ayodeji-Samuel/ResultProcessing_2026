# Approval Workflow System - Implementation Guide

## Overview
This document describes the comprehensive security and integrity features added to the Result Processing System, including the approval workflow, role-based access control, and modern UI enhancements.

## New Features Implemented

### 1. Enhanced User Roles
**Three distinct roles with hierarchical permissions:**

- **HoD (Head of Department)** - Full system access
  - Assign lecturers to courses
  - Unlock approved results
  - Give final approval after departmental board meetings
  - Access all levels and programs
  
- **Level Adviser** - Level and program-specific access
  - Upload and manage results for assigned level/program
  - Approve results for their courses
  - Cannot unlock results once approved
  
- **Lecturer** - Course-specific access
  - Must be assigned to specific courses by HoD
  - Upload and manage results only for assigned courses
  - Approve results (locks them from editing)
  - Cannot unlock own approved results

### 2. Course Assignment System
**HoD can assign lecturers to specific courses:**
- New `CourseAssignment` model tracks lecturer-course relationships
- One course can have multiple lecturers assigned
- Assignments are session-specific
- HoD can add/remove assignments anytime
- View assignments from course management interface

### 3. Result Approval Workflow

#### Phase 1: Draft Results
- Lecturers upload results via CSV or manual entry
- Results are editable by the lecturer
- Status: **DRAFT** (Blue badge)

#### Phase 2: Lecturer Approval
- Lecturer clicks "Approve Results" button
- All results for that course are **LOCKED**
- Locked results cannot be edited/deleted by lecturer
- Status: **LOCKED** (Amber badge)
- Only HoD can unlock if corrections needed

#### Phase 3: HoD Unlock (if needed)
- HoD can unlock approved results
- Allows lecturer to make corrections
- Audit trail maintained for unlock actions
- Results return to draft state

#### Phase 4: Final Approval
- After departmental board meeting
- HoD gives "Final Approval" to course
- Signifies official approval of all results
- Status: **OFFICIALLY APPROVED** (Green badge)
- Results are permanently locked

## Database Schema Changes

### New Tables

#### `course_assignments`
```sql
- id (PK)
- user_id (FK -> users.id)
- course_id (FK -> courses.id)
- session_id (FK -> academic_sessions.id)
- assigned_by (FK -> users.id)
- assigned_at (DateTime)
- is_active (Boolean)
```

### Modified Tables

#### `users`
```sql
+ role: 'hod' | 'level_adviser' | 'lecturer' (default: 'lecturer')
```

#### `courses`
```sql
+ is_approved (Boolean, default: False)
+ approved_by (FK -> users.id)
+ approved_at (DateTime)
```

#### `results`
```sql
+ is_locked (Boolean, default: False)
+ locked_by (FK -> users.id)
+ locked_at (DateTime)
+ unlocked_by (FK -> users.id)
+ unlocked_at (DateTime)
```

## New Routes

### Results Management
- `POST /results/course/<id>/approve` - Lecturer approves their results
- `POST /results/course/<id>/unlock` - HoD unlocks results
- `POST /results/course/<id>/final-approve` - HoD gives final approval

### Course Assignments (HoD Only)
- `GET/POST /courses/<id>/assign-lecturer` - Assign lecturer to course
- `GET /courses/<id>/assignments` - View course assignments
- `POST /courses/assignment/<id>/remove` - Remove assignment

## Security Features

### 1. Access Control
- **Course-level access**: Lecturers can only access assigned courses
- **Level-based access**: Level Advisers restricted to their level
- **Lock enforcement**: Locked results protected from unauthorized changes
- **HoD override**: HoD can unlock and override any restriction

### 2. Audit Trail
All approval actions are logged:
- Lecturer approvals (APPROVE_RESULTS)
- HoD unlocks (UNLOCK_RESULTS)
- Final approvals (FINAL_APPROVE_COURSE)
- Each log includes: user, timestamp, IP, user agent, details

### 3. Validation Checks
- Cannot approve empty results
- Cannot delete/edit locked results (except HoD)
- Cannot upload to locked courses (except HoD)
- Final approval requires all results to be lecturer-approved

## UI/UX Enhancements

### 1. Status Banners
**Course view page displays:**
- Green banner: Final approval granted (with approver details)
- Amber banner: Results locked, awaiting HoD approval
- Blue banner: Draft results, pending approval

### 2. Action Buttons
- **Approve Results**: Blue button, locks all course results
- **Unlock Results**: Amber button (HoD only)
- **Give Final Approval**: Green button (HoD only, when all locked)
- Buttons auto-hide based on status and permissions

### 3. Visual Indicators
- **Lock icons** on locked result rows
- **Status badges** in results listing:
  - 🟢 Final Approved
  - 🟡 Locked
  - 🔵 Draft
- **Disabled buttons** for locked actions
- **Color-coded** permission indicators

### 4. Modern Design
- Gradient headers and cards
- Smooth transitions and hover effects
- Responsive layout
- Icon-rich interface (Remix Icons)
- Professional color scheme

## Migration Guide

### Step 1: Run Database Migration
```bash
python migrate_approval_system.py
```

This will:
- Add new columns to existing tables
- Create course_assignments table
- Preserve all existing data

### Step 2: Update Existing Users
```python
# Set user roles appropriately
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    # Set HoD
    hod = User.query.filter_by(username='hod@esui.edu.ng').first()
    if hod:
        hod.role = 'hod'
    
    # Set Level Advisers
    advisers = User.query.filter_by(role='level_adviser').all()
    # These already have correct role
    
    # Set Lecturers
    lecturers = User.query.filter(User.role.in_(['lecturer', None])).all()
    for lecturer in lecturers:
        lecturer.role = 'lecturer'
    
    db.session.commit()
```

### Step 3: Assign Lecturers to Courses
- Login as HoD
- Navigate to Courses page
- Click "Assign" button for each course
- Select lecturer(s) from dropdown
- Confirm assignment

### Step 4: Test Workflow
1. **As Lecturer**: Upload results, approve them
2. **As HoD**: View locked status, unlock if needed
3. **As HoD**: Give final approval after board meeting

## Workflow Example

### Scenario: End of Semester Result Processing

**Week 1-2: Result Upload**
- Lecturers upload their course results
- Edit and verify accuracy
- Results in DRAFT status

**Week 3: Lecturer Approval**
- Each lecturer approves their results
- Results become LOCKED
- No further edits possible

**Week 4: Corrections (if needed)**
- If errors found, HoD unlocks specific courses
- Lecturer makes corrections
- Re-approves results

**Week 5: Departmental Board Meeting**
- Board reviews all results
- Discusses borderline cases
- Makes final decisions

**After Board Meeting**
- HoD gives FINAL APPROVAL to all courses
- Results are officially approved
- System generates final transcripts

## Best Practices

### For Lecturers
1. Double-check all results before approving
2. Verify student matriculation numbers
3. Ensure grades match institutional policy
4. Don't approve until absolutely certain
5. Contact HoD if unlock needed

### For Level Advisers
1. Monitor all courses in your level
2. Coordinate with lecturers
3. Approve only after verification
4. Prepare summary reports for board

### For HoD
1. Assign lecturers at start of session
2. Monitor approval progress
3. Unlock only when necessary
4. Document unlock reasons
5. Give final approval only after board meeting
6. Review audit logs regularly

## Troubleshooting

### Issue: Lecturer can't see assigned course
**Solution**: Verify course assignment in system. HoD should check assignments page.

### Issue: Results still editable after approval
**Solution**: Check is_locked field in database. May need to re-approve.

### Issue: Can't unlock results
**Solution**: Only HoD can unlock. Verify user role is set to 'hod'.

### Issue: Final approval button not showing
**Solution**: Ensure ALL results for course are locked by lecturers first.

## API Endpoints Summary

| Endpoint | Method | Access | Purpose |
|----------|--------|--------|---------|
| `/results/course/<id>/approve` | POST | Lecturer, Adviser, HoD | Lock results after approval |
| `/results/course/<id>/unlock` | POST | HoD Only | Unlock for corrections |
| `/results/course/<id>/final-approve` | POST | HoD Only | Final board approval |
| `/courses/<id>/assign-lecturer` | GET/POST | HoD Only | Assign lecturer to course |
| `/courses/<id>/assignments` | GET | HoD Only | View assignments |
| `/courses/assignment/<id>/remove` | POST | HoD Only | Remove assignment |

## Security Considerations

1. **Session Management**: 2-hour session timeout
2. **CSRF Protection**: All forms include CSRF tokens
3. **SQL Injection**: Parameterized queries throughout
4. **Access Control**: Role-based checks on every route
5. **Audit Logging**: Complete trail of sensitive actions
6. **Input Validation**: Server-side validation on all inputs

## Future Enhancements

- Email notifications for approvals
- Bulk approval operations
- Result comparison (before/after unlock)
- Approval deadline enforcement
- Mobile app support
- Export approval reports
- Statistical dashboards

## Support

For issues or questions:
1. Check audit logs for action history
2. Verify user roles in database
3. Review course assignments
4. Contact system administrator

---

**Last Updated**: February 5, 2026
**Version**: 2.0.0
**Author**: Result Processing System Team
