from flask import Blueprint, render_template, redirect, url_for, request, flash, session, Response
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User
from app.i18n import set_locale, translate as _
from app.services.captcha import generate_captcha_image, verify_captcha

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/captcha')
def get_captcha():
    image_data = generate_captcha_image()
    return Response(image_data.getvalue(), mimetype='image/png')

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

    from app.models import StudentAccessCode
    # Check if this is the initial setup: no users exist yet
    user_count = User.query.count()
    is_initial_setup = (user_count == 0)

    if request.method == 'POST':
        captcha_input = request.form.get('captcha', '').strip()
        if not verify_captcha(captcha_input):
            flash(_('invalid_captcha'), 'danger')
            return render_template('auth/register.html', is_initial_setup=is_initial_setup)

        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash(_('invalid_credentials'), 'danger')
            return render_template('auth/register.html', is_initial_setup=is_initial_setup)

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash(_('user_already_exists'), 'warning')
            return render_template('auth/register.html', is_initial_setup=is_initial_setup)

        access_code_obj = None
        if is_initial_setup:
            role = 'professor'
        else:
            # Regular registration requires a valid student access code
            student_code = request.form.get('access_code', '').strip().upper()
            if not student_code:
                flash(_('student_code_required'), 'danger')
                return render_template('auth/register.html', is_initial_setup=is_initial_setup)

            access_code_obj = StudentAccessCode.query.filter_by(code=student_code, is_used=False).first()
            if not access_code_obj:
                flash(_('invalid_student_code'), 'danger')
                return render_template('auth/register.html', is_initial_setup=is_initial_setup)

            role = 'student'

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if access_code_obj:
            access_code_obj.is_used = True
            access_code_obj.used_by_id = user.id

        db.session.commit()

        flash(_('setup_success') if is_initial_setup else _('register_success'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', is_initial_setup=is_initial_setup)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_professor:
            return redirect(url_for('professor.dashboard'))
        return redirect(url_for('student.dashboard'))

    # If no users exist, redirect to registration/setup
    if User.query.count() == 0:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        captcha_input = request.form.get('captcha', '').strip()
        if not verify_captcha(captcha_input):
            flash(_('invalid_captcha'), 'danger')
            return render_template('auth/login.html')

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
