"""CSV processing utility functions"""
import csv
import io
from werkzeug.utils import secure_filename


def allowed_file(filename, allowed_extensions):
    """
    Check if file has an allowed extension.
    
    Args:
        filename: The filename to check
        allowed_extensions: Set of allowed extensions
    
    Returns:
        bool: True if allowed, False otherwise
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def parse_student_csv(file_content):
    """
    Parse student records from CSV file.
    Expected columns: Matric Number, Surname, First Name, Other Names (optional)
    
    Args:
        file_content: The CSV file content (string or file object)
    
    Returns:
        tuple: (records, errors)
            records: List of dicts with student data
            errors: List of error messages
    """
    records = []
    errors = []
    
    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')  # Handle BOM
        
        reader = csv.DictReader(io.StringIO(file_content))
        
        # Normalize column names
        fieldnames = reader.fieldnames
        if not fieldnames:
            return ([], ['CSV file is empty or has no headers'])
        
        # Map expected column names (case-insensitive)
        column_map = {}
        for field in fieldnames:
            field_lower = field.lower().strip()
            if 'matric' in field_lower:
                column_map['matric_number'] = field
            elif 'surname' in field_lower or 'last' in field_lower:
                column_map['surname'] = field
            elif 'first' in field_lower:
                column_map['first_name'] = field
            elif 'other' in field_lower or 'middle' in field_lower:
                column_map['other_names'] = field
        
        # Validate required columns
        required = ['matric_number', 'surname', 'first_name']
        missing = [col for col in required if col not in column_map]
        if missing:
            return ([], [f'Missing required columns: {", ".join(missing)}'])
        
        for row_num, row in enumerate(reader, start=2):
            try:
                matric = row.get(column_map['matric_number'], '').strip()
                surname = row.get(column_map['surname'], '').strip()
                first_name = row.get(column_map['first_name'], '').strip()
                other_names = row.get(column_map.get('other_names', ''), '').strip() if 'other_names' in column_map else ''
                
                if not matric:
                    errors.append(f'Row {row_num}: Missing matric number')
                    continue
                if not surname:
                    errors.append(f'Row {row_num}: Missing surname')
                    continue
                if not first_name:
                    errors.append(f'Row {row_num}: Missing first name')
                    continue
                
                records.append({
                    'matric_number': matric.upper(),
                    'surname': surname.upper(),
                    'first_name': first_name.title(),
                    'other_names': other_names.title() if other_names else None
                })
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
    except Exception as e:
        errors.append(f'Error parsing CSV: {str(e)}')
    
    return (records, errors)


def parse_results_csv(file_content):
    """
    Parse results from CSV file.
    Expected columns: Matric Number, CA Score, Exam Score
    
    Args:
        file_content: The CSV file content
    
    Returns:
        tuple: (records, errors)
            records: List of dicts with result data
            errors: List of error messages
    """
    records = []
    errors = []
    
    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8-sig')
        
        reader = csv.DictReader(io.StringIO(file_content))
        
        fieldnames = reader.fieldnames
        if not fieldnames:
            return ([], ['CSV file is empty or has no headers'])
        
        # Map expected column names (case-insensitive)
        column_map = {}
        for field in fieldnames:
            field_lower = field.lower().strip()
            if 'matric' in field_lower:
                column_map['matric_number'] = field
            elif 'ca' in field_lower or 'continuous' in field_lower or 'assessment' in field_lower:
                column_map['ca_score'] = field
            elif 'exam' in field_lower:
                column_map['exam_score'] = field
        
        # Validate required columns
        required = ['matric_number', 'ca_score', 'exam_score']
        missing = [col for col in required if col not in column_map]
        if missing:
            return ([], [f'Missing required columns: {", ".join(missing)}. Expected: Matric Number, CA Score, Exam Score'])
        
        for row_num, row in enumerate(reader, start=2):
            try:
                matric = row.get(column_map['matric_number'], '').strip()
                ca_score_str = row.get(column_map['ca_score'], '').strip()
                exam_score_str = row.get(column_map['exam_score'], '').strip()
                
                if not matric:
                    errors.append(f'Row {row_num}: Missing matric number')
                    continue
                
                try:
                    ca_score = float(ca_score_str) if ca_score_str else 0
                except ValueError:
                    errors.append(f'Row {row_num}: Invalid CA score "{ca_score_str}"')
                    continue
                
                try:
                    exam_score = float(exam_score_str) if exam_score_str else 0
                except ValueError:
                    errors.append(f'Row {row_num}: Invalid Exam score "{exam_score_str}"')
                    continue
                
                # Validate score ranges
                if ca_score < 0 or ca_score > 30:
                    errors.append(f'Row {row_num}: CA score must be between 0 and 30 (got {ca_score})')
                    continue
                
                if exam_score < 0 or exam_score > 70:
                    errors.append(f'Row {row_num}: Exam score must be between 0 and 70 (got {exam_score})')
                    continue
                
                records.append({
                    'matric_number': matric.upper(),
                    'ca_score': ca_score,
                    'exam_score': exam_score,
                    'total_score': ca_score + exam_score
                })
            except Exception as e:
                errors.append(f'Row {row_num}: {str(e)}')
        
    except Exception as e:
        errors.append(f'Error parsing CSV: {str(e)}')
    
    return (records, errors)


def generate_sample_student_csv():
    """
    Generate a sample student CSV file content.
    
    Returns:
        str: Sample CSV content
    """
    content = "Matric Number,Surname,First Name,Other Names\n"
    content += "CSC/2023/001,ADEYEMI,John,Oluwaseun\n"
    content += "CSC/2023/002,OKONKWO,Mary,Chidinma\n"
    content += "CSC/2023/003,IBRAHIM,Ahmed,Musa\n"
    return content


def generate_sample_results_csv():
    """
    Generate a sample results CSV file content.
    
    Returns:
        str: Sample CSV content
    """
    content = "Matric Number,CA Score,Exam Score\n"
    content += "CSC/2023/001,25,50\n"
    content += "CSC/2023/002,28,55\n"
    content += "CSC/2023/003,20,45\n"
    return content
