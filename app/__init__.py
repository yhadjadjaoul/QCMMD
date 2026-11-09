import os
from flask import Flask, request, session, redirect, url_for
from flask_login import LoginManager, current_user
from app.models import db, User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_overrides=None):
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-secret-key-12345')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///qcm.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    login_manager.init_app(app)

    # i18n helper context processor
    from app.i18n import get_locale, translate
    @app.context_processor
    def inject_i18n():
        return {
            '_': translate,
            'current_locale': get_locale(),
        }

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.professor import professor_bp
    from app.routes.student import student_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(professor_bp, url_prefix='/professor')
    app.register_blueprint(student_bp, url_prefix='/student')

    # Register index route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.is_professor:
                return redirect(url_for('professor.dashboard'))
            return redirect(url_for('student.dashboard'))
        return redirect(url_for('auth.login'))

    with app.app_context():
        db.create_all()

    return app
