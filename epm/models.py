from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    pw = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # admin/examiner/student
    status = db.Column(db.String(10), default='active')  # active/pending/inactive/rejected
    phone = db.Column(db.String(30), default='')
    department = db.Column(db.String(120), default='')
    created = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    active = db.Column(db.Boolean, default=True)
    exams = db.relationship('Exam', backref='course')

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Draft')
    slot_start = db.Column(db.Date); slot_end = db.Column(db.Date)
    book_start = db.Column(db.Date); book_end = db.Column(db.Date)
    cancel_days = db.Column(db.Integer, default=1)  # cancel allowed until N days before slot
    published = db.Column(db.Boolean, default=False)
    rubrics = db.relationship('Rubric', backref='exam', cascade='all,delete-orphan')
    slots = db.relationship('Slot', backref='exam')

class Rubric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.ForeignKey('exam.id'), nullable=False)
    criterion = db.Column(db.String(100), nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, default=1)
    description = db.Column(db.Text, default='')

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.ForeignKey('exam.id'), nullable=False)
    examiner_id = db.Column(db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start = db.Column(db.Time, nullable=False); end = db.Column(db.Time, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    examiner = db.relationship('User')
    bookings = db.relationship('Booking', backref='slot')
    def taken(self): return sum(1 for b in self.bookings if b.status == 'Booked')
    def seats(self): return self.capacity - self.taken()

class Booking(db.Model):
    __table_args__ = (db.UniqueConstraint('slot_id', 'student_id'),)
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.ForeignKey('slot.id'), nullable=False)
    student_id = db.Column(db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(12), default='Booked')  # Booked/Cancelled
    created = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('User')
    evaluation = db.relationship('Evaluation', backref='booking', uselist=False)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.ForeignKey('booking.id'), unique=True, nullable=False)
    status = db.Column(db.String(10), default='Draft')  # Draft/Submitted
    remarks = db.Column(db.Text, default='')
    total = db.Column(db.Float, default=0)
    scores = db.relationship('Score', backref='evaluation', cascade='all,delete-orphan')

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluation_id = db.Column(db.ForeignKey('evaluation.id'), nullable=False)
    rubric_id = db.Column(db.ForeignKey('rubric.id'), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    rubric = db.relationship('Rubric')

class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    at = db.Column(db.DateTime, default=datetime.utcnow)
    who = db.Column(db.String(80)); what = db.Column(db.String(255))
