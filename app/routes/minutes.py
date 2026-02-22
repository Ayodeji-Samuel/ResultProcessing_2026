"""Meeting Minutes Routes - Voice Recording, AI Transcription & Minutes Generation"""
import json
import os
import requests
from datetime import date, datetime
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, current_app, make_response)
from flask_login import login_required, current_user
from app import db
from app.models import MeetingMinutes

minutes_bp = Blueprint('minutes', __name__)

# ─────────────────────────── helpers ────────────────────────────────────────

# OpenRouter credentials and settings are pulled from environment variables.
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
# base URL for OpenRouter; can be overridden via environment
OPENROUTER_BASE    = os.environ.get('OPENROUTER_BASE', "https://openrouter.ai/api/v1/chat/completions")
# also allow fallback without "/api"
ALT_OPENROUTER_BASE = os.environ.get('ALT_OPENROUTER_BASE', "https://openrouter.ai/v1/chat/completions")

OPENROUTER_MODEL   = os.environ.get('OPENROUTER_MODEL', "google/gemini-flash-1.5")  # fast, capable model

if not OPENROUTER_API_KEY:
    # warn at import time; the routes will still function but AI requests will fail elegantly
    import logging
    logging.getLogger(__name__).warning('OPENROUTER_API_KEY not set in environment')


def call_openrouter(system_prompt: str, user_content: str, temperature: float = 0.3) -> str:
    """Send a chat request to OpenRouter and return the text reply."""
    # headers must be latin-1 encodable per RFC 7230; strip or replace any others
    def clean_header(val: str) -> str:
        return val.encode('latin-1', 'ignore').decode('latin-1')

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": clean_header("https://edsu-results.local"),
        # replace en-dash with hyphen in title header to avoid encoding error
        "X-Title": clean_header("EDSU Result Processing - Meeting Minutes"),
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
    }
    resp = requests.post(OPENROUTER_BASE, headers=headers, json=payload, timeout=120)
    # if not found, try alternate base if provided
    if resp.status_code == 404 and ALT_OPENROUTER_BASE:
        resp = requests.post(ALT_OPENROUTER_BASE, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"OpenRouter returned non-JSON response: {resp.text[:300]}") from exc

    # Handle error messages returned by the API (e.g. rate limit, bad key)
    if "error" in data:
        err = data["error"]
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise RuntimeError(f"OpenRouter API error: {msg}")

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected OpenRouter response structure: {str(data)[:300]}"
        ) from exc


# ─────────────────────────── list ───────────────────────────────────────────

@minutes_bp.route('/')
@login_required
def index():
    """List all meeting minutes for the current user."""
    q = request.args.get('q', '').strip()
    query = MeetingMinutes.query

    # Admins / HoD see everything; others see only their own
    if current_user.role not in ('admin', 'hod'):
        query = query.filter_by(created_by_id=current_user.id)

    if q:
        query = query.filter(MeetingMinutes.title.ilike(f'%{q}%'))

    minutes = query.order_by(MeetingMinutes.meeting_date.desc(),
                             MeetingMinutes.created_at.desc()).all()
    return render_template('minutes/index.html', minutes=minutes, q=q)


# ─────────────────────────── new / record ───────────────────────────────────

@minutes_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Create a new meeting minutes record (with voice recording)."""
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        meeting_date_str = request.form.get('meeting_date', '')
        meeting_time = request.form.get('meeting_time', '').strip()
        venue       = request.form.get('venue', '').strip()
        chairperson = request.form.get('chairperson', '').strip()
        attendees   = request.form.get('attendees', '').strip()
        agenda      = request.form.get('agenda', '').strip()
        transcript  = request.form.get('transcript', '').strip()

        if not title or not meeting_date_str:
            flash('Title and meeting date are required.', 'danger')
            return render_template('minutes/new.html')

        try:
            meeting_date = date.fromisoformat(meeting_date_str)
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('minutes/new.html')

        record = MeetingMinutes(
            title=title,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            venue=venue,
            chairperson=chairperson,
            attendees=attendees,
            agenda=agenda,
            raw_transcript=transcript,
            status='draft',
            created_by_id=current_user.id,
        )
        db.session.add(record)
        db.session.commit()
        flash('Meeting saved. You can now generate AI minutes.', 'success')
        return redirect(url_for('minutes.view', meeting_id=record.id))

    return render_template('minutes/new.html', today=date.today().isoformat())


# ─────────────────────────── view ───────────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>')
@login_required
def view(meeting_id):
    """View a saved meeting minutes record."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    action_items = []
    if record.action_items:
        try:
            action_items = json.loads(record.action_items)
        except (json.JSONDecodeError, TypeError):
            action_items = []
    return render_template('minutes/view.html', record=record,
                           action_items=action_items)


# ─────────────────────────── edit ───────────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(meeting_id):
    """Edit meeting metadata and/or transcript."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)

    if request.method == 'POST':
        record.title        = request.form.get('title', record.title).strip()
        record.venue        = request.form.get('venue', '').strip()
        record.chairperson  = request.form.get('chairperson', '').strip()
        record.attendees    = request.form.get('attendees', '').strip()
        record.agenda       = request.form.get('agenda', '').strip()
        record.raw_transcript = request.form.get('transcript', '').strip()

        date_str = request.form.get('meeting_date', '')
        if date_str:
            try:
                record.meeting_date = date.fromisoformat(date_str)
            except ValueError:
                pass
        record.meeting_time = request.form.get('meeting_time', '').strip()
        record.updated_at   = datetime.utcnow()
        db.session.commit()
        flash('Meeting updated successfully.', 'success')
        return redirect(url_for('minutes.view', meeting_id=record.id))

    return render_template('minutes/edit.html', record=record)


# ─────────────────────────── delete ─────────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>/delete', methods=['POST'])
@login_required
def delete(meeting_id):
    """Delete a meeting minutes record."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    db.session.delete(record)
    db.session.commit()
    flash('Meeting minutes deleted.', 'success')
    return redirect(url_for('minutes.index'))


