"""
PDF extraction utilities for past exam result records.

Supports extraction from:
 - Score-sheet PDFs (tables with matric, name, CA, exam columns)
 - Structured text-based PDFs (column headers detected by keyword matching)
"""
import io
import re
import csv
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Public helper
# ──────────────────────────────────────────────────────────────────────────────

def extract_results_from_pdf(file_bytes):
    """
    Extract exam result records from a PDF file.

    Tries pdfplumber table extraction first; falls back to raw text parsing.

    Args:
        file_bytes (bytes): Raw bytes of the uploaded PDF.

    Returns:
        tuple: (records, errors)
            records – list of dicts with keys:
                        matric_number, name (optional), ca_score (optional),
                        exam_score (optional), total_score (optional)
            errors  – list of human-readable error / warning strings
    """
    records = []
    errors = []

    # --- attempt 1: pdfplumber table extraction ------------------------------
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                for table in tables:
                    recs, errs = _parse_table(table, page_num)
                    records.extend(recs)
                    errors.extend(errs)

        if records:
            return records, errors
    except ImportError:
        errors.append("pdfplumber is not installed – falling back to text extraction. "
                      "Run: pip install pdfplumber")
    except Exception as exc:
        errors.append(f"pdfplumber table extraction failed: {exc}")

    # --- attempt 2: raw text extraction -------------------------------------
    try:
        import pdfplumber
        text_records, text_errors = _extract_from_text(file_bytes)
        records.extend(text_records)
        errors.extend(text_errors)
    except ImportError:
        pass
    except Exception as exc:
        errors.append(f"Text-based extraction failed: {exc}")

    if not records:
        errors.append(
            "No result records could be extracted from the PDF. "
            "The file may be scanned (image-only) or in an unsupported format. "
            "Please use the CSV upload option instead."
        )

    return records, errors


def generate_sample_past_results_csv():
    """Return a sample CSV string for past result uploads."""
    lines = [
        "Matric Number,Student Name,CA Score,Exam Score",
        "FSC/CSC/20001,ADEYEMI JOHN OLUWASEUN,25,50",
        "FSC/CBS/20002,OKONKWO MARY CHIDINMA,28,55",
        "FSC/SWE/20003,IBRAHIM AHMED MUSA,20,45",
        "FSC/CSC/CV/19001,OSAGIE GRACE,22,48",
        "2020123456AB,EKHATOR PETER OSAHON,18,40",
    ]
    return "\n".join(lines)


def parse_past_results_csv(file_content):
    """
    Parse past result records from CSV.

    Accepts columns (case-insensitive / flexible order):
        Matric Number | CA Score | Exam Score
        Matric Number | Total Score
        Matric Number | Student Name | CA Score | Exam Score
        Matric Number | Student Name | Total Score

    Returns:
        tuple: (records, errors)
    """
    records = []
    errors = []

    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode("utf-8-sig")

        reader = csv.DictReader(io.StringIO(file_content))
        fieldnames = reader.fieldnames
        if not fieldnames:
            return [], ["CSV file is empty or has no headers."]

        # Map columns
        col = {}
        for f in fieldnames:
            fl = f.lower().strip()
            if "matric" in fl or "reg" in fl or "jamb" in fl:
                col["matric"] = f
            elif "name" in fl:
                col["name"] = f
            elif "ca" in fl or "continuous" in fl or "assessment" in fl:
                col["ca"] = f
            elif "exam" in fl:
                col["exam"] = f
            elif "total" in fl or "score" in fl:
                col.setdefault("total", f)

        if "matric" not in col:
            return [], ["Missing required column: Matric Number (or Reg Number / JAMB No)"]
        if "ca" not in col and "total" not in col:
            return [], ["Missing score columns. Need either 'CA Score' + 'Exam Score', or 'Total Score'."]

        for row_num, row in enumerate(reader, start=2):
            try:
                matric = row.get(col["matric"], "").strip().upper()
                if not matric:
                    errors.append(f"Row {row_num}: Missing matric / reg number – skipped.")
                    continue

                name = row.get(col.get("name", ""), "").strip() or None

                if "ca" in col and "exam" in col:
                    ca_str = row.get(col["ca"], "").strip()
                    exam_str = row.get(col["exam"], "").strip()
                    try:
                        ca = float(ca_str) if ca_str else 0.0
                        exam = float(exam_str) if exam_str else 0.0
                    except ValueError:
                        errors.append(f"Row {row_num} ({matric}): Invalid score value – skipped.")
                        continue

                    if not (0 <= ca <= 30):
                        errors.append(f"Row {row_num} ({matric}): CA score {ca} out of range (0–30) – skipped.")
                        continue
                    if not (0 <= exam <= 70):
                        errors.append(f"Row {row_num} ({matric}): Exam score {exam} out of range (0–70) – skipped.")
                        continue

                    records.append({
                        "matric_number": matric,
                        "name": name,
                        "ca_score": ca,
                        "exam_score": exam,
                        "total_score": round(ca + exam, 1),
                    })

                elif "total" in col:
                    total_str = row.get(col["total"], "").strip()
                    try:
                        total = float(total_str) if total_str else 0.0
                    except ValueError:
                        errors.append(f"Row {row_num} ({matric}): Invalid total score – skipped.")
                        continue

                    if not (0 <= total <= 100):
                        errors.append(f"Row {row_num} ({matric}): Total score {total} out of range (0–100) – skipped.")
                        continue

                    # Estimate CA/Exam split (30/70 ratio – user can override in manual entry)
                    ca_est = round(total * 0.30, 1)
                    exam_est = round(total * 0.70, 1)
                    # Ensure the split sums back to total exactly
                    exam_est = round(total - ca_est, 1)

                    records.append({
                        "matric_number": matric,
                        "name": name,
                        "ca_score": ca_est,
                        "exam_score": exam_est,
                        "total_score": total,
                        "split_estimated": True,
                    })

            except Exception as exc:
                errors.append(f"Row {row_num}: Unexpected error – {exc}")

    except Exception as exc:
        errors.append(f"Error reading CSV: {exc}")

    return records, errors


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

