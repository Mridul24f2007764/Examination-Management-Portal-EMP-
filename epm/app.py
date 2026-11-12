import os
from datetime import date, datetime, time
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
from models import *

TYPES = ['Viva', 'Practical', 'Project Demo', 'Assessment']
STATUSES = ['Draft', 'Slot Creation Open', 'Booking Open', 'Booking Closed', 'In Progress', 'Evaluation Pending', 'Completed']

def create_app(cfg=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-only-change-me'),
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'examination_portal.db'))
    app.config.update(cfg or {})
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app); CSRFProtect(app)
    lm = LoginManager(app); lm.login_view = 'login'
    lm.user_loader(lambda i: db.session.get(User, int(i)))
    app.jinja_env.globals['csrf'] = lambda: Markup(f'<input type="hidden" name="csrf_token" value="{generate_csrf()}">')
    with app.app_context():
        db.create_all()
        # Lightweight, backward-compatible schema upgrade for existing SQLite databases.
        with db.engine.begin() as conn:
            cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(user)").fetchall()}
            if 'phone' not in cols:
                conn.exec_driver_sql("ALTER TABLE user ADD COLUMN phone VARCHAR(30) DEFAULT ''")
            if 'department' not in cols:
                conn.exec_driver_sql("ALTER TABLE user ADD COLUMN department VARCHAR(120) DEFAULT ''")
        if not User.query.filter_by(role='admin').first():
            db.session.add(User(name='Administrator', email=os.environ.get('ADMIN_EMAIL', 'admin@epm.local'), role='admin',
                pw=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Admin@123'))))
            db.session.commit()

    def role(r):
        def deco(f):
            @wraps(f)
            @login_required
            def w(*a, **k):
                if current_user.role != r or current_user.status != 'active': abort(403)
                return f(*a, **k)
            return w
        return deco
    def log(msg): db.session.add(Audit(who=current_user.email, what=msg))
    def pd(s): return datetime.strptime(s, '%Y-%m-%d').date() if s else None
    def pt(s): return datetime.strptime(s, '%H:%M').time()
    def ok(msg): flash(msg, 'ok')
    def err(msg): flash(msg, 'err')

    @app.errorhandler(403)
    def e403(e): return render_template('error.html', msg='You do not have access to this page.'), 403
    @app.errorhandler(404)
    def e404(e): return render_template('error.html', msg='Page not found.'), 404

    # ---------- auth ----------
    @app.route('/')
    def index(): return redirect(url_for('home') if current_user.is_authenticated else url_for('login'))

    @app.route('/home')
    @login_required
    def home(): return redirect(url_for({'admin': 'admin_dash', 'examiner': 'ex_dash', 'student': 'st_dash'}[current_user.role]))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            u = User.query.filter_by(email=request.form['email'].strip().lower()).first()
            if not u or not check_password_hash(u.pw, request.form['password']): err('Incorrect email or password.')
            elif u.status == 'pending': err('Your examiner account is awaiting admin approval.')
            elif u.status != 'active': err('This account is not active. Contact the administrator.')
            else:
                login_user(u); db.session.add(Audit(who=u.email, what='Logged in')); db.session.commit(); return redirect(url_for('home'))
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            f = request.form; email = f['email'].strip().lower()
            if f['role'] not in ('student', 'examiner'): abort(400)
            if len(f['password']) < 8: err('Password must be at least 8 characters.')
            elif '@' not in email or not f['name'].strip(): err('Enter a valid name and email.')
            elif User.query.filter_by(email=email).first(): err('That email is already registered.')
            else:
                db.session.add(User(name=f['name'].strip(), email=email, role=f['role'], pw=generate_password_hash(f['password']),
                    status='pending' if f['role'] == 'examiner' else 'active', phone=f.get('phone','').strip(), department=f.get('department','').strip()))
                db.session.add(Audit(who=email, what='Registered as ' + f['role']))
                db.session.commit()
                ok('Registered. ' + ('An admin must approve your account before you can log in.' if f['role'] == 'examiner' else 'You can log in now.'))
                return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        db.session.add(Audit(who=current_user.email, what='Logged out')); db.session.commit()
        logout_user(); return redirect(url_for('login'))

    # ---------- admin ----------
    @app.route('/admin')
    @role('admin')
    def admin_dash():
        s = dict(Courses=Course.query.count(), Examinations=Exam.query.count(),
            Examiners=User.query.filter_by(role='examiner', status='active').count(),
            Students=User.query.filter_by(role='student').count(), Slots=Slot.query.count(),
            Bookings=Booking.query.filter_by(status='Booked').count(),
            **{'Pending approvals': User.query.filter_by(role='examiner', status='pending').count(),
               'Pending evaluations': Booking.query.filter_by(status='Booked').count() - Evaluation.query.join(Booking).filter(Evaluation.status == 'Submitted', Booking.status == 'Booked').count()})
        return render_template('admin_dash.html', s=s, audit=Audit.query.order_by(Audit.id.desc()).limit(8).all())

    @app.route('/admin/courses', methods=['GET', 'POST'])
    @role('admin')
    def admin_courses():
        if request.method == 'POST':
            f = request.form; code = f['code'].strip().upper()
            if not code or not f['name'].strip(): err('Code and name are required.')
            elif Course.query.filter_by(code=code).first(): err('Course code already exists.')
            else:
                db.session.add(Course(code=code, name=f['name'].strip(), description=f['description'])); log('Created course ' + code); db.session.commit(); ok('Course created.')
        q = request.args.get('q', '')
        cs = Course.query.filter((Course.name.contains(q)) | (Course.code.contains(q))).all()
        return render_template('admin_courses.html', cs=cs, q=q)

    @app.route('/admin/courses/<int:i>/<act>', methods=['POST'])
    @role('admin')
    def course_act(i, act):
        c = db.get_or_404(Course, i)
        if act == 'toggle': c.active = not c.active; ok('Course status updated.')
        elif act == 'delete':
            if c.exams: err('Cannot delete: examinations depend on this course. Deactivate it instead.')
            else: db.session.delete(c); ok('Course deleted.')
        else: abort(404)
        log(f'{act} course {c.code}'); db.session.commit(); return redirect(url_for('admin_courses'))

    @app.route('/admin/exams', methods=['GET', 'POST'])
    @role('admin')
    def admin_exams():
        if request.method == 'POST':
            f = request.form
            try:
                ss, se, bs, be = pd(f['slot_start']), pd(f['slot_end']), pd(f['book_start']), pd(f['book_end'])
                if not (ss and se and bs and be) or ss > se or bs > be: raise ValueError
                if f['type'] not in TYPES or not f['name'].strip(): raise ValueError
                db.session.add(Exam(course_id=int(f['course_id']), name=f['name'].strip(), type=f['type'], slot_start=ss, slot_end=se,
                    book_start=bs, book_end=be, cancel_days=max(0, int(f.get('cancel_days') or 1))))
                log('Created exam ' + f['name']); db.session.commit(); ok('Examination created.')
            except (ValueError, KeyError): err('Check the form: all dates are required and each end date must not precede its start date.')
        q = request.args.get('q', '')
        ex = Exam.query.join(Course).filter((Exam.name.contains(q)) | (Course.name.contains(q)) | (Exam.id == (int(q) if q.isdigit() else -1))).all()
        return render_template('admin_exams.html', ex=ex, q=q, courses=Course.query.filter_by(active=True).all(), types=TYPES)

    @app.route('/admin/exams/<int:i>', methods=['GET', 'POST'])
    @role('admin')
    def admin_exam(i):
        e = db.get_or_404(Exam, i)
        if request.method == 'POST':
            f = request.form; a = f['action']
            if a == 'status' and f['status'] in STATUSES: e.status = f['status']; ok('Status changed.')
            elif a == 'publish':
                pending = [b for s in e.slots for b in s.bookings if b.status == 'Booked' and not (b.evaluation and b.evaluation.status == 'Submitted')]
                if pending and not e.published: err(f'{len(pending)} booking(s) still lack a submitted evaluation.')
                else: e.published = not e.published; e.status = 'Completed' if e.published else e.status; ok('Results ' + ('published.' if e.published else 'hidden.'))
            elif a == 'rubric':
                try:
                    m = float(f['max_marks']); w = float(f['weight'] or 1)
                    if m <= 0 or w <= 0 or not f['criterion'].strip(): raise ValueError
                    if any(s.bookings and any(b.evaluation for b in s.bookings) for s in e.slots): err('Rubric is locked: evaluations already exist.'); return redirect(request.url)
                    db.session.add(Rubric(exam_id=e.id, criterion=f['criterion'].strip(), max_marks=m, weight=w, description=f['description'])); ok('Criterion added.')
                except ValueError: err('Criterion name, positive max marks and weightage are required.')
            elif a == 'del_rubric':
                r = db.session.get(Rubric, int(f['rid']))
                if r and r.exam_id == e.id and not Score.query.filter_by(rubric_id=r.id).first(): db.session.delete(r); ok('Criterion removed.')
                else: err('Cannot remove a criterion that has scores.')
            log(f'{a} on exam {e.id}'); db.session.commit(); return redirect(request.url)
        return render_template('admin_exam.html', e=e, statuses=STATUSES)

    @app.route('/admin/examiners', methods=['GET', 'POST'])
    @role('admin')
    def admin_examiners():
        if request.method == 'POST':
            u = db.get_or_404(User, int(request.form['uid']))
            if u.role != 'examiner': abort(400)
            action = request.form['action']
            if action not in ('approve', 'reject', 'deactivate', 'activate'): abort(400)
            u.status = {'approve': 'active', 'reject': 'rejected', 'deactivate': 'inactive', 'activate': 'active'}[action]
            log(f"{request.form['action']} examiner {u.email}"); db.session.commit(); ok('Examiner updated.')
        q = request.args.get('q', '')
        us = User.query.filter_by(role='examiner').filter((User.name.contains(q)) | (User.id == (int(q) if q.isdigit() else -1))).all()
        return render_template('admin_examiners.html', us=us, q=q)

    @app.route('/admin/students')
    @role('admin')
    def admin_students():
        q = request.args.get('q', '').strip()
        qs = User.query.filter_by(role='student')
        if q:
            qs = qs.filter((User.name.contains(q)) | (User.email.contains(q)) | (User.id == (int(q) if q.isdigit() else -1)))
        students = qs.order_by(User.name).all()
        counts = {u.id: Booking.query.filter_by(student_id=u.id).count() for u in students}
        return render_template('admin_students.html', students=students, q=q, u_bookings=counts)

    @app.route('/examiner/profile', methods=['GET', 'POST'])
    @role('examiner')
    def examiner_profile():
        if request.method == 'POST':
            phone = request.form.get('phone', '').strip()
            department = request.form.get('department', '').strip()
            if len(phone) > 30 or len(department) > 120:
                err('Please check the profile field lengths.')
            else:
                current_user.phone = phone
                current_user.department = department
                log('Updated examiner profile')
                db.session.commit()
                ok('Profile updated.')
            return redirect(url_for('examiner_profile'))
        return render_template('examiner_profile.html')

    @app.route('/admin/bookings', methods=['GET', 'POST'])
    @role('admin')
    def admin_bookings():
        if request.method == 'POST':
            f = request.form; a = f['action']
            if a == 'reassign':
                s = db.get_or_404(Slot, int(f['slot_id'])); u = db.get_or_404(User, int(f['examiner_id']))
                if u.role != 'examiner' or u.status != 'active': err('Choose an active examiner.')
                elif conflict(u.id, s.date, s.start, s.end, s.id): err('That examiner has a conflicting slot.')
                else: s.examiner_id = u.id; log(f'Reassigned slot {s.id} to {u.email}'); db.session.commit(); ok('Examiner reassigned.')
            elif a == 'reschedule':
                b = db.get_or_404(Booking, int(f['booking_id'])); s = db.get_or_404(Slot, int(f['slot_id']))
                msg = check_book(b.student, s, ignore=b.id, admin=True)
                if b.status != 'Booked': err('Only active bookings can be rescheduled.')
                elif b.evaluation: err('Cannot reschedule an evaluated booking.')
                elif msg: err(msg)
                else: b.slot_id = s.id; log(f'Rescheduled booking {b.id} to slot {s.id}'); db.session.commit(); ok('Booking rescheduled.')
        q = request.args.get('q', '')
        bs = Booking.query.join(User, Booking.student_id == User.id).filter(User.name.contains(q)).order_by(Booking.id.desc()).all()
        return render_template('admin_bookings.html', bs=bs, q=q, slots=Slot.query.all(), examiners=User.query.filter_by(role='examiner', status='active').all())

    # ---------- shared rules ----------
    def conflict(eid, d, st, en, ignore=None):
        return any(s.id != ignore and s.examiner_id == eid and s.date == d and s.start < en and st < s.end for s in Slot.query.filter_by(examiner_id=eid, date=d))

    def check_book(stu, s, ignore=None, admin=False):
        e = s.exam; today = date.today()
        if not admin and not (e.book_start <= today <= e.book_end): return 'Booking is not open for this examination.'
        if e.status not in ('Booking Open',) and not admin: return 'Booking is closed for this examination.'
        if s.date < today: return 'This slot is in the past.'
        if s.date < e.slot_start or s.date > e.slot_end: return 'This slot is outside the examination slot date range.'
        if s.date < e.book_start or s.date > e.book_end: return 'This slot is outside the examination booking date range.'
        for b in Booking.query.filter_by(student_id=stu.id, status='Booked'):
            if b.id == ignore: continue
            if b.slot_id == s.id: return 'You already have a booking in this slot.'
            o = b.slot
            if o.date == s.date and o.start < s.end and s.start < o.end: return 'This overlaps another booking.'
        if s.seats() <= 0: return 'This slot is full.'
        return None

    # ---------- examiner ----------
    @app.route('/examiner')
    @role('examiner')
    def ex_dash():
        sl = Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date).all()
        bk = [b for s in sl for b in s.bookings if b.status == 'Booked']
        done = sum(1 for b in bk if b.evaluation and b.evaluation.status == 'Submitted')
        return render_template('ex_dash.html', sl=sl, booked=len(bk), seats=sum(s.seats() for s in sl), done=done, pending=len(bk) - done)

    @app.route('/examiner/slots', methods=['GET', 'POST'])
    @role('examiner')
    def ex_slots():
        today = date.today()
        if request.method == 'POST':
            f = request.form; a = f.get('action', 'create')
            if a == 'create':
                e = db.session.get(Exam, int(f['exam_id']))
                try:
                    d, st, en, cap = pd(f['date']), pt(f['start']), pt(f['end']), int(f['capacity'])
                    if not e: raise ValueError('Select an examination.')
                    if not (e.slot_start <= today <= e.slot_end) or e.status != 'Slot Creation Open': raise ValueError('Slot creation is not open for this examination.')
                    if en <= st: raise ValueError('End time must be after start time.')
                    if cap < 1: raise ValueError('Capacity must be positive.')
                    if d < today: raise ValueError('Date cannot be in the past.')
                    if d < e.slot_start or d > e.slot_end: raise ValueError('Slot date must be within the examination slot creation date range.')
                    if d < e.book_start or d > e.book_end: raise ValueError('Slot date must fall within the examination booking date range.')
                    if conflict(current_user.id, d, st, en): raise ValueError('This overlaps another of your slots.')
                    db.session.add(Slot(exam_id=e.id, examiner_id=current_user.id, date=d, start=st, end=en, capacity=cap)); db.session.commit(); ok('Slot created.')
                except (ValueError, TypeError, KeyError) as x: err(str(x) if str(x) and 'invalid literal' not in str(x) and 'does not match' not in str(x) else 'Fill in every field with valid values.')
            elif a == 'delete':
                s = db.get_or_404(Slot, int(f['slot_id']))
                if s.examiner_id != current_user.id: abort(403)
                if any(b.status == 'Booked' for b in s.bookings): err('Cannot remove a slot that has bookings.')
                elif today >= s.exam.book_start: err('Slots can only be removed before booking starts.')
                else:
                    for b in s.bookings: db.session.delete(b)
                    db.session.delete(s); db.session.commit(); ok('Slot removed.')
        exams = Exam.query.filter(Exam.status == 'Slot Creation Open', Exam.slot_start <= today, Exam.slot_end >= today).all()
        return render_template('ex_slots.html', exams=exams, sl=Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date).all())

    def own_booking(bid):
        b = db.get_or_404(Booking, bid)
        if b.slot.examiner_id != current_user.id or b.status != 'Booked': abort(403)
        return b

    @app.route('/examiner/evaluate')
    @role('examiner')
    def ex_eval():
        sl = Slot.query.filter_by(examiner_id=current_user.id).order_by(Slot.date).all()
        return render_template('ex_eval.html', sl=sl)

    @app.route('/examiner/evaluate/<int:bid>', methods=['GET', 'POST'])
    @role('examiner')
    def ex_eval_one(bid):
        b = own_booking(bid); e = b.slot.exam; ev = b.evaluation
        locked = ev is not None and ev.status == 'Submitted'
        if request.method == 'POST':
            if locked: err('This evaluation is submitted and locked. Ask an admin for a correction.'); return redirect(request.url)
            if not e.rubrics: err('No rubric defined for this examination.'); return redirect(request.url)
            try:
                vals = {}
                for r in e.rubrics:
                    v = float(request.form[f'r{r.id}'])
                    if v < 0 or v > r.max_marks: raise ValueError(f'"{r.criterion}" must be between 0 and {r.max_marks:g}.')
                    vals[r.id] = v
            except (ValueError, KeyError) as x: err(str(x) if 'must be' in str(x) else 'Enter a number for every criterion.'); return redirect(request.url)
            ev = ev or Evaluation(booking_id=b.id); db.session.add(ev); db.session.flush()
            Score.query.filter_by(evaluation_id=ev.id).delete()
            for rid, v in vals.items(): db.session.add(Score(evaluation_id=ev.id, rubric_id=rid, marks=v))
            ev.remarks = request.form.get('remarks', '')
            total_weight = sum(r.weight for r in e.rubrics)
            if total_weight <= 0: err('Rubric weightage must be positive.'); return redirect(request.url)
            # Weighted percentage score on a 100-point scale.
            ev.total = sum((vals[r.id] / r.max_marks) * r.weight for r in e.rubrics) / total_weight * 100
            ev.status = 'Submitted' if request.form['action'] == 'submit' else 'Draft'
            db.session.commit(); ok('Evaluation submitted.' if ev.status == 'Submitted' else 'Draft saved.')
            return redirect(url_for('ex_eval'))
        sc = {s.rubric_id: s.marks for s in ev.scores} if ev else {}
        return render_template('ex_eval_one.html', b=b, e=e, ev=ev, sc=sc, locked=locked)

    # ---------- student ----------
    @app.route('/student')
    @role('student')
    def st_dash():
        bs = Booking.query.filter_by(student_id=current_user.id).order_by(Booking.id.desc()).all()
        return render_template('st_dash.html', bs=bs, today=date.today())

    @app.route('/student/exams')
    @role('student')
    def st_exams():
        q, t = request.args.get('q', ''), request.args.get('type', '')
        qs = Exam.query.join(Course).filter(Exam.status != 'Draft', ((Exam.name.contains(q)) | (Course.name.contains(q))))
        if t: qs = qs.filter(Exam.type == t)
        return render_template('st_exams.html', ex=qs.all(), q=q, t=t, types=TYPES, today=date.today())

    @app.route('/student/book/<int:sid>', methods=['POST'])
    @role('student')
    def st_book(sid):
        s = db.get_or_404(Slot, sid); msg = check_book(current_user, s)
        if msg: err(msg)
        else:
            old = Booking.query.filter_by(slot_id=sid, student_id=current_user.id, status='Cancelled').first()
            if old: old.status = 'Booked'
            else: db.session.add(Booking(slot_id=sid, student_id=current_user.id))
            try: db.session.commit(); ok(f'Booked: {s.exam.name} on {s.date} at {s.start:%H:%M}.')
            except Exception: db.session.rollback(); err('Could not complete the booking. Please retry.')
        return redirect(url_for('st_exams'))

    @app.route('/student/cancel/<int:bid>', methods=['POST'])
    @role('student')
    def st_cancel(bid):
        b = db.get_or_404(Booking, bid)
        if b.student_id != current_user.id: abort(403)
        if b.status != 'Booked': err('Booking already cancelled.')
        elif (b.slot.date - date.today()).days < b.slot.exam.cancel_days: err('The cancellation deadline has passed.')
        elif b.evaluation: err('This booking has been evaluated.')
        else: b.status = 'Cancelled'; db.session.commit(); ok('Booking cancelled. The seat is available again.')
        return redirect(url_for('st_dash'))

    @app.route('/student/results')
    @role('student')
    def st_results():
        rs = [b for b in Booking.query.filter_by(student_id=current_user.id, status='Booked') if b.slot.exam.published and b.evaluation and b.evaluation.status == 'Submitted']
        return render_template('st_results.html', rs=rs)

    return app

if __name__ == '__main__':
    create_app().run(debug=True)
