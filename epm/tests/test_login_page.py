"""Tests for the redesigned login page. They drive the real Flask app and a throwaway SQLite database."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from app import create_app
from models import *

ADMIN = ('admin@epm.local', 'Admin@123')

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'WTF_CSRF_ENABLED': False, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/t.db'})

@pytest.fixture
def csrf_app(tmp_path):  # CSRF protection on, as in production
    return create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path}/c.db'})

def post_login(c, e, p, **extra): return c.post('/login', data={'email': e, 'password': p, **extra})
def register(c, name, email, role): return c.post('/register', data={'name': name, 'email': email, 'password': 'password1', 'role': role})
def set_status(app, email, status):
    with app.app_context():
        u = User.query.filter_by(email=email).first(); u.status = status; db.session.commit()

# ---- page rendering ----
def test_page_structure(app):
    r = app.test_client().get('/login'); h = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'Welcome back' in h and 'Sign in to access your examination dashboard.' in h
    assert 'A smarter way to manage examinations, schedules and academic assessments.' in h
    for feat in ('Smart Examination Scheduling', 'Secure Role-Based Access', 'Transparent Evaluation Management'): assert feat in h
    assert re.search(r'<form method="post" action="/login"', h)
    assert 'name="csrf_token"' in h
    assert re.search(r'<input id="lp-password" name="password" type="password"', h)
    assert 'href="/register"' in h
    assert 'name="role"' not in h                      # no client-side role selector
    assert 'remember' not in h.lower() and 'forgot' not in h.lower()   # unsupported features are not shown
    assert '/static/login.css' in h and '<script src' not in h and 'http://' not in h and 'https://' not in h.replace('https://openfontlicense', '')  # no external resources

def test_static_assets_served(app):
    c = app.test_client()
    for path in ('/static/login.css', '/static/fonts/manrope-latin-wght-normal.woff2', '/static/fonts/source-serif-4-latin-wght-normal.woff2', '/static/style.css'):
        assert c.get(path).status_code == 200, path

def test_register_link_works_and_admin_not_registrable(app):
    c = app.test_client()
    assert c.get('/register').status_code == 200
    assert register(c, 'Bad', 'bad@x.com', 'admin').status_code == 400

# ---- role-based sign-in and redirects ----
def test_admin_login_redirects_to_admin_dashboard(app):
    c = app.test_client(); r = post_login(c, *ADMIN)
    assert r.status_code == 302 and r.headers['Location'].endswith('/home')
    r = c.get('/home'); assert r.headers['Location'].endswith('/admin')
    assert c.get('/admin').status_code == 200

def test_student_login_redirects_to_student_dashboard(app):
    c = app.test_client(); register(c, 'Stu', 's@x.com', 'student')
    assert post_login(c, 's@x.com', 'password1').status_code == 302
    assert c.get('/home').headers['Location'].endswith('/student')
    assert c.get('/student').status_code == 200
    assert c.get('/admin').status_code == 403 and c.get('/examiner').status_code == 403

def test_approved_examiner_login_redirects_to_examiner_dashboard(app):
    c = app.test_client(); register(c, 'Ex', 'e@x.com', 'examiner')
    set_status(app, 'e@x.com', 'active')               # what Admin > Examiners > Approve does
    assert post_login(c, 'e@x.com', 'password1').status_code == 302
    assert c.get('/home').headers['Location'].endswith('/examiner')
    assert c.get('/examiner').status_code == 200 and c.get('/admin').status_code == 403

def test_pending_examiner_blocked_with_message(app):
    c = app.test_client(); register(c, 'Ex', 'p@x.com', 'examiner')
    r = post_login(c, 'p@x.com', 'password1')
    assert r.status_code == 200 and 'awaiting admin approval' in r.get_data(as_text=True)
    assert 'lp-alert--err' in r.get_data(as_text=True)
    assert c.get('/examiner').status_code == 302       # still anonymous: bounced to /login

@pytest.mark.parametrize('status', ['inactive', 'rejected'])
def test_inactive_or_rejected_account_blocked(app, status):
    c = app.test_client(); register(c, 'Ex', 'x@x.com', 'examiner'); set_status(app, 'x@x.com', status)
    r = post_login(c, 'x@x.com', 'password1')
    assert 'not active' in r.get_data(as_text=True) and c.get('/examiner').status_code == 302

# ---- invalid credentials ----
def test_wrong_password_and_unknown_email_share_one_message(app):
    c = app.test_client()
    a = post_login(c, ADMIN[0], 'wrong').get_data(as_text=True)
    b = post_login(c, 'nobody@x.com', 'whatever').get_data(as_text=True)
    assert 'Incorrect email or password.' in a and 'Incorrect email or password.' in b   # no account enumeration
    assert c.get('/admin').status_code == 302

def test_email_is_kept_but_password_never_echoed(app):
    h = post_login(app.test_client(), ADMIN[0], 'SuperSecret!1').get_data(as_text=True)
    assert 'value="admin@epm.local"' in h and 'SuperSecret!1' not in h
    assert re.search(r'name="password"[^>]*\sautofocus', h)   # focus moves to password after a failed attempt

def test_email_is_escaped(app):
    h = post_login(app.test_client(), '"><script>alert(1)</script>', 'x').get_data(as_text=True)
    assert '<script>alert(1)</script>' not in h

def test_email_case_and_whitespace_normalised(app):
    assert post_login(app.test_client(), '  ADMIN@EPM.LOCAL ', ADMIN[1]).status_code == 302

# ---- server-side enforcement; tampering with the form changes nothing ----
def test_extra_role_field_is_ignored(app):
    c = app.test_client(); register(c, 'Stu', 's@x.com', 'student')
    post_login(c, 's@x.com', 'password1', role='admin', status='active', is_admin='1')
    assert c.get('/admin').status_code == 403 and c.get('/student').status_code == 200

def test_passwords_are_hashed_in_db(app):
    with app.app_context():
        pw = User.query.filter_by(role='admin').first().pw
        assert pw != ADMIN[1] and pw.startswith(('scrypt:', 'pbkdf2:'))

def test_csrf_enforced_and_login_works_with_token(csrf_app):
    c = csrf_app.test_client()
    assert post_login(c, *ADMIN).status_code == 400            # forged/missing token rejected
    tok = re.search(r'name="csrf_token" value="([^"]+)"', c.get('/login').get_data(as_text=True)).group(1)
    r = c.post('/login', data={'email': ADMIN[0], 'password': ADMIN[1], 'csrf_token': tok})
    assert r.status_code == 302 and c.get('/admin').status_code == 200

# ---- messages, logout, session handling ----
def test_registration_success_message_shown_on_login(app):
    c = app.test_client()
    h = c.post('/register', data={'name': 'Ex', 'email': 'n@x.com', 'password': 'password1', 'role': 'examiner'}, follow_redirects=True).get_data(as_text=True)
    assert 'lp-alert--ok' in h and 'An admin must approve your account' in h

def test_login_required_notice_is_styled(app):
    h = app.test_client().get('/admin', follow_redirects=True).get_data(as_text=True)
    assert 'Please log in to access this page.' in h and 'lp-alert--info' in h

def test_logout_ends_session(app):
    c = app.test_client(); post_login(c, *ADMIN); assert c.get('/admin').status_code == 200
    r = c.post('/logout'); assert r.status_code == 302 and r.headers['Location'].endswith('/login')
    assert c.get('/admin').status_code == 302 and c.get('/login').status_code == 200
