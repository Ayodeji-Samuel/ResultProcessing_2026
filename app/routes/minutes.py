"""Meeting Minutes Routes - Voice Recording, AI Transcription, Minutes Generation & Attendance"""
import json
import os
import secrets
import hashlib
from datetime import date, datetime, timedelta

import requests
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, jsonify, current_app, make_response, abort)
from flask_login import login_required, current_user
from app import db, csrf
from app.models import MeetingMinutes, AttendanceToken, MeetingAttendee, KnownAttendee

minutes_bp = Blueprint('minutes', __name__)

# ─────────────────────────── helpers ────────────────────────────────────────

# OpenRouter credentials and settings are pulled from environment variables.
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
# base URL for OpenRouter; can be overridden via environment
OPENROUTER_BASE    = os.environ.get('OPENROUTER_BASE', "https://openrouter.ai/api/v1/chat/completions")
# also allow fallback without "/api"
ALT_OPENROUTER_BASE = os.environ.get('ALT_OPENROUTER_BASE', "https://openrouter.ai/v1/chat/completions")

OPENROUTER_MODEL   = os.environ.get('OPENROUTER_MODEL', "google/gemini-2.5-flash")  # fast, capable model

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
    # Only try alternate base on 404 if the primary returned non-JSON (i.e. a
    # proxy/CDN 404, not an API-level 404 with a JSON error body).
    if resp.status_code == 404 and ALT_OPENROUTER_BASE:
        try:
            # If the body is already valid JSON from the API, don't retry –
            # it's a real model-not-found / route error from the API itself.
            resp.json()
            # JSON decoded fine → it is an API error; keep resp as-is and fall
            # through to the error handler below.
        except ValueError:
            # Non-JSON 404 (e.g. a CDN page) → try the alternate base URL.
            resp = requests.post(ALT_OPENROUTER_BASE, headers=headers, json=payload, timeout=120)

    # capture details for debugging
    status = resp.status_code
    text = resp.text
    if status >= 400:
        # Try to surface the API error message if the body is JSON
        try:
            err_data = resp.json()
            if 'error' in err_data:
                err_msg = err_data['error']
                msg = err_msg.get('message', str(err_msg)) if isinstance(err_msg, dict) else str(err_msg)
                raise RuntimeError(f"OpenRouter API error ({status}): {msg}")
        except (ValueError, RuntimeError):
            pass
        msg = f"OpenRouter HTTP {status}: {text[:1000]}"
        if current_app:
            current_app.logger.error(msg)
        resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError as exc:
        # log full body for investigation
        if current_app:
            current_app.logger.error("OpenRouter non-JSON response:\n" + text)
        raise RuntimeError(f"OpenRouter returned non-JSON response (status {status}); see logs for details") from exc

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

        # Auto-generate an attendance token so the link is immediately available
        tok = AttendanceToken(
            meeting_id    = record.id,
            token         = secrets.token_urlsafe(32),
            created_by_id = current_user.id,
            expires_at    = None,
            is_active     = True,
        )
        db.session.add(tok)
        db.session.commit()

        flash('Meeting saved! Share the attendance link below before you start recording.', 'success')
        # Re-render the same page with the record and token so the user sees
        # the attendance link immediately, without leaving the recording page.
        return render_template('minutes/new.html',
                               today=date.today().isoformat(),
                               record=record,
                               token=tok,
                               host_url=request.host_url.rstrip('/'))

    return render_template('minutes/new.html', today=date.today().isoformat())


# ─────────────────────────── quick-start (AJAX) ─────────────────────────────

