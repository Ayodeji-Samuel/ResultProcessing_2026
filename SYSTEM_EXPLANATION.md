# Result Processing System — Detailed Technical Explanation

**Institution:** Edo State University Iyamho  
**Department:** Computer Science  
**Stack:** Python 3.10 · Flask · SQLAlchemy · MySQL (production) / SQLite (dev) · ReportLab · Jinja2 / Tailwind CSS

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Project Layout](#2-architecture--project-layout)
3. [Database Models (Entities)](#3-database-models-entities)
4. [User Roles & Access Control](#4-user-roles--access-control)
5. [Authentication & Security](#5-authentication--security)
6. [Academic Session Management](#6-academic-session-management)
7. [Student Management](#7-student-management)
8. [Course Management](#8-course-management)
9. [Result Entry & Upload](#9-result-entry--upload)
10. [Grading System](#10-grading-system)
11. [Carryover Tracking](#11-carryover-tracking)
12. [NR (Not Registered) Handling](#12-nr-not-registered-handling)
13. [Approval Workflow](#13-approval-workflow)
14. [Report & Spreadsheet Generation](#14-report--spreadsheet-generation)
15. [PDF Generation](#15-pdf-generation)
16. [Audit Trail & Result Alteration Tracking](#16-audit-trail--result-alteration-tracking)
17. [System Settings](#17-system-settings)
18. [Meeting Minutes Module](#18-meeting-minutes-module)
19. [Deployment](#19-deployment)
20. [Data Flow — End-to-End Example](#20-data-flow--end-to-end-example)

---

## 1. System Overview

The Result Processing System is a web application that manages the complete academic result lifecycle for the Department of Computer Science (and related programmes) at Edo State University Iyamho. It supports:

- **Three undergraduate programmes** — Computer Science, Cyber Security, Software Engineering — plus PGD, MSc, and PhD tracks.
- **Four levels** — 100L, 200L, 300L, 400L.
- **Two semesters** per academic year.
- A **role-based multi-user** workflow (Admin → HoD → Level Adviser → Lecturer).
- **CSV/PDF upload** of student and result data.
- **Carryover tracking** — students who fail a course carry it forward to the next session.
- **Automatic, NR-flagged spreadsheets** — unregistered courses appear as "NR" (Not Registered) rather than a score of 0 or a dash.
- **PDF examination record spreadsheets** via ReportLab.
- **Full audit trail** of every result alteration, including device, browser, IP address, and GPS coordinates.

---

## 2. Architecture & Project Layout

```
ResultProcessing_2026/
├── run.py                        # Entry point — starts the Flask dev server
├── wsgi.py                       # WSGI entry point for production (Gunicorn / uWSGI)
├── config.py                     # ConfigBase, DevelopmentConfig, ProductionConfig
├── requirements.txt
├── .env                          # DATABASE_URL, SECRET_KEY (not committed)
├── app/
│   ├── __init__.py               # create_app() factory, extension init, blueprint registration
│   ├── models.py                 # All SQLAlchemy ORM models (15 tables)
│   ├── location_config.py        # Default GPS coordinates for localhost audit logging
│   ├── forms/
│   │   ├── auth_forms.py         # Login, Registration, ChangePassword, EditUser forms
│   ├── routes/
│   │   ├── auth.py               # Login/logout, user management, audit helpers, role decorators
│   │   ├── dashboard.py          # Main dashboard + academic session CRUD
│   │   ├── students.py           # Student CRUD + CSV bulk import
│   │   ├── courses.py            # Course CRUD + lecturer assignment
│   │   ├── results.py            # Result upload (CSV), manual entry, approval workflow
│   │   ├── reports.py            # Spreadsheet preview + PDF download + student report card
│   │   ├── settings.py           # System settings, grading config, logo, DB backup, carryover scanner
│   │   └── minutes.py            # Meeting minutes (AI transcript → formatted PDF)
│   ├── static/
│   │   ├── css/style.css, remixicon.css, tailwind.min.js
│   │   └── js/alpine.min.js, main.js
│   ├── templates/                # Jinja2 HTML templates (Tailwind CSS styled)
│   └── utils/
│       ├── grading.py            # Grade calculation, GPA, carryover utilities
│       ├── pdf_generator.py      # ReportLab spreadsheet + student result PDF
│       ├── csv_processor.py      # CSV parsing for students and results
│       ├── pdf_extractor.py      # Extract past results from uploaded PDF files
│       └── minutes_pdf.py        # Meeting minutes PDF generation
└── instance/                     # SQLite DB file (dev only)
```

The app is instantiated through the **application factory** `create_app()` in `app/__init__.py`, which:
1. Loads configuration from `config.py` (which reads `.env` via `python-dotenv`).
2. Initialises Flask-SQLAlchemy, Flask-Login, and Flask-WTF CSRF protection.
3. Registers all eight blueprints.
4. Calls `db.create_all()` on first run to create any missing tables.

---

## 3. Database Models (Entities)

The database has **15 tables**. Here is a description of each:

### 3.1 `users`
Stores all system users (staff accounts).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | — |
| `username` | String(120) unique | University email used as username |
| `email` | String(120) unique | Same as username |
| `password_hash` | String(256) | PBKDF2-SHA256 hash |
| `full_name` | String(128) | Display name |
| `role` | String(20) | `admin`, `hod`, `level_adviser`, `lecturer` |
| `program` | String(64) | Assigned programme (legacy single-value) |
| `level` | Integer | Assigned level (legacy single-value) |
| `is_active` | Boolean | Deactivated accounts cannot log in |
| `is_locked` | Boolean | Locked by HoD/Admin after repeated failures |
| `failed_login_attempts` | Integer | Counter; resets on successful login |
| `locked_until` | DateTime | Temporary lockout expiry |
| `must_change_password` | Boolean | Force password change on first login |
| `last_login`, `last_login_ip`, `last_login_device` | — | Login tracking |
| `created_by` | FK → users | Who created this account |

### 3.2 `level_adviser_programs`
Allows a single level adviser to be assigned to **multiple (level, programme)** pairs, replacing the legacy single `User.program` / `User.level` fields.

### 3.3 `academic_sessions`
One row per academic year (e.g. "2025/2026"). Only one session can be `is_current = True` at a time.

### 3.4 `students`
Student records **scoped per session**. A student who is promoted re-appears as a new row in the next session with an incremented level.

| Column | Description |
|--------|-------------|
| `matric_number` | e.g. `FSC/CSC/23/001`. Unique per session. |
| `surname`, `first_name`, `other_names` | Name fields |
| `gender` | `M` or `F` |
| `program` | `Computer Science`, `Cyber Security`, `Software Engineering`, etc. |
| `level` | 100, 200, 300, or 400 |
| `session_id` | FK → academic_sessions |

**Unique constraint:** `(matric_number, session_id)` — the same student can exist in different sessions.

### 3.5 `courses`
Course catalogue entries, one per (course_code, programme, level) combination.

| Column | Description |
|--------|-------------|
| `course_code` | e.g. `CSC 101` |
| `credit_unit` | Integer (1–6) |
| `semester` | 1 or 2 |
| `level` | 100–400 |
| `program` | Programme name |
| `status` | `C` = Compulsory, `R` = Required, `E` = Elective |
| `degree_type` | `BSc`, `PGD`, `MSc`, `PhD` |
| `is_active` | Soft delete |
| `is_approved` / `approved_by` / `approved_at` | Final HoD approval flag |

**Unique constraint:** `(course_code, program, level)`.

### 3.6 `course_assignments`
Maps a **Lecturer** user to a specific course in a specific session (assigned by HoD). Lecturers can only see/upload results for their assigned courses.

### 3.7 `results`
The core table — one row per (student, course, session).

| Column | Description |
|--------|-------------|
| `ca_score` | Continuous Assessment (0–30) |
| `exam_score` | Examination score (0–70) |
| `total_score` | `ca_score + exam_score` (0–100) |
| `grade` | A/B/C/D/E/F |
| `grade_point` | 5/4/3/2/1/0 |
| `is_carryover` | True if the student is retaking the course from a previous session |
| `is_locked` | Locked after lecturer approval |
| `locked_by` / `locked_at` | Who locked it and when |
| `unlocked_by` / `unlocked_at` | HoD can unlock for correction |
| `uploaded_by` | FK → users (last editor) |

**Unique constraint:** `(student_id, course_id, session_id)` — no duplicate scores.

### 3.8 `grading_systems`
Configurable score ranges per degree type. Defaults are set at application startup and can be modified by HoD/Admin.

| Degree | Grade | Score Range | Points |
|--------|-------|-------------|--------|
| BSc | A | 70–100 | 5 |
| BSc | B | 60–69 | 4 |
| BSc | C | 50–59 | 3 |
| BSc | D | 45–49 | 2 |
| BSc | E | 40–44 | 1 |
| BSc | F | 0–39 | 0 |

PGD, MSc, and PhD have separate configurable scales.

### 3.9 `system_settings`
Key-value store for system-wide settings such as university name, faculty name, PDF font sizes, and page margins.

### 3.10 `carryovers`
Tracks failed courses that a student must retake. Identified by `student_matric` (not `student_id`) so the record persists across sessions.

| Column | Description |
|--------|-------------|
| `student_matric` | Matric number (persists across sessions) |
| `course_id` | FK → courses |
| `original_session_id` | Session when the student first failed |
| `original_level` | Student's level when they failed |
| `is_cleared` | True when the student later passes the course |
| `cleared_session_id` | Session when it was cleared |
| `cleared_result_id` | The Result that cleared it |

**Unique constraint:** `(student_matric, course_id, original_session_id)` — no duplicate carryover entries.

### 3.11 `student_academic_history`
Snapshot of per-session GPA, CGPA, credit units passed/failed, and academic standing remarks for each student.

### 3.12 `upload_logs`
Records every CSV upload — user, file name, records processed/failed, status, and error messages.

### 3.13 `audit_logs`
Comprehensive security log for every significant action. Stores user, action type, category, resource, IP address, device type, browser, OS, location, and Flask session ID.

### 3.14 `result_alterations`
Specialised alteration log for **every change to a result** (create, update, delete). Stores old and new score/grade values, actor's device details, IP, browser, GPS coordinates (latitude/longitude), and reason.

### 3.15 `meeting_minutes` / `known_attendees` / `attendance_tokens` / `meeting_attendees`
Support tables for the Meeting Minutes module (see [Section 18](#18-meeting-minutes-module)).

---

## 4. User Roles & Access Control

| Role | Who | Permissions |
|------|-----|-------------|
| **admin** | System administrator | Full access to all data, settings, user management, database backup, audit logs, result alteration logs |
| **hod** | Head of Department | All academic data across all programmes/levels; creates/manages user accounts; approves and unlocks results; gives final approvals; system settings |
| **level_adviser** | Assigned by HoD | Full access limited to their assigned (level, programme) pair(s); can upload results, generate spreadsheets, approve courses |
| **lecturer** | Assigned by HoD | Access limited to courses explicitly assigned in `course_assignments`; can upload results for their courses and approve them |

Role restrictions are enforced server-side via:
- The `@hod_required`, `@admin_required`, and `@admin_or_hod_required` decorators in `auth.py`.
- The `get_accessible_filters()` utility in `grading.py` which returns `(level, programs)` filter values that are applied to every database query in the results and reports blueprints.

---

## 5. Authentication & Security

### Login Flow
1. User submits email + password via the `/login` page.
2. The system checks:
   - Is the account active (`is_active == True`)?
   - Is the account locked (`is_locked == True` or `locked_until` in the future)?
   - Does the password hash match (`check_password_hash`)?
3. On **failure**: increments `failed_login_attempts`. After 5 failures → sets `locked_until` to +15 minutes.
4. On **success**: resets `failed_login_attempts`, records `last_login`, `last_login_ip`, and `last_login_device`; writes an `AuditLog(action='LOGIN')` entry.
5. If `must_change_password == True` (e.g. first login), the user is immediately redirected to the force-change-password page.

### Password Security
- Hashed with PBKDF2-SHA256 via Werkzeug's `generate_password_hash`.
- All new accounts default to `must_change_password = True`.

### Session Security
- Flask sessions with CSRF protection (Flask-WTF) — `WTF_CSRF_ENABLED = True`.
- Session lifetime: 2 hours (`PERMANENT_SESSION_LIFETIME`).
- In production: `SESSION_COOKIE_SECURE = True` (HTTPS only).

### IP & Device Tracking
Every login and every result alteration records:
- IP address (handles `X-Forwarded-For` proxy header)
- Geolocation via `ip-api.com` (city, region, country; lat/lon)
- Device type, browser, and OS parsed from the User-Agent string using the `user-agents` library

---

## 6. Academic Session Management

Managed at `/dashboard/sessions` (HoD/Admin).

- Sessions are named in `YYYY/YYYY` format (e.g. `2025/2026`).
- Only **one session** can be marked `is_current = True` at a time. Setting a new session as current automatically clears the previous one.
- All other data (students, results, assignments) is scoped to `session_id`, so changing the active session gives a clean slate without deleting historical data.

---

## 7. Student Management

### Manual Entry
Via `/students/new` — form-based entry of individual students into the current session.

### CSV Bulk Import
Via `/students/upload` — accepts a CSV file with columns:
- `Matric Number` (required)
- `Surname` (required)  
- `First Name` (required)
- `Other Names` (optional)
- `Gender` (optional, `M`/`F`)
- `Level` (optional — if omitted, uses the form-selected default)
- `Program` (optional — if omitted, uses the form-selected default)

The parser (`csv_processor.parse_student_csv`) normalises column names case-insensitively, validates matric numbers and levels, detects within-file duplicates, and reports errors per row. On import, existing students (same matric + session) are **updated** rather than duplicated.

### Matric Number Format
```
FSC/CSC/YY/NNN    — Computer Science
FSC/CBS/YY/NNN    — Cyber Security
FSC/SWE/YY/NNN    — Software Engineering
FSC/CSC/CV/NNN    — Computer Science (Conversion)
```

---

## 8. Course Management

Managed at `/courses/` (HoD/Admin/Level Adviser).

### Creating Courses
Each course belongs to a specific `program` and `level`, so `CSC 101` at 100L Computer Science is a **different record** from `CSC 101` at 100L Cyber Security. This design allows different credit units, status, or syllabi per programme.

### Course Assignment to Lecturers
HoD assigns courses to lecturers via `CourseAssignment` records. Lecturers can only view, upload, and approve results for their assigned courses.

### Course Approval
After a departmental board meeting, the HoD can mark a course `is_approved = True`, signalling that all results are final. This is separate from the per-result `is_locked` flag.

---

## 9. Result Entry & Upload

Results can be entered in two ways:

### 9.1 CSV Upload (`/results/upload`)
1. Lecturer selects a course and uploads a CSV file.
2. CSV columns: `Matric Number`, `CA Score` (0–30), `Exam Score` (0–70).
3. The system validates scores, looks up the student, computes `total_score = CA + Exam`, and derives the grade.
4. **Student Lookup Logic (Carryover-Aware):**
   - First, try an exact match: `matric_number + session_id + level == course.level + program == course.program`.
   - If not found, check if there is a **higher-level student** in the current session who has this matric number (i.e. a student at 300L uploading results for a 100L course they are retaking).
   - If still not found → `not_found` list (warning shown after upload).
5. `is_carryover` is set to `True` if `student.level > course.level` OR if there is an uncleared `Carryover` record for that student + course.
6. If the result is a **pass** (`grade != 'F'`) and `is_carryover`, the system calls `check_and_clear_carryovers()` to mark the carryover as cleared.
7. After all results are saved, `process_carryovers_for_student()` is called for each student to create `Carryover` records for any **new failures**.
8. Every CREATE and UPDATE is logged to `result_alterations`.

### 9.2 Manual Entry (`/results/entry/<course_id>`)
1. The system displays a table with all students at the course's level/programme **plus** any carryover students (higher-level students with outstanding carryovers for this course).
2. Scores are entered inline. Empty rows are skipped.
3. The same carryover detection, grade calculation, and alteration logging applies.
4. Supports AJAX submission (returns JSON if `X-Requested-With: XMLHttpRequest` header is present).
5. If a result is changed **back** to F, any previously cleared `Carryover` record is re-activated.

---

## 10. Grading System

Grades are computed by `get_grade_info(total_score, degree_type)` in `app/utils/grading.py`.

### Default BSc Scale
| Grade | Score Range | Grade Point | Description |
|-------|-------------|-------------|-------------|
| A | 70 – 100 | 5 | Excellent |
| B | 60 – 69 | 4 | Very Good |
| C | 50 – 59 | 3 | Good |
| D | 45 – 49 | 2 | Fair |
| E | 40 – 44 | 1 | Pass |
| F | 0 – 39 | 0 | Fail |

The system first queries `GradingSystem` table for custom ranges. If the table is empty or has no match, it falls back to the hardcoded defaults above. Custom ranges can be configured per degree type (BSc, PGD, MSc, PhD) in Settings.

### GPA & CGPA Calculation
```
GPA = Σ(grade_point × credit_unit) / Σ(credit_unit)
```
Applies to a set of results for a single semester or session. `calculate_cgpa()` aggregates all results across semesters.

### Class of Degree (CGPA)
| CGPA | Class |
|------|-------|
| ≥ 4.50 | First Class Honours |
| ≥ 3.50 | Second Class Honours (Upper Division) |
| ≥ 2.40 | Second Class Honours (Lower Division) |
| ≥ 1.50 | Third Class Honours |
| ≥ 1.00 | Pass |
| < 1.00 | Fail |

---

## 11. Carryover Tracking

The carryover system tracks students who fail courses and must retake them in subsequent sessions.

### How Carryovers Are Created

**Automatic (on upload/entry):**  
After every batch of results is saved, `process_carryovers_for_student()` queries all `Result` rows with `grade = 'F'` for that student in the current session and creates `Carryover` records if they do not already exist.

**Retroactive scanning:**  
The admin/HoD can trigger `scan_and_create_past_carryovers()` from the Settings page ("Carryover Scanner"). This three-phase scan:
1. Creates `Carryover` records for **all** existing failed results that do not yet have one.
2. Auto-clears carryovers where the student has a passing result in any session (for that same course).
3. Sets `Result.is_carryover = True` for any result where `student.level > course.level`.

This is idempotent — running it multiple times is safe.

### How Carryovers Are Cleared

`check_and_clear_carryovers()` is called whenever a result is saved. If the grade is not F and there is an uncleared `Carryover` for that student+course, it marks `is_cleared = True` and records `cleared_session_id` and `cleared_result_id`.

### Impact on Spreadsheets

When a spreadsheet is generated for (e.g.) 100L Computer Science, the system:
1. Fetches all regular 100L Computer Science students.
2. Calls `get_carryover_students_for_level(100, 'Computer Science', session_id)` to find students at **higher levels** (200L, 300L, 400L) who have results for any 100L Computer Science course in the current session.
3. Combines both lists (deduplicating by student ID) and generates one unified spreadsheet.

This ensures that a 400L student retaking CSC 101 appears on the 100L spreadsheet in the correct row.

---

## 12. NR (Not Registered) Handling

When the spreadsheet is generated, a result is shown as **NR** (Not Registered) if a student has **no result record** for a particular course in the current session. This is distinct from a score of zero.

### Where NR Appears

| Location | Code | Behaviour |
|----------|------|-----------|
| Spreadsheet preview (HTML) | `reports/spreadsheet_preview.html` | Cell shows "NR" in grey italic when `result == None` |
| Spreadsheet PDF | `pdf_generator.py` (lines ~375, ~388, ~421) | `.get(course_code, 'NR')` default |
| Route data builder | `reports.py` spreadsheet() | `student_row['first_semester'][code] = 'NR'` when no Result |

### What NR Means
- **Not counted in GPA** — only courses with actual results are included in GPA/CGPA calculations.
- **Not treated as a failure** — no `Carryover` record is created for NR courses.
- **Displayed with grey italic styling** in the preview template.
- The spreadsheet grading key includes an explanation of "NR = Not Registered (course not attempted; not counted in GPA)".

---

## 13. Approval Workflow

The system enforces a **three-tier approval** process before results are considered final.

```
Lecturer → Level Adviser / Lecturer Approval → HoD Unlock (if correction needed) → HoD Final Approval
```

### Step 1 — Lecturer Approval (`/results/course/<id>/approve`)
- Any lecturer **assigned** to the course (via `CourseAssignment`), or any Level Adviser/HoD in scope, can approve.
- Approval **locks** all results for the course: `Result.is_locked = True`, `locked_by`, `locked_at`.
- Locked results **cannot be edited or deleted** by regular lecturers.

### Step 2 — HoD Unlock (if needed) (`/results/course/<id>/unlock`)
- Only the **HoD** can unlock results: `Result.is_locked = False`, `unlocked_by`, `unlocked_at`.
- This allows corrections then re-approval.

### Step 3 — HoD Final Approval (`/results/course/<id>/final-approve`)
- Only the **HoD** can give final approval.
- **Prerequisite:** ALL results for the course must be locked (i.e. approved by the lecturer).
- Sets `Course.is_approved = True`, `Course.approved_by`, `Course.approved_at`.
- Once finally approved, results are considered immutable for the academic record.

All three actions create `AuditLog` entries.

---

## 14. Report & Spreadsheet Generation

### Spreadsheet Preview (`/reports/spreadsheet`)

1. User selects level, programme, and semester (First, Second, or Both).
2. The system fetches:
   - Regular students at the selected level/programme.
   - Carryover students from higher levels (via `get_carryover_students_for_level()`).
3. For each student, the system loops over all active courses for the selected level/programme/semester(s) and looks up their `Result`. Missing results → `'NR'`.
4. GPA/CGPA is calculated from the actual results (NR entries excluded).
5. The combined data is passed to `spreadsheet_preview.html` for a paginated web preview.
6. A **Download PDF** button calls the same data generation logic and passes it to `generate_spreadsheet_pdf()`.

### Student Report Card (`/reports/student/<matric>`)

Generates a per-student report showing all results across all sessions, semester GPAs, CGPA, class of degree, and outstanding carryovers.

---

## 15. PDF Generation

All PDFs use **ReportLab** (landscape A4).

### Examination Record Spreadsheet PDF

Generated by `generate_spreadsheet_pdf()` in `app/utils/pdf_generator.py`.

**Structure:**
1. **Header block** — university logo (if uploaded), university name, faculty, department, session, programme, level, semester.
2. **Student table** — one row per student with columns:
   - S/N — Matric Number — Student Name — Gender
   - One column per course (score+grade formatted as e.g. "70A") — missing → "NR"
   - First/Second Semester summaries: Units Registered, Units Passed, Units Failed, GPA
   - Session summary: Total Units, CGPA
3. **Course headers** — course codes/titles are rendered **vertically** (rotated 90°) using the `VerticalText` flowable to save horizontal space.
4. **Footer** — three signatory lines: Course Adviser, HoD, Dean.

**Configurable via `system_settings`:**
- `pdf_data_font_size` — font size for score cells (min 8pt)
- `pdf_course_hdr_font_size` — font size for the vertical course title headers
- `pdf_page_margin` — page margin in cm

**Score format:** `format_score_grade()` returns e.g. `"70A"`, `"55C"`, `"39F"`.

### Student Result PDF

Generated by `generate_student_result_pdf()` — portrait A4 result slip with university header, student bio-data, table of results (course code, title, CA, Exam, Total, Grade, Credit Units), GPA, CGPA, and class of degree.

---

## 16. Audit Trail & Result Alteration Tracking

### General Audit Log (`audit_logs`)
Written by `log_audit()` in `auth.py`. Captures every significant action:
- Login / Logout / Failed Login / Forced Logout
- User creation, update, deactivation
- Session creation/change
- Course/student CRUD
- Result approvals, locks, unlocks, final approvals
- System settings changes
- Database backup downloads

### Result Alteration Log (`result_alterations`)
Written by `log_result_alteration()` in `auth.py` whenever a result is **created, updated, or deleted**. Contains:
- `old_ca_score`, `old_exam_score`, `old_total_score`, `old_grade`
- `new_ca_score`, `new_exam_score`, `new_total_score`, `new_grade`
- Reason (e.g. "CSV upload creation", "Manual entry update")
- Actor details: name, role, IP address
- Device details: device type, browser, OS, `device_username` (from request headers)
- GPS coordinates: `latitude`, `longitude` (from IP geolocation or default campus coords)

Only **Admin** users can view the result alteration log.

---

## 17. System Settings

Managed at `/settings/system` (Admin/HoD). Includes:

| Setting | Description |
|---------|-------------|
| `university_name` | Printed in PDF headers |
| `faculty_name` | Printed in PDF headers |
| `department_name` | Printed in PDF headers |
| `pdf_data_font_size` | Score cell font size in PDF |
| `pdf_course_hdr_font_size` | Vertical course header font size |
| `pdf_page_margin` | PDF margin (cm) |

### Logo
Upload a custom university logo (PNG/JPG/GIF) at `/settings/logo`. Saved as `app/static/logos/university_logo.jpg`. If no custom logo is found, the default logo at `app/static/images/default_logo.png` is used.

### Grading System
Edit grading scale per degree type at `/settings/grading/<degree_type>`. Changes take effect immediately for all subsequent grade calculations.

### Database Backup (Admin only)
- **SQLite** — copies the `.db` file to a download buffer.
- **MySQL** — runs `mysqldump` as a subprocess and streams the SQL dump.
- **PostgreSQL** — runs `pg_dump --format=custom`.

### Carryover Scanner (Admin/HoD)
A single-click tool at `/settings/scan-carryovers` that runs `scan_and_create_past_carryovers()` to back-fill carryover records for all historical results. Reports count of records created, cleared, and flagged. Safe to run multiple times.

---

## 18. Meeting Minutes Module

An auxiliary feature at `/minutes/` that assists in documenting departmental meetings.

- **Create a meeting record** — set title, date, time, venue, chairperson, attendees.
- **Voice transcript** — raw transcript can be pasted or recorded.
- **AI-formatted minutes** — if configured, an AI endpoint formats the raw transcript into structured Markdown minutes.
- **Action items** — extracted from the minutes and stored as JSON.
- **PDF export** — generates a formatted meeting minutes PDF.
- **Attendance tokens** — the organiser can generate a one-time URL that allows any attendee to self-register their attendance (name, email, department). Tokens can be revoked at any time and auto-expire.
- **Known attendees** — once someone registers via an attendance token, their profile is stored and auto-fills on future forms.

---

## 19. Deployment

### Development
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS

pip install -r requirements.txt

# Set DATABASE_URL in .env (defaults to SQLite if not set)
python run.py
```

### Production (DigitalOcean / any VPS)
- Set `DATABASE_URL` and `SECRET_KEY` in environment variables or `.env`.
- Run with **Gunicorn**: `gunicorn wsgi:app --workers 4 --bind 0.0.0.0:8000`
- Or **uWSGI**, or via a systemd service.
- Use **Nginx** as a reverse proxy.
- See [DIGITALOCEAN_DEPLOYMENT.md](DIGITALOCEAN_DEPLOYMENT.md) for step-by-step VPS setup.

### CI/CD
A `Jenkinsfile` is present in the project root, enabling automated build and deploy pipelines.

---

## 20. Data Flow — End-to-End Example

Below is a step-by-step walk-through of how results are entered and a spreadsheet produced for **100L Computer Science, First Semester, 2025/2026**.

### Step 1 — Set Academic Session
1. Admin/HoD navigates to Dashboard → Sessions.
2. Creates `2025/2026` and marks it as current.

### Step 2 — Import Students
1. Level Adviser uploads `students_100L_CS.csv`.
2. System creates `Student` rows with `level=100`, `program='Computer Science'`, `session_id=<2025/2026 ID>`.

### Step 3 — Ensure Courses Exist
1. HoD verifies that 100L Computer Science First Semester courses (`CSC 101`, `CSC 103`, `MTH 101`, etc.) exist in the `courses` table.
2. Each course has `level=100`, `program='Computer Science'`, `semester=1`, `is_active=True`.

### Step 4 — Assign Courses to Lecturers
1. HoD assigns `CSC 101` to Dr. A via `CourseAssignment`.
2. Dr. A can now see `CSC 101` on their upload page.

### Step 5 — Upload Results (CSC 101)
1. Dr. A uploads `csc101_results.csv`:
   ```
   Matric Number, CA Score, Exam Score
   FSC/CSC/23/001, 25, 55
   FSC/CSC/23/002, 18, 32
   ```
2. System parses CSV → looks up students → calculates totals (80 → A5, 50 → E1).
3. `Result` rows created. `Carryover` row created for `FSC/CSC/23/002` (grade F, total=50 < 40... wait, 50 is E not F — corrected: 18+32=50 → E, no carryover).
4. Alteration log entry written for each result.

### Step 6 — Lecturer Approval
1. Dr. A reviews results at `/results/course/<CSC101_id>` and clicks **Approve**.
2. All `Result.is_locked = True`.

### Step 7 — HoD Final Approval
1. After the departmental board meeting, HoD clicks **Final Approve** on CSC 101.
2. `Course.is_approved = True`.

### Step 8 — Carryover Students Add to 100L
Suppose `FSC/CSC/22/005` is now a 300L student but failed `CSC 101` in 2022/2023. In 2025/2026 they retake it. Their result is uploaded via CSV or manual entry under CSC 101 — the system finds them via the higher-level student fallback lookup and marks `is_carryover = True`.

### Step 9 — Generate Spreadsheet
1. Level Adviser navigates to Reports → Spreadsheet.
2. Selects Level 100, Computer Science, Both Semesters.
3. System:
   - Fetches all 100L CS students (regular).
   - Calls `get_carryover_students_for_level(100, 'Computer Science', session_id)` → finds `FSC/CSC/22/005`.
   - Combines lists.
   - Loops over courses: result found → `"80A"`, no result → `"NR"`.
   - Calculates GPA per semester, CGPA per student.
4. Preview rendered in browser.
5. Click **Download PDF** → `generate_spreadsheet_pdf()` produces a landscape A4 PDF with vertical course headers.

---

## Summary of Key Design Decisions

| Decision | Reason |
|----------|--------|
| Students scoped per session | Historical results are preserved when a student is promoted |
| Carryover tracked by matric number, not student ID | Matric number persists across sessions; student ID changes each year |
| NR instead of 0/F for unregistered courses | Clearly distinguishes "did not sit" from "sat and failed"; prevents grade pollution |
| Higher-level students included on lower-level spreadsheets | Carryover students must appear on the original level's official document |
| Two-stage result locking (lecturer + HoD) | Matches Nigerian university academic board workflow |
| Configurable grading per degree type | PGD/MSc/PhD often use different score thresholds |
| Alteration log with GPS/device data | Provides forensic evidence if results are tampered with |