# ─────────────────────────── finalize ───────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>/finalize', methods=['POST'])
@login_required
def finalize(meeting_id):
    """Mark meeting minutes as finalized."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    record.status = 'finalized'
    record.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Meeting minutes finalized.', 'success')
    return redirect(url_for('minutes.view', meeting_id=record.id))


# ─────────────────────────── AI endpoints ───────────────────────────────────

@minutes_bp.route('/api/generate-minutes', methods=['POST'])
@login_required
def api_generate_minutes():
    """Generate AI-formatted minutes from a transcript (AJAX)."""
    try:
        body = request.get_json(force=True, silent=True) or {}
        transcript       = (body.get('transcript') or '').strip()
        title            = (body.get('title') or 'Meeting').strip()
        meeting_date_str = (body.get('meeting_date') or '').strip()
        venue            = (body.get('venue') or '').strip()
        chairperson      = (body.get('chairperson') or '').strip()
        attendees        = (body.get('attendees') or '').strip()
        agenda           = (body.get('agenda') or '').strip()
        meeting_id       = body.get('meeting_id')

        if not transcript:
            return jsonify({'error': 'Transcript is empty. Please add some meeting notes or record audio first.'}), 400

        system_prompt = (
            "You are an expert professional secretary specializing in preparing formal, "
            "well-structured meeting minutes for academic/university settings. "
            "Your output must be clean Markdown with proper headings, numbered lists, "
            "bold names, and action items clearly separated. Be thorough but concise."
        )

        context = f"""Meeting Title  : {title}
Date           : {meeting_date_str}
Venue          : {venue}
Chairperson    : {chairperson}
Attendees      : {attendees}
Agenda         : {agenda}

--- RAW TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---

Please produce:
1. A **formal Minutes of Meeting** document (with numbered agenda items, discussions, resolutions).
2. A clearly labelled **Action Items** table at the bottom with columns: #, Action, Responsible, Deadline.
3. A **Closing** section with date/time and Chairperson's name.

Format everything in professional Markdown."""

        ai_text = call_openrouter(system_prompt, context, temperature=0.3)

        # Extract action items as JSON for DB storage
        action_items_json = _extract_action_items(ai_text)

        # Persist if meeting_id provided
        if meeting_id:
            record = MeetingMinutes.query.get(int(meeting_id))
            if record and (record.created_by_id == current_user.id
                           or current_user.role in ('admin', 'hod')):
                record.ai_minutes   = ai_text
                record.action_items = json.dumps(action_items_json)
                record.updated_at   = datetime.utcnow()
                db.session.commit()

        return jsonify({'minutes': ai_text, 'action_items': action_items_json})

    except Exception as exc:
        current_app.logger.error(f"api_generate_minutes error: {exc}", exc_info=True)
        return jsonify({'error': str(exc)}), 500


@minutes_bp.route('/api/enhance-transcript', methods=['POST'])
@login_required
def api_enhance_transcript():
    """Clean up / enhance a raw voice transcript (AJAX)."""
    try:
        body       = request.get_json(force=True, silent=True) or {}
        transcript = (body.get('transcript') or '').strip()

        if not transcript:
            return jsonify({'error': 'Transcript is empty.'}), 400

        system_prompt = (
            "You are a professional transcription editor. "
            "Fix grammar, remove filler words, correct obvious speech-recognition errors, "
            "and return only the cleaned transcript text with no extra commentary."
        )

        cleaned = call_openrouter(system_prompt, transcript, temperature=0.2)
        return jsonify({'transcript': cleaned})

    except Exception as exc:
        current_app.logger.error(f"api_enhance_transcript error: {exc}", exc_info=True)
        return jsonify({'error': str(exc)}), 500


# ─────────────────────────── PDF export ─────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>/pdf')
@login_required
def export_pdf(meeting_id):
    """Generate and download PDF of the meeting minutes."""
    from app.utils.minutes_pdf import generate_minutes_pdf   # lazy import

    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)

    action_items = []
    if record.action_items:
        try:
            action_items = json.loads(record.action_items)
        except (json.JSONDecodeError, TypeError):
            action_items = []

    pdf_bytes = generate_minutes_pdf(record, action_items)

    safe_title = "".join(c if c.isalnum() or c in ' _-' else '_' for c in record.title)
    filename   = f"Minutes_{safe_title}_{record.meeting_date}.pdf"

    response = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ─────────────────────────── internal helpers ─────────────────────────────

def _check_access(record: MeetingMinutes):
    """Abort with 403 if current user has no access to this record."""
    from flask import abort
    if (record.created_by_id != current_user.id
            and current_user.role not in ('admin', 'hod')):
        abort(403)


def _extract_action_items(markdown_text: str) -> list:
    """Rudimentary extraction of action items from AI markdown output."""
    items = []
    in_table = False
    for line in markdown_text.splitlines():
        stripped = line.strip()
        # Detect table rows that contain 3+ pipe separators
        if stripped.startswith('|') and stripped.count('|') >= 3:
            # Skip header and separator rows
            if '---' in stripped or 'Action' in stripped:
                in_table = True
                continue
            if in_table:
                parts = [p.strip() for p in stripped.split('|') if p.strip()]
                if len(parts) >= 2:
                    items.append({
                        'action':      parts[1] if len(parts) > 1 else parts[0],
                        'responsible': parts[2] if len(parts) > 2 else '',
                        'deadline':    parts[3] if len(parts) > 3 else '',
                    })
        elif in_table and not stripped.startswith('|'):
            in_table = False
    return items
