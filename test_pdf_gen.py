from app.utils.minutes_pdf import generate_minutes_pdf

class Dummy:
    pass

rec = Dummy()
rec.title='Test – en dash'
from datetime import date
rec.meeting_date=date.today()
rec.meeting_time='10:00'
rec.venue='Room – 101'
rec.chairperson='Dr. – Smith'
rec.attendees='A – B'
rec.agenda='Item – example'
rec.raw_transcript='Hello – world'
rec.ai_minutes='This is an AI–generated text with en dash – should be fine.'

user=Dummy()
user.full_name='Tester'
rec.created_by=user
rec.status='draft'
rec.created_at=None

bytes_data=generate_minutes_pdf(rec, [])
print('generated pdf length', len(bytes_data))

with open('test_minutes.pdf','wb') as f:
    f.write(bytes_data)
print('wrote test_minutes.pdf')
