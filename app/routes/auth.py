from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.i18n import set_locale, translate as _

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/set-language/<lang>')
def change_language(lang):
    if lang in ('en', 'fr'):
        set_locale(lang)
    next_url = request.args.get('next') or request.referrer or url_for('auth.login')
    return redirect(next_url)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_professor:
            return redirect(url_for('professor.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')

        if not username or not email or not password:
            flash(_('invalid_credentials'), 'danger')
            return render_template('auth/register.html')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'warning')
            return render_template('auth/register.html')

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(_('register_success'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_professor:
            return redirect(url_for('professor.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            if user.is_professor:
                return redirect(url_for('professor.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash(_('invalid_credentials'), 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