# Regex patterns for matric / JAMB numbers
_MATRIC_RE = re.compile(
    r"FSC/(?:CSC|CBS|SWE)(?:/CV)?/\d+",  # FSC/CSC/CV/20001 style
    re.IGNORECASE,
)
_JAMB_RE = re.compile(r"\d{8,}[A-Z]{0,3}", re.IGNORECASE)   # e.g. 2020123456AB


def _looks_like_matric(text):
    """Return True if text looks like an ESU matric or JAMB number."""
    t = text.strip().upper()
    return bool(_MATRIC_RE.match(t) or _JAMB_RE.match(t))


def _find_column_indices(header_row):
    """
    Given a list of header cells (strings), return a dict mapping
    role → column index for: matric, name, ca, exam, total.
    """
    mapping = {}
    for idx, cell in enumerate(header_row):
        if cell is None:
            continue
        cl = str(cell).lower().strip()
        if any(k in cl for k in ("matric", "reg no", "reg. no", "jamb")):
            mapping["matric"] = idx
        elif any(k in cl for k in ("name", "student")):
            mapping.setdefault("name", idx)
        elif any(k in cl for k in ("c.a", "ca ", " ca", "continuous", "assessment")):
            mapping["ca"] = idx
        elif "exam" in cl:
            mapping["exam"] = idx
        elif any(k in cl for k in ("total", "score", "total score")):
            mapping.setdefault("total", idx)
    return mapping