@minutes_bp.route('/api/quick-start', methods=['POST'])
@login_required
def api_quick_start():
    """AJAX: Create a minimal meeting record + attendance token in one step.

    Called from the new-meeting page so the host can share the attendance link
    the moment the meeting begins — before they have finished filling in all
    details and before any recording starts.  Members who sign in via the link
    can record a short voice introduction so the AI can attribute contributions
    to speakers when generating minutes later.
    """
    body = request.get_json(force=True, silent=True) or {}
    title = (body.get('title') or '').strip() or 'Untitled Meeting'
    meeting_date_str = (body.get('meeting_date') or '').strip()
    try:
        meeting_date = date.fromisoformat(meeting_date_str) if meeting_date_str else date.today()
    except ValueError:
        meeting_date = date.today()

    record = MeetingMinutes(
        title         = title,
        meeting_date  = meeting_date,
        meeting_time  = (body.get('meeting_time') or '').strip(),
        venue         = (body.get('venue')        or '').strip(),
        chairperson   = (body.get('chairperson')  or '').strip(),
        status        = 'draft',
        created_by_id = current_user.id,
    )
    db.session.add(record)
    db.session.commit()

    tok = AttendanceToken(
        meeting_id    = record.id,
        token         = secrets.token_urlsafe(32),
        created_by_id = current_user.id,
        expires_at    = None,
        is_active     = True,
    )
    db.session.add(tok)
    db.session.commit()

    return jsonify({
        'ok':        True,
        'meeting_id': record.id,
        'attend_url': request.host_url.rstrip('/') + url_for('minutes.attend', token=tok.token),
        'edit_url':   url_for('minutes.edit', meeting_id=record.id),
    })


# ─────────────────────────── view ───────────────────────────────────────────

@minutes_bp.route('/<int:meeting_id>')
@login_required
def view(meeting_id):
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    action_items = []
    if record.action_items:
        try:
            action_items = json.loads(record.action_items)
        except (json.JSONDecodeError, TypeError):
            action_items = []
    tokens    = AttendanceToken.query.filter_by(meeting_id=meeting_id).order_by(
                    AttendanceToken.created_at.desc()).all()
    submitted = MeetingAttendee.query.filter_by(meeting_id=meeting_id).order_by(
                    MeetingAttendee.submitted_at).all()
    return render_template('minutes/view.html', record=record,
                           action_items=action_items, tokens=tokens,
                           submitted=submitted)


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
        # If the update came from the new-meeting recording page, stay there
        # so the user can still see the attendance link and continue recording.
        if request.form.get('_source') == 'new':
            tok = AttendanceToken.query.filter_by(
                meeting_id=record.id, is_active=True
            ).order_by(AttendanceToken.created_at.desc()).first()
            return render_template('minutes/new.html',
                                   today=date.today().isoformat(),
                                   record=record,
                                   token=tok,
                                   host_url=request.host_url.rstrip('/'))
        return redirect(url_for('minutes.view', meeting_id=record.id))

    return render_template('minutes/edit.html', record=record)


# ───────────────────── save AI minutes text (inline edit) ─────────────────────

