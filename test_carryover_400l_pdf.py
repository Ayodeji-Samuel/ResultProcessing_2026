"""
Test: 400-Level Student with Heavy Carryover Load – PDF Spreadsheet Generation
===============================================================================
Scenario
--------
* One special 400L student (ADEYEMI TAIWO GABRIEL) accumulated carryovers from
  three previous levels while still sitting all current 400L courses.

  First Semester exams  (22 total, displayed 100L → 400L):
    - 5 × 100L carryover courses
    - 3 × 200L carryover courses
    - 4 × 300L carryover courses
    - 10 × 400L current courses  ← 10 official 400L first-semester courses

  Second Semester exams (12 total, displayed 100L → 400L):
    - 1 × 100L carryover course
    - 1 × 200L carryover course
    - 2 × 300L carryover courses
    - 8 × 400L current courses   ← 8 official 400L second-semester courses
                                   ("filled 8 courses from both semesters")

* Four additional NORMAL 400L students sit only the 400L courses (carryover
  columns show "-" for them).

Course ordering requirement
---------------------------
Courses are sorted lowest-level-first (100L → 200L → 300L → 400L) within each
semester column group, exactly as required by the department.

Usage
-----
    python test_carryover_400l_pdf.py

Output PDFs
-----------
    test_400l_carryover_both_semesters.pdf  – BOTH semesters view (main test)
    test_400l_carryover_sem1_only.pdf       – first semester only
    test_400l_carryover_sem2_only.pdf       – second semester only
"""

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap Flask app context (needed by pdf_generator → get_logo_path)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app
from app.utils.pdf_generator import generate_spreadsheet_pdf
from config import Config

app = create_app()

# ===========================================================================
# 1.  COURSE CATALOGUE  (sorted 100L → 400L within each semester)
# ===========================================================================

