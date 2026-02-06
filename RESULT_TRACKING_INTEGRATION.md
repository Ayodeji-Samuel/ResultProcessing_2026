# Result Alteration Tracking Integration Guide

## Overview
This guide shows how to integrate result alteration tracking into your results routes.

## Import Required Functions

Add to the top of `app/routes/results.py`:

```python
from app.routes.auth import log_result_alteration
from app.models import Student, Course, AcademicSession
```

## Track Result Creation

When creating new results (e.g., after CSV upload or manual entry):

```python
# After creating a new result
result = Result(
    student_id=student.id,
    course_id=course.id,
    session_id=session.id,
    ca_score=ca_score,
    exam_score=exam_score,
    total_score=total_score,
    grade=grade,
    grade_point=grade_point,
    uploaded_by=current_user.id
)
db.session.add(result)
db.session.commit()

# Log the alteration
log_result_alteration(
    result_id=result.id,
    student=student,
    course=course,
    session_name=session.session_name,
    alteration_type='CREATE',
    old_result=None,
    new_result=result,
    reason=f'Result uploaded via {upload_method}'  # e.g., 'CSV', 'Manual Entry'
)
```

## Track Result Updates

When updating existing results (e.g., editing scores):

```python
# Before updating
old_result_copy = type('obj', (object,), {
    'ca_score': result.ca_score,
    'exam_score': result.exam_score,
    'total_score': result.total_score,
    'grade': result.grade,
    'grade_point': result.grade_point
})

# Update the result
result.ca_score = new_ca_score
result.exam_score = new_exam_score
result.total_score = new_total_score
result.grade = new_grade
result.grade_point = new_grade_point
db.session.commit()

# Log the alteration
log_result_alteration(
    result_id=result.id,
    student=result.student,
    course=result.course,
    session_name=result.session.session_name,
    alteration_type='UPDATE',
    old_result=old_result_copy,
    new_result=result,
    reason=request.form.get('reason', 'Manual correction')
)
```

## Track Result Deletion

When deleting results:

```python
# Before deleting
student = result.student
course = result.course
session_name = result.session.session_name

old_result_copy = type('obj', (object,), {
    'ca_score': result.ca_score,
    'exam_score': result.exam_score,
    'total_score': result.total_score,
    'grade': result.grade,
    'grade_point': result.grade_point
})

result_id = result.id

# Delete the result
db.session.delete(result)
db.session.commit()

# Log the alteration
log_result_alteration(
    result_id=result_id,
    student=student,
    course=course,
    session_name=session_name,
    alteration_type='DELETE',
    old_result=old_result_copy,
    new_result=None,
    reason=request.form.get('reason', 'Result deleted')
)
```

## Example: Complete Manual Entry Route

```python
@results_bp.route('/manual-entry', methods=['GET', 'POST'])
@login_required
def manual_entry():
    """Manual result entry with alteration tracking"""
    
    if request.method == 'POST':
        matric = request.form.get('matric_number')
        course_code = request.form.get('course_code')
        ca_score = float(request.form.get('ca_score'))
        exam_score = float(request.form.get('exam_score'))
        
        # Get student, course, session
        student = Student.query.filter_by(matric_number=matric).first()
        course = Course.query.filter_by(course_code=course_code).first()
        session = AcademicSession.query.filter_by(is_current=True).first()
        
        if not student or not course:
            flash('Student or course not found', 'danger')
            return redirect(url_for('results.manual_entry'))
        
        # Calculate total and grade
        total_score = ca_score + exam_score
        grade, grade_point = calculate_grade(total_score, course.degree_type)
        
        # Check if result already exists
        existing = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            session_id=session.id
        ).first()
        
        if existing:
            # UPDATE existing result
            old_result_copy = type('obj', (object,), {
                'ca_score': existing.ca_score,
                'exam_score': existing.exam_score,
                'total_score': existing.total_score,
                'grade': existing.grade,
                'grade_point': existing.grade_point
            })
            
            existing.ca_score = ca_score
            existing.exam_score = exam_score
            existing.total_score = total_score
            existing.grade = grade
            existing.grade_point = grade_point
            db.session.commit()
            
            # Log alteration
            log_result_alteration(
                result_id=existing.id,
                student=student,
                course=course,
                session_name=session.session_name,
                alteration_type='UPDATE',
                old_result=old_result_copy,
                new_result=existing,
                reason='Manual entry update'
            )
            
            flash('Result updated successfully', 'success')
        else:
            # CREATE new result
            result = Result(
                student_id=student.id,
                course_id=course.id,
                session_id=session.id,
                ca_score=ca_score,
                exam_score=exam_score,
                total_score=total_score,
                grade=grade,
                grade_point=grade_point,
                uploaded_by=current_user.id
            )
            db.session.add(result)
            db.session.commit()
            
            # Log alteration
            log_result_alteration(
                result_id=result.id,
                student=student,
                course=course,
                session_name=session.session_name,
                alteration_type='CREATE',
                old_result=None,
                new_result=result,
                reason='Manual entry'
            )
            
            flash('Result created successfully', 'success')
        
        return redirect(url_for('results.manual_entry'))
    
    return render_template('results/manual_entry.html')
```

## Example: Bulk CSV Upload

```python
@results_bp.route('/upload', methods=['POST'])
@login_required
def upload_results():
    """Bulk CSV upload with alteration tracking"""
    
    # Process CSV file
    for row in csv_data:
        student = get_student(row['matric'])
        course = get_course(row['course_code'])
        
        # Check if exists
        existing = Result.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            session_id=session.id
        ).first()
        
        if existing:
            # Track old values before update
            old_result = type('obj', (object,), {
                'ca_score': existing.ca_score,
                'exam_score': existing.exam_score,
                'total_score': existing.total_score,
                'grade': existing.grade
            })
            
            # Update
            existing.ca_score = row['ca']
            existing.exam_score = row['exam']
            # ... update other fields
            
            log_result_alteration(
                result_id=existing.id,
                student=student,
                course=course,
                session_name=session.session_name,
                alteration_type='UPDATE',
                old_result=old_result,
                new_result=existing,
                reason=f'CSV upload: {filename}'
            )
        else:
            # Create new
            result = Result(...)
            db.session.add(result)
            db.session.commit()
            
            log_result_alteration(
                result_id=result.id,
                student=student,
                course=course,
                session_name=session.session_name,
                alteration_type='CREATE',
                old_result=None,
                new_result=result,
                reason=f'CSV upload: {filename}'
            )
    
    db.session.commit()
```

## Important Notes

1. **Always log after commit** - Ensure the result has an ID before logging
2. **Provide meaningful reasons** - Help admins understand why changes were made
3. **Copy old values** - Create a copy before updating to preserve original state
4. **Error handling** - Wrap in try/except to prevent logging failures from breaking operations
5. **Bulk operations** - Log each individual result change, not just the upload

## Optional: Add Reason Field to Forms

Update your result entry forms to include an optional reason field:

```html
<div class="form-group">
    <label>Reason for Change (Optional)</label>
    <textarea name="reason" class="form-control" rows="2" 
              placeholder="Brief explanation of why this result is being modified"></textarea>
</div>
```

Then use it in your tracking:

```python
reason = request.form.get('reason', 'No reason provided')
log_result_alteration(..., reason=reason)
```

## Testing

After integration:

1. Create a result → Check Result Alterations page
2. Update a result → Verify old and new values are shown
3. Delete a result → Confirm deletion is tracked
4. Check device information is captured
5. Verify IP address is logged
6. Test filtering and searching

---

**Integration is optional but recommended for complete audit compliance!**