@minutes_bp.route('/<int:meeting_id>/save-minutes', methods=['POST'])
@login_required
def save_minutes_text(meeting_id):
    """Save inline-edited AI minutes text (AJAX)."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Empty text.'}), 400
    record.ai_minutes   = text
    record.updated_at   = datetime.utcnow()
    action_items        = _extract_action_items(text)
    record.action_items = json.dumps(action_items)
    db.session.commit()
    return jsonify({'ok': True, 'action_items': action_items})


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
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    # Revoke all active attendance tokens when meeting is finalized
    for tok in record.tokens:
        tok.is_active = False
    record.status     = 'finalized'
    record.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Meeting minutes finalized and all attendance links revoked.', 'success')
    return redirect(url_for('minutes.view', meeting_id=record.id))


# ─────────────────────────── attendance link ──────────────────────────────────

@minutes_bp.route('/<int:meeting_id>/attendance-link', methods=['POST'])
@login_required
def create_attendance_link(meeting_id):
    """Generate a shareable attendance link for this meeting."""
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    expire_hours_str = request.form.get('expire_hours', '').strip()
    expires_at = None
    if expire_hours_str and expire_hours_str.isdigit() and int(expire_hours_str) > 0:
        expires_at = datetime.utcnow() + timedelta(hours=int(expire_hours_str))
    tok = AttendanceToken(
        meeting_id    = meeting_id,
        token         = secrets.token_urlsafe(32),
        created_by_id = current_user.id,
        expires_at    = expires_at,
        is_active     = True,
    )
    db.session.add(tok)
    db.session.commit()
    flash('Attendance link generated. Share it with meeting members.', 'success')
    return redirect(url_for('minutes.view', meeting_id=meeting_id))


@minutes_bp.route('/attendance-token/<int:token_id>/revoke', methods=['POST'])
@login_required
def revoke_attendance_token(token_id):
    tok = AttendanceToken.query.get_or_404(token_id)
    _check_access(tok.meeting)
    tok.is_active = False
    db.session.commit()
    flash('Attendance link revoked.', 'success')
    return redirect(url_for('minutes.view', meeting_id=tok.meeting_id))


# ─────────────────────────── import submitted attendees ───────────────────────

@minutes_bp.route('/<int:meeting_id>/import-attendees', methods=['POST'])
@login_required
def import_attendees(meeting_id):
    record = MeetingMinutes.query.get_or_404(meeting_id)
    _check_access(record)
    submitted = MeetingAttendee.query.filter_by(meeting_id=meeting_id).all()
    if not submitted:
        flash('No submitted attendances to import.', 'warning')
        return redirect(url_for('minutes.view', meeting_id=meeting_id))
    existing = {n.strip().lower() for n in (record.attendees or '').split(',') if n.strip()}
    new_names = []
    for a in submitted:
        display = a.display_name()
        if display.lower() not in existing:
            new_names.append(display)
            existing.add(display.lower())
    if new_names:
        base       = record.attendees.rstrip(', ') if record.attendees else ''
        record.attendees  = (base + ', ' if base else '') + ', '.join(new_names)
        record.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'{len(new_names)} attendee(s) imported.', 'success')
    else:
        flash('All submitted attendees already listed.', 'info')
    return redirect(url_for('minutes.view', meeting_id=meeting_id))


# ─────────────────────────── public attendance form ───────────────────────────

@minutes_bp.route('/attend/<token>', methods=['GET', 'POST'])
@csrf.exempt
def attend(token):
    """Public attendance form – no login required."""
    tok = AttendanceToken.query.filter_by(token=token).first_or_404()
    if not tok.is_valid:
        return render_template('minutes/attend_closed.html',
                               reason='This attendance link has expired or been revoked.')
    record = tok.meeting

    if request.method == 'POST':
        full_name  = (request.form.get('full_name')  or '').strip()
        email      = (request.form.get('email')      or '').strip().lower()
        department = (request.form.get('department') or '').strip()
        rank       = (request.form.get('rank')       or '').strip()
        distance   = (request.form.get('distance_km') or '').strip()

        if not full_name:
            return render_template('minutes/attend.html', tok=tok, record=record,
                                   error='Full name is required.')
        # Prevent duplicate submission per email
        if email:
            if MeetingAttendee.query.filter_by(meeting_id=record.id, email=email).first():
                return render_template('minutes/attend.html', tok=tok, record=record,
                                       error='You have already submitted attendance for this meeting.',
                                       already_submitted=True)

        distance_km = None
        try:
            if distance:
                distance_km = float(distance)
        except ValueError:
            pass

        attendee = MeetingAttendee(
            meeting_id  = record.id,
            token_id    = tok.id,
            full_name   = full_name,
            email       = email or None,
            department  = department or None,
            rank        = rank or None,
            distance_km = distance_km,
        )
        db.session.add(attendee)

        # Handle optional voice sample
        voice_file = request.files.get('voice_sample')
        if email and voice_file and voice_file.filename:
            voice_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'voice_profiles')
            os.makedirs(voice_dir, exist_ok=True)
            import hashlib as _hl
            safe_name = _hl.md5(email.encode()).hexdigest() + '.webm'
            voice_file.save(os.path.join(voice_dir, safe_name))
            profile = KnownAttendee.query.filter_by(email=email).first()
            if not profile:
                profile = KnownAttendee(email=email, full_name=full_name,
                                        department=department, rank=rank)
                db.session.add(profile)
            else:
                profile.full_name  = full_name
                profile.department = department or profile.department
                profile.rank       = rank or profile.rank
                profile.updated_at = datetime.utcnow()
            profile.has_voice_sample = True
            profile.voice_filename   = safe_name
        elif email:
            profile = KnownAttendee.query.filter_by(email=email).first()
            if not profile:
                profile = KnownAttendee(email=email, full_name=full_name,
                                        department=department, rank=rank)
                db.session.add(profile)
            else:
                profile.full_name  = full_name
                profile.department = department or profile.department
                profile.rank       = rank or profile.rank
                profile.updated_at = datetime.utcnow()

        db.session.commit()
        return render_template('minutes/attend_success.html', record=record, attendee=attendee)

    return render_template('minutes/attend.html', tok=tok, record=record)


@minutes_bp.route('/attend/profile-check', methods=['POST'])
@csrf.exempt
def profile_check():
    """AJAX: Check if an email has a saved voice / profile (public, no auth)."""
    body  = request.get_json(force=True, silent=True) or {}
    email = (body.get('email') or '').strip().lower()
    if not email:
        return jsonify({'known': False})
    profile = KnownAttendee.query.filter_by(email=email).first()
    if not profile:
        return jsonify({'known': False})
    return jsonify({
        'known':            True,
        'full_name':        profile.full_name,
        'department':       profile.department or '',
        'rank':             profile.rank or '',
        'has_voice_sample': profile.has_voice_sample,
    })


# ─────────────────────────── AI endpoints ───────────────────────────────────

@minutes_bp.route('/api/generate-minutes', methods=['POST'])
@login_required
def api_generate_minutes():
    """Generate AI-formatted minutes from a transcript (AJAX)."""
    try:
        body             = request.get_json(force=True, silent=True) or {}
        transcript       = (body.get('transcript')    or '').strip()
        title            = (body.get('title')         or 'Meeting').strip()
        meeting_date_str = (body.get('meeting_date')  or '').strip()
        meeting_time_str = (body.get('meeting_time')  or '').strip()
        venue            = (body.get('venue')         or '').strip()
        chairperson      = (body.get('chairperson')   or '').strip()
        attendees        = (body.get('attendees')     or '').strip()
        agenda           = (body.get('agenda')        or '').strip()
        meeting_id       = body.get('meeting_id')

        if not transcript:
            return jsonify({'error': 'Transcript is empty. Please add some meeting notes or record audio first.'}), 400

        # Build known-speaker hints from submitted attendees
        speaker_hints = ''
        if meeting_id:
            submitted = MeetingAttendee.query.filter_by(meeting_id=int(meeting_id)).all()
            if submitted:
                names = [a.display_name() for a in submitted]
                speaker_hints = (
                    'Known meeting participants (use these names to attribute speaker contributions): '
                    + ', '.join(names) + '.'
                )

        def _val(v): return v if v else 'Not specified'

        system_prompt = (
            'You are an expert professional secretary specialising in preparing formal, '
            'well-structured meeting minutes for academic/university settings. '
            'Your output must be clean Markdown with proper headings, numbered lists, '
            'bold names, and action items clearly separated.\n'
            'IMPORTANT RULES:\n'
            '- Do NOT use placeholder text like "[to be inserted]", "[unknown]", or similar.\n'
            '- If a field value is "Not specified", omit that line from the header block entirely.\n'
            '- Attribute contributions to specific speakers by name wherever the transcript makes it identifiable.\n'
            '- Be thorough but concise.'
        )

        context = (
            f'Meeting Title : {_val(title)}\n'
            f'Date          : {_val(meeting_date_str)}\n'
            + (f'Time          : {meeting_time_str}\n' if meeting_time_str else '')
            + (f'Venue         : {venue}\n' if venue else '')
            + (f'Chairperson   : {chairperson}\n' if chairperson else '')
            + (f'Attendees     : {attendees}\n' if attendees else '')
            + (f'Agenda        : {agenda}\n' if agenda else '')
            + (f'{speaker_hints}\n' if speaker_hints else '')
            + f'\n--- RAW TRANSCRIPT ---\n{transcript}\n--- END TRANSCRIPT ---\n\n'
            'Please produce:\n'
            '1. A **formal Minutes of Meeting** document (header block, numbered agenda items, discussions, resolutions).\n'
            '2. A clearly labelled **Action Items** table: # | Action | Responsible | Deadline.\n'
            '3. A **Closing** section noting date/time and Chairperson.\n\n'
            'Format everything in professional Markdown.'
        )

        ai_text           = call_openrouter(system_prompt, context, temperature=0.3)
        action_items_json = _extract_action_items(ai_text)

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
        current_app.logger.error(f'api_generate_minutes error: {exc}', exc_info=True)
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
