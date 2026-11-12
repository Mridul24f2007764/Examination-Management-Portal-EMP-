import re, sys, os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app import create_app
from models import *

@pytest.fixture
def app(tmp_path):
    a = create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/t.db'})
    yield a

def login(c, e, p): return c.post('/login', data={'email': e, 'password': p}, follow_redirects=True)
def reg(c, n, e, r): return c.post('/register', data={'name': n, 'email': e, 'password': 'password1', 'role': r}, follow_redirects=True)
def taken(app):
    with app.app_context(): return Slot.query.get(1).taken()
def day(n): return (date.today() + timedelta(days=n)).isoformat()

def setup_exam(app, cap=1):
    ad = app.test_client(); login(ad, 'admin@epm.local', 'Admin@123')
    ad.post('/admin/courses', data={'code': 'C1', 'name': 'Course', 'description': ''})
    ad.post('/admin/exams', data={'course_id': 1, 'name': 'Viva 1', 'type': 'Viva', 'slot_start': day(-1), 'slot_end': day(5), 'book_start': day(-1), 'book_end': day(10), 'cancel_days': 1})
    ad.post('/admin/exams/1', data={'action': 'rubric', 'criterion': 'Clarity', 'max_marks': '10', 'weight': '1', 'description': ''})
    reg(app.test_client(), 'Ex', 'ex@x.com', 'examiner')
    ad.post('/admin/examiners', data={'uid': 2, 'action': 'approve'})
    ad.post('/admin/exams/1', data={'action': 'status', 'status': 'Slot Creation Open'})
    ex = app.test_client(); login(ex, 'ex@x.com', 'password1')
    ex.post('/examiner/slots', data={'action': 'create', 'exam_id': 1, 'date': day(3), 'start': '10:00', 'end': '11:00', 'capacity': cap})
    ad.post('/admin/exams/1', data={'action': 'status', 'status': 'Booking Open'})
    return ad, ex

def student(app, n):
    c = app.test_client(); reg(c, n, f'{n}@x.com', 'student'); login(c, f'{n}@x.com', 'password1'); return c

def test_admin_seeded_and_no_public_admin(app):
    with app.app_context(): assert User.query.filter_by(role='admin').count() == 1
    assert reg(app.test_client(), 'Bad', 'b@x.com', 'admin').status_code == 400

def test_pending_examiner_cannot_login(app):
    c = app.test_client(); reg(c, 'P', 'p@x.com', 'examiner')
    assert b'awaiting admin approval' in login(c, 'p@x.com', 'password1').data

def test_permissions(app):
    s = student(app, 's1')
    assert s.get('/admin').status_code == 403 and s.get('/examiner').status_code == 403
    assert app.test_client().get('/admin').status_code == 302

def test_slot_validation_and_conflict(app):
    ad, ex = setup_exam(app)
    ad.post('/admin/exams/1', data={'action': 'status', 'status': 'Slot Creation Open'})
    r = ex.post('/examiner/slots', data={'action': 'create', 'exam_id': 1, 'date': day(3), 'start': '10:30', 'end': '11:30', 'capacity': 2}, follow_redirects=True)
    assert b'overlaps' in r.data
    r = ex.post('/examiner/slots', data={'action': 'create', 'exam_id': 1, 'date': day(4), 'start': '12:00', 'end': '11:00', 'capacity': 2}, follow_redirects=True)
    assert b'End time must be after' in r.data

def test_booking_duplicate_overbook_cancel(app):
    ad, ex = setup_exam(app, cap=1)
    a, b = student(app, 'a'), student(app, 'b')
    assert b'Booked:' in a.post('/student/book/1', follow_redirects=True).data
    assert b'already have a booking' in a.post('/student/book/1', follow_redirects=True).data
    assert b'full' in b.post('/student/book/1', follow_redirects=True).data
    assert taken(app) == 1
    a.post('/student/cancel/1'); assert taken(app) == 0
    assert b'Booked:' in b.post('/student/book/1', follow_redirects=True).data

def test_cancel_deadline(app):
    ad, ex = setup_exam(app); a = student(app, 'a'); a.post('/student/book/1')
    with app.app_context(): Exam.query.get(1).cancel_days = 30; db.session.commit()
    assert b'deadline has passed' in a.post('/student/cancel/1', follow_redirects=True).data

def test_evaluation_and_hidden_results(app):
    ad, ex = setup_exam(app); a = student(app, 'a'); a.post('/student/book/1')
    r = ex.post('/examiner/evaluate/1', data={'r1': '11', 'remarks': 'x', 'action': 'submit'}, follow_redirects=True)
    assert b'must be between 0 and 10' in r.data
    ex.post('/examiner/evaluate/1', data={'r1': '8', 'remarks': 'Good', 'action': 'submit'})
    assert b'locked' in ex.post('/examiner/evaluate/1', data={'r1': '9', 'remarks': 'y', 'action': 'submit'}, follow_redirects=True).data
    assert b'Good' not in a.get('/student/results').data
    ad.post('/admin/exams/1', data={'action': 'publish'})
    assert b'Good' in a.get('/student/results').data
    other = student(app, 'z'); assert other.get('/examiner/evaluate/1').status_code == 403

def test_admin_reassign(app):
    ad, ex = setup_exam(app)
    reg(app.test_client(), 'Ex2', 'ex2@x.com', 'examiner'); ad.post('/admin/examiners', data={'uid': 3, 'action': 'approve'})
    ad.post('/admin/bookings', data={'action': 'reassign', 'slot_id': 1, 'examiner_id': 3})
    with app.app_context(): assert Slot.query.get(1).examiner_id == 3
