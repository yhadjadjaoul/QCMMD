from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'professor' or 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    quizzes = db.relationship('Quiz', backref='author', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='student', lazy=True, cascade='all, delete-orphan')
    created_access_codes = db.relationship('StudentAccessCode', backref='creator', foreign_keys='StudentAccessCode.created_by_id', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_professor(self):
        return self.role == 'professor'


class StudentAccessCode(db.Model):
    __tablename__ = 'student_access_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    used_by = db.relationship('User', foreign_keys=[used_by_id], backref='used_access_code')


class Quiz(db.Model):
    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default='')
    raw_markdown = db.Column(db.Text, default='')
    is_open = db.Column(db.Boolean, default=True)
    shuffle_questions = db.Column(db.Boolean, default=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship('Section', backref='quiz', lazy=True, cascade='all, delete-orphan', order_by='Section.order_index')
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan', order_by='Question.order_index')
    submissions = db.relationship('Submission', backref='quiz', lazy=True, cascade='all, delete-orphan')

    @property
    def total_max_score(self):
        return sum(q.max_score for q in self.questions)


class Section(db.Model):
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    subtext = db.Column(db.Text, default='')
    order_index = db.Column(db.Integer, default=0)

    questions = db.relationship('Question', backref='section', lazy=True, cascade='all, delete-orphan', order_by='Question.order_index')


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    subtext = db.Column(db.Text, default='')
    question_type = db.Column(db.String(20), default='choice')  # 'choice' or 'text'
    choice_type = db.Column(db.String(20), default='auto')  # 'single' (case 1), 'multiple' (case 2), or 'auto'
    max_score = db.Column(db.Float, default=1.0)
    hint = db.Column(db.Text, default='')
    answer_key = db.Column(db.Text, default='')  # Reference/sample answer for text questions
    order_index = db.Column(db.Integer, default=0)

    choices = db.relationship('Choice', backref='question', lazy=True, cascade='all, delete-orphan', order_by='Choice.order_index')
    answer_submissions = db.relationship('AnswerSubmission', backref='question', lazy=True, cascade='all, delete-orphan')

    @property
    def is_multiple_choice(self):
        """
        Returns True if question needs multiple answers (case 2 -> checkboxes),
        False if question needs one answer (case 1 -> radio buttons).
        """
        if self.choice_type in ('multiple', 'checkbox', 'case2', 'case_2', 'case 2'):
            return True
        if self.choice_type in ('single', 'radio', 'case1', 'case_1', 'case 1'):
            return False
        # If auto, determine from number of correct choices
        correct_count = sum(1 for c in self.choices if c.is_correct)
        return correct_count > 1


class Choice(db.Model):
    __tablename__ = 'choices'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    order_index = db.Column(db.Integer, default=0)


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_score = db.Column(db.Float, default=0.0)
    max_score = db.Column(db.Float, default=0.0)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    answers = db.relationship('AnswerSubmission', backref='submission', lazy=True, cascade='all, delete-orphan')


class AnswerSubmission(db.Model):
    __tablename__ = 'answer_submissions'

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_choice_ids = db.Column(db.String(255), default='')  # comma-separated IDs of selected choices
    text_response = db.Column(db.Text, default='')
    score_awarded = db.Column(db.Float, default=0.0)
    is_graded = db.Column(db.Boolean, default=False)  # True once graded (automatic for choice, manual for text)