# ── First Semester Courses ──────────────────────────────────────────────────
FIRST_SEM_COURSES = [
    # 5 × 100L  (carryovers)
    {'code': 'CSC101', 'title': 'Introduction to Computer Science',   'credit_unit': 3, 'status': 'C', 'level': 100, 'carryover': True},
    {'code': 'MTH101', 'title': 'Elementary Mathematics I',           'credit_unit': 3, 'status': 'C', 'level': 100, 'carryover': True},
    {'code': 'PHY101', 'title': 'General Physics I',                  'credit_unit': 3, 'status': 'C', 'level': 100, 'carryover': True},
    {'code': 'CHM101', 'title': 'General Chemistry I',                'credit_unit': 3, 'status': 'C', 'level': 100, 'carryover': True},
    {'code': 'ENG101', 'title': 'Communication in English I',         'credit_unit': 2, 'status': 'C', 'level': 100, 'carryover': True},
    # 3 × 200L  (carryovers)
    {'code': 'CSC201', 'title': 'Computer Programming I',             'credit_unit': 3, 'status': 'C', 'level': 200, 'carryover': True},
    {'code': 'MTH201', 'title': 'Mathematical Methods I',             'credit_unit': 3, 'status': 'C', 'level': 200, 'carryover': True},
    {'code': 'CSC203', 'title': 'Data Structures & Algorithms',       'credit_unit': 3, 'status': 'C', 'level': 200, 'carryover': True},
    # 4 × 300L  (carryovers)
    {'code': 'CSC301', 'title': 'Systems Analysis & Design',          'credit_unit': 3, 'status': 'C', 'level': 300, 'carryover': True},
    {'code': 'CSC303', 'title': 'Database Management Systems',        'credit_unit': 3, 'status': 'C', 'level': 300, 'carryover': True},
    {'code': 'CSC305', 'title': 'Software Engineering I',             'credit_unit': 3, 'status': 'C', 'level': 300, 'carryover': True},
    {'code': 'MTH305', 'title': 'Numerical Methods',                  'credit_unit': 2, 'status': 'E', 'level': 300, 'carryover': True},
    # 10 × 400L  (official current-level courses for S1)
    {'code': 'CSC401', 'title': 'Compiler Construction',              'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC403', 'title': 'Artificial Intelligence',            'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC405', 'title': 'Computer Networks II',               'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC407', 'title': 'Operating Systems II',               'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC409', 'title': 'Information Security',               'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC411', 'title': 'Computer Architecture II',           'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC413', 'title': 'Final Year Project I',               'credit_unit': 6, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC415', 'title': 'Distributed Systems',                'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC417', 'title': 'Machine Learning Fundamentals',      'credit_unit': 3, 'status': 'E', 'level': 400, 'carryover': False},
    {'code': 'CSC419', 'title': 'Cloud Computing',                    'credit_unit': 3, 'status': 'E', 'level': 400, 'carryover': False},
]

# ── Second Semester Courses ─────────────────────────────────────────────────
SECOND_SEM_COURSES = [
    # 1 × 100L  (remaining carryover)
    {'code': 'MTH102', 'title': 'Elementary Mathematics II',          'credit_unit': 3, 'status': 'C', 'level': 100, 'carryover': True},
    # 1 × 200L  (remaining carryover)
    {'code': 'CSC202', 'title': 'Computer Programming II',            'credit_unit': 3, 'status': 'C', 'level': 200, 'carryover': True},
    # 2 × 300L  (remaining carryovers)
    {'code': 'CSC302', 'title': 'Object-Oriented Programming',        'credit_unit': 3, 'status': 'C', 'level': 300, 'carryover': True},
    {'code': 'CSC304', 'title': 'Computer Graphics',                  'credit_unit': 3, 'status': 'E', 'level': 300, 'carryover': True},
    # 8 × 400L  (official current-level courses for S2 — the "filled 8 courses")
    {'code': 'CSC402', 'title': 'Advanced Algorithms',                'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC404', 'title': 'Digital Signal Processing',          'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC406', 'title': 'Research Methods in Computing',      'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC408', 'title': 'Parallel & Distributed Computing',   'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC410', 'title': 'Advanced Database Systems',          'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC412', 'title': 'Human Computer Interaction',         'credit_unit': 3, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC414', 'title': 'Final Year Project II',              'credit_unit': 6, 'status': 'C', 'level': 400, 'carryover': False},
    {'code': 'CSC416', 'title': 'Cyber Security Management',          'credit_unit': 3, 'status': 'E', 'level': 400, 'carryover': False},
]

# Verify counts
assert len(FIRST_SEM_COURSES)  == 22, f"Expected 22 S1 courses, got {len(FIRST_SEM_COURSES)}"
assert len(SECOND_SEM_COURSES) == 12, f"Expected 12 S2 courses, got {len(SECOND_SEM_COURSES)}"

s1_100l = [c for c in FIRST_SEM_COURSES  if c['level'] == 100]
s1_200l = [c for c in FIRST_SEM_COURSES  if c['level'] == 200]
s1_300l = [c for c in FIRST_SEM_COURSES  if c['level'] == 300]
s1_400l = [c for c in FIRST_SEM_COURSES  if c['level'] == 400]
s2_100l = [c for c in SECOND_SEM_COURSES if c['level'] == 100]
s2_200l = [c for c in SECOND_SEM_COURSES if c['level'] == 200]
s2_300l = [c for c in SECOND_SEM_COURSES if c['level'] == 300]
s2_400l = [c for c in SECOND_SEM_COURSES if c['level'] == 400]

assert len(s1_100l) == 5,  f"Expected 5 100L S1, got {len(s1_100l)}"
assert len(s1_200l) == 3,  f"Expected 3 200L S1, got {len(s1_200l)}"
assert len(s1_300l) == 4,  f"Expected 4 300L S1, got {len(s1_300l)}"
assert len(s1_400l) == 10, f"Expected 10 400L S1, got {len(s1_400l)}"
assert len(s2_100l) == 1,  f"Expected 1  100L S2, got {len(s2_100l)}"
assert len(s2_200l) == 1,  f"Expected 1  200L S2, got {len(s2_200l)}"
assert len(s2_300l) == 2,  f"Expected 2  300L S2, got {len(s2_300l)}"
assert len(s2_400l) == 8,  f"Expected 8  400L S2, got {len(s2_400l)}"

# ===========================================================================
# 2.  HELPER: assign a plausible score + grade + grade-point for each entry
# ===========================================================================

def make_score(base: int, delta: int = 0) -> dict:
    """Return a score entry dict given a total score."""
    total = max(0, min(100, base + delta))
    ca    = round(total * 0.30)
    exam  = total - ca

    if total >= 70:
        grade, gp = 'A', 5
    elif total >= 60:
        grade, gp = 'B', 4
    elif total >= 50:
        grade, gp = 'C', 3
    elif total >= 45:
        grade, gp = 'D', 2
    elif total >= 40:
        grade, gp = 'E', 1
    else:
        grade, gp = 'F', 0

    return {
        'ca': ca, 'exam': exam, 'total': total,
        'grade': grade, 'gp': gp,
        'display': f"{total}{grade}",   # e.g. "72A"
        'credit_unit': None,            # filled per course below
    }


def score_for(course: dict, offset: int = 0) -> dict:
    """
    Generate a context-aware score for a course.
    Carryover courses follow a realistic pattern (borderline pass / retry).
    Regular courses are generally higher scores.
    """
    import hashlib
    seed = int(hashlib.md5(course['code'].encode()).hexdigest()[:4], 16) % 30
    if course.get('carryover'):
        base = 48 + (seed % 20) + offset   # 48–67 range (some still fail)
    else:
        base = 60 + (seed % 25) + offset   # 60–84 range
    entry = make_score(base)
    entry['credit_unit'] = course['credit_unit']
    return entry


def compute_summary(course_scores: list) -> dict:
    """Compute semester summary from a list of (course, score_entry) pairs."""
    total_units = 0
    passed_units = 0
    failed_units = 0
    weighted_gp = 0.0

    for course, entry in course_scores:
        cu = course['credit_unit']
        total_units += cu
        if entry['gp'] > 0:
            passed_units += cu
            weighted_gp += entry['gp'] * cu
        else:
            failed_units += cu

    gpa = (weighted_gp / total_units) if total_units > 0 else 0.0
    return {
        'total_units':  total_units,
        'passed_units': passed_units,
        'failed_units': failed_units,
        'gpa':          round(gpa, 2),
    }


def compute_session_summary(s1_summary: dict, s2_summary: dict) -> dict:
    combined_total  = s1_summary['total_units']  + s2_summary['total_units']
    combined_passed = s1_summary['passed_units'] + s2_summary['passed_units']
    combined_failed = s1_summary['failed_units'] + s2_summary['failed_units']
    # CGPA = weighted average of the two GPAs by total units
    if combined_total > 0:
        cgpa = (
            s1_summary['gpa'] * s1_summary['total_units'] +
            s2_summary['gpa'] * s2_summary['total_units']
        ) / combined_total
    else:
        cgpa = 0.0
    return {
        'total_units':  combined_total,
        'passed_units': combined_passed,
        'failed_units': combined_failed,
        'cgpa':         round(cgpa, 2),
    }


# ===========================================================================
# 3.  STUDENT PROFILES
# ===========================================================================

# ── 3a. The carryover student ───────────────────────────────────────────────
def build_carryover_student() -> dict:
    """
    ADEYEMI TAIWO GABRIEL – 400L male student with heavy carryover load.
    S1 : all 22 courses sit (5×100L + 3×200L + 4×300L + 10×400L)
    S2 : all 12 courses sit (1×100L + 1×200L + 2×300L + 8×400L)
    """
    s1_scores: dict[str, str] = {}
    s1_pairs  = []
    for course in FIRST_SEM_COURSES:
        entry = score_for(course, offset=0)
        s1_scores[course['code']] = entry['display']
        s1_pairs.append((course, entry))

    s2_scores: dict[str, str] = {}
    s2_pairs  = []
    for course in SECOND_SEM_COURSES:
        entry = score_for(course, offset=5)   # slightly better in S2
        s2_scores[course['code']] = entry['display']
        s2_pairs.append((course, entry))

    s1_sum = compute_summary(s1_pairs)
    s2_sum = compute_summary(s2_pairs)
    ss_sum = compute_session_summary(s1_sum, s2_sum)

    # Work out remark: fail more than 1/3 of CU → Probation
    remark = 'Probation' if ss_sum['failed_units'] > ss_sum['total_units'] // 3 else 'Proceed'

    return {
        'matric_number':          'FSC/CSC/19/0047',
        'name':                   'ADEYEMI Taiwo Gabriel',
        'gender':                 'M',
        'first_semester':         s1_scores,
        'second_semester':        s2_scores,
        'first_semester_summary': s1_sum,
        'second_semester_summary': s2_sum,
        'session_summary':        ss_sum,
        'remark':                 remark,
        '_note': (
            f"S1 => {len(FIRST_SEM_COURSES)} exams "
            f"(5×100L + 3×200L + 4×300L + 10×400L);  "
            f"S2 => {len(SECOND_SEM_COURSES)} exams "
            f"(1×100L + 1×200L + 2×300L + 8×400L filled)"
        ),
    }


# ── 3b. Four regular 400L students ─────────────────────────────────────────
REGULAR_STUDENTS_RAW = [
    ('FSC/CSC/19/0051', 'IBRAHIM Fatima Zara',   'F', 8),
    ('FSC/CSC/19/0063', 'OKEKE Chukwuemeka B.',  'M', 3),
    ('FSC/CSC/19/0078', 'BELLO Aminu Suleiman',  'M', 12),
    ('FSC/CSC/19/0082', 'OKAFOR Chidinma Ngozi', 'F', -5),
]


def build_regular_student(matric: str, name: str, gender: str, score_offset: int) -> dict:
    """
    Regular 400L student: scores ONLY in current 400L courses.
    Carryover columns (100L/200L/300L) will show '-' automatically.
    """
    s1_scores = {}
    s1_pairs  = []
    for course in FIRST_SEM_COURSES:
        if course['level'] == 400:
            entry = score_for(course, offset=score_offset)
            s1_scores[course['code']] = entry['display']
            s1_pairs.append((course, entry))
        # lower-level columns are intentionally left absent (will display '-')

    s2_scores = {}
    s2_pairs  = []
    for course in SECOND_SEM_COURSES:
        if course['level'] == 400:
            entry = score_for(course, offset=score_offset)
            s2_scores[course['code']] = entry['display']
            s2_pairs.append((course, entry))

    s1_sum = compute_summary(s1_pairs)
    s2_sum = compute_summary(s2_pairs)
    ss_sum = compute_session_summary(s1_sum, s2_sum)
    remark = 'Proceed' if ss_sum['failed_units'] == 0 else 'Resit'

    return {
        'matric_number':           matric,
        'name':                    name,
        'gender':                  gender,
        'first_semester':          s1_scores,
        'second_semester':         s2_scores,
        'first_semester_summary':  s1_sum,
        'second_semester_summary': s2_sum,
        'session_summary':         ss_sum,
        'remark':                  remark,
    }


# ===========================================================================
# 4.  ASSEMBLE ALL STUDENTS
# ===========================================================================

carryover_student = build_carryover_student()

all_students = [carryover_student] + [
    build_regular_student(m, n, g, o) for m, n, g, o in REGULAR_STUDENTS_RAW
]

# ===========================================================================
# 5.  PDF DATA PAYLOAD  (matches generate_spreadsheet_pdf expectations)
# ===========================================================================

# Strip internal helper keys before passing to PDF generator
def clean_student(s: dict) -> dict:
    return {k: v for k, v in s.items() if not k.startswith('_')}


students_payload = [clean_student(s) for s in all_students]

first_courses_data  = [
    {'code': c['code'], 'title': c['title'], 'status': c['status'], 'credit_unit': c['credit_unit']}
    for c in FIRST_SEM_COURSES
]
second_courses_data = [
    {'code': c['code'], 'title': c['title'], 'status': c['status'], 'credit_unit': c['credit_unit']}
    for c in SECOND_SEM_COURSES
]

config = {
    'university_name': Config.UNIVERSITY_NAME,
    'faculty_name':    Config.FACULTY_NAME,
    'department_name': Config.DEPARTMENT_NAME,
}
signatories = {
    'course_adviser': 'Dr. O.A. Egbedokun',
    'hod':            'Prof. E.I. Odion',
    'dean':           'Prof. A.B. Okafor',
}

BASE_DATA = {
    'students':               students_payload,
    'first_semester_courses': first_courses_data,
    'second_semester_courses': second_courses_data,
    'level':   400,
    'program': 'Computer Science',
    'session': '2025/2026',
}


# ===========================================================================
# 6.  GENERATE PDFs
# ===========================================================================

def generate_and_save(semester_key: str, filename: str) -> bool:
    data = {**BASE_DATA, 'semester': semester_key}
    try:
        with app.app_context():
            buf = generate_spreadsheet_pdf(data, config, signatories)
        size = buf.getbuffer().nbytes
        with open(filename, 'wb') as fh:
            fh.write(buf.getvalue())
        print(f"  ✓  {filename}  ({size:,} bytes)")
        return True
    except Exception as exc:
        print(f"  ✗  {filename}  — ERROR: {exc}")
        import traceback; traceback.print_exc()
        return False


# ===========================================================================
# 7.  MAIN
# ===========================================================================

if __name__ == '__main__':
    sep = '=' * 76

    print(sep)
    print("  TEST: 400-Level Carryover Student — PDF Spreadsheet")
    print(sep)

    # ── Course summary ──────────────────────────────────────────────────────
    print(f"\nCourse Layout  (ordered 100L → 400L within each semester)")
    print(f"{'─'*60}")
    print(f"  FIRST SEMESTER  ({len(FIRST_SEM_COURSES)} courses total)")
    print(f"    100L carryover : {len(s1_100l)} courses  ({', '.join(c['code'] for c in s1_100l)})")
    print(f"    200L carryover : {len(s1_200l)} courses  ({', '.join(c['code'] for c in s1_200l)})")
    print(f"    300L carryover : {len(s1_300l)} courses  ({', '.join(c['code'] for c in s1_300l)})")
    print(f"    400L official  : {len(s1_400l)} courses  ({', '.join(c['code'] for c in s1_400l)})")
    print()
    print(f"  SECOND SEMESTER ({len(SECOND_SEM_COURSES)} courses total)")
    print(f"    100L carryover : {len(s2_100l)} course   ({', '.join(c['code'] for c in s2_100l)})")
    print(f"    200L carryover : {len(s2_200l)} course   ({', '.join(c['code'] for c in s2_200l)})")
    print(f"    300L carryover : {len(s2_300l)} courses  ({', '.join(c['code'] for c in s2_300l)})")
    print(f"    400L filled    : {len(s2_400l)} courses  ({', '.join(c['code'] for c in s2_400l)})")
    print(f"                      ↑ These are the 8 courses the student 'filled'")
    print(f"                        (officially enrolled in) for second semester")

    # ── Student summary ─────────────────────────────────────────────────────
    print(f"\nStudent Roster ({len(all_students)} students)")
    print(f"{'─'*60}")
    for i, s in enumerate(all_students, 1):
        s1_cnt = sum(1 for v in s['first_semester'].values()  if v != '-')
        s2_cnt = sum(1 for v in s['second_semester'].values() if v != '-')
        note   = s.get('_note', '')
        tag    = '[CARRYOVER]' if note else '[REGULAR  ]'
        print(f"  {i}. {tag} {s['matric_number']}  {s['name']:<28}  "
              f"S1={s1_cnt:>2} courses  S2={s2_cnt:>2} courses")
        if note:
            print(f"            Note: {note}")

    # ── Generating PDFs ─────────────────────────────────────────────────────
    print(f"\nGenerating PDFs …")
    print(f"{'─'*60}")

    results = {
        'both': generate_and_save('both', 'test_400l_carryover_both_semesters.pdf'),
        'sem1': generate_and_save('1',    'test_400l_carryover_sem1_only.pdf'),
        'sem2': generate_and_save('2',    'test_400l_carryover_sem2_only.pdf'),
    }

    # ── Carryover student detail ────────────────────────────────────────────
    cs = carryover_student
    print(f"\n{'─'*60}")
    print(f"  Carryover student score detail — {cs['matric_number']}  {cs['name']}")
    print(f"{'─'*60}")
    print(f"  FIRST SEMESTER (22 courses):")
    for lvl in [100, 200, 300, 400]:
        lbl = 'carryover' if lvl < 400 else 'official '
        lvl_courses = [c for c in FIRST_SEM_COURSES if c['level'] == lvl]
        scores = [cs['first_semester'].get(c['code'], '-') for c in lvl_courses]
        print(f"    {lvl}L {lbl} : {scores}")
    s1s = cs['first_semester_summary']
    print(f"    → CUF={s1s['failed_units']}  CUP={s1s['passed_units']}  "
          f"TCU={s1s['total_units']}  GPA={s1s['gpa']:.2f}")

    print(f"\n  SECOND SEMESTER (12 courses, incl. 8 filled 400L courses):")
    for lvl in [100, 200, 300, 400]:
        lbl = 'carryover' if lvl < 400 else 'filled   '
        lvl_courses = [c for c in SECOND_SEM_COURSES if c['level'] == lvl]
        scores = [cs['second_semester'].get(c['code'], '-') for c in lvl_courses]
        if lvl_courses:
            print(f"    {lvl}L {lbl} : {scores}")
    s2s = cs['second_semester_summary']
    print(f"    → CUF={s2s['failed_units']}  CUP={s2s['passed_units']}  "
          f"TCU={s2s['total_units']}  GPA={s2s['gpa']:.2f}")

    ss = cs['session_summary']
    print(f"\n  SESSION SUMMARY:")
    print(f"    Total CU registered : {ss['total_units']}")
    print(f"    Total CU passed     : {ss['passed_units']}")
    print(f"    Total CU failed     : {ss['failed_units']}")
    print(f"    CGPA                : {ss['cgpa']:.2f}")
    print(f"    Remark              : {cs['remark']}")

    # ── Final result ────────────────────────────────────────────────────────
    print(f"\n{sep}")
    all_ok = all(results.values())
    if all_ok:
        print("  ALL 3 PDFs generated successfully ✓")
        print(f"  Open 'test_400l_carryover_both_semesters.pdf' to inspect the layout.")
    else:
        print("  One or more PDFs FAILED to generate ✗")
        sys.exit(1)
    print(sep)