def _parse_table(table, page_num):
    """Parse a pdfplumber table (list of list of strings)."""
    records = []
    errors = []

    if not table or len(table) < 2:
        return records, errors

    # Find the header row (first row that has recognisable header keywords)
    header_idx = None
    col_map = {}
    for i, row in enumerate(table[:5]):  # only scan first 5 rows for header
        if row is None:
            continue
        row_clean = [str(c).strip() if c else "" for c in row]
        candidate = _find_column_indices(row_clean)
        if "matric" in candidate or (len(candidate) >= 2):
            header_idx = i
            col_map = candidate
            break

    if header_idx is None or "matric" not in col_map:
        # No recognised header – try to auto-detect column from data
        col_map, header_idx = _autodetect_columns(table)
        if col_map is None:
            errors.append(f"Page {page_num}: Could not identify column headers – table skipped.")
            return records, errors

    for row_num, row in enumerate(table[header_idx + 1:], start=1):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue
        row_clean = [str(c).strip() if c else "" for c in row]

        matric = row_clean[col_map["matric"]] if col_map["matric"] < len(row_clean) else ""
        matric = matric.upper().replace(" ", "")
        if not matric or not (_looks_like_matric(matric) or len(matric) >= 5):
            continue  # skip non-data rows (totals, footers, etc.)

        name = None
        if "name" in col_map and col_map["name"] < len(row_clean):
            name = row_clean[col_map["name"]] or None

        record = {"matric_number": matric, "name": name}

        if "ca" in col_map and "exam" in col_map:
            ca_str = row_clean[col_map["ca"]] if col_map["ca"] < len(row_clean) else ""
            exam_str = row_clean[col_map["exam"]] if col_map["exam"] < len(row_clean) else ""
            ca = _safe_float(ca_str)
            exam = _safe_float(exam_str)
            if ca is None or exam is None:
                errors.append(f"Page {page_num}, row {row_num} ({matric}): Invalid CA/Exam score – skipped.")
                continue
            record.update(ca_score=ca, exam_score=exam, total_score=round(ca + exam, 1))
        elif "total" in col_map:
            total_str = row_clean[col_map["total"]] if col_map["total"] < len(row_clean) else ""
            total = _safe_float(total_str)
            if total is None:
                errors.append(f"Page {page_num}, row {row_num} ({matric}): Invalid total score – skipped.")
                continue
            ca_est = round(total * 0.30, 1)
            exam_est = round(total - ca_est, 1)
            record.update(ca_score=ca_est, exam_score=exam_est,
                          total_score=total, split_estimated=True)
        else:
            errors.append(f"Page {page_num}, row {row_num} ({matric}): No score columns found – skipped.")
            continue

        records.append(record)

    return records, errors


def _autodetect_columns(table):
    """
    Try to detect the matric column from data rows when there's no clear header.
    Returns (col_map, header_idx) or (None, None).
    """
    for row_idx, row in enumerate(table):
        if row is None:
            continue
        for col_idx, cell in enumerate(row):
            if cell and _looks_like_matric(str(cell)):
                # Found matric column; now try to find score columns nearby
                col_map = {"matric": col_idx}
                # Look for numeric columns to the right
                numeric_cols = []
                for ci in range(col_idx + 1, len(row)):
                    v = _safe_float(str(row[ci]) if row[ci] else "")
                    if v is not None and 0 <= v <= 100:
                        numeric_cols.append(ci)
                if len(numeric_cols) >= 2:
                    col_map["ca"] = numeric_cols[0]
                    col_map["exam"] = numeric_cols[1]
                elif len(numeric_cols) == 1:
                    col_map["total"] = numeric_cols[0]
                if len(numeric_cols) >= 1:
                    return col_map, max(0, row_idx - 1)
    return None, None


def _extract_from_text(file_bytes):
    """Fallback: extract matric numbers and scores from raw page text."""
    records = []
    errors = []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                recs, errs = _parse_text_lines(text, page_num)
                records.extend(recs)
                errors.extend(errs)
    except Exception as exc:
        errors.append(f"Text extraction error: {exc}")
    return records, errors


def _parse_text_lines(text, page_num):
    """
    Scan lines of extracted text for matric-number-like tokens followed by numbers.
    """
    records = []
    errors = []
    lines = text.splitlines()
    for line in lines:
        tokens = line.split()
        for i, token in enumerate(tokens):
            t = token.upper()
            if _looks_like_matric(t):
                # Collect up to 3 numbers following the matric
                numbers = []
                for j in range(i + 1, min(i + 6, len(tokens))):
                    v = _safe_float(tokens[j])
                    if v is not None and 0 <= v <= 100:
                        numbers.append(v)
                    elif not tokens[j].replace(",", "").replace(".", "").isdigit():
                        # Non-numeric non-score token – stop collecting
                        break

                if len(numbers) >= 2:
                    ca, exam = numbers[0], numbers[1]
                    if 0 <= ca <= 30 and 0 <= exam <= 70:
                        records.append({
                            "matric_number": t,
                            "name": None,
                            "ca_score": ca,
                            "exam_score": exam,
                            "total_score": round(ca + exam, 1),
                        })
                    elif len(numbers) >= 1:
                        total = numbers[-1]
                        ca_e = round(total * 0.30, 1)
                        exam_e = round(total - ca_e, 1)
                        records.append({
                            "matric_number": t,
                            "name": None,
                            "ca_score": ca_e,
                            "exam_score": exam_e,
                            "total_score": total,
                            "split_estimated": True,
                        })
    return records, errors


def _safe_float(s):
    """Convert string to float, returning None on failure."""
    try:
        return float(str(s).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None
