import pytest
from app import create_app, db
from app.models import User, StudentAccessCode

@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    with app.test_client() as client:
        yield client

def test_initial_setup_and_login(client):
    # Initial setup: no user exists yet, so register creates the professor/admin account without code
    res = client.post('/auth/register', data={
        'username': 'prof_jane',
        'email': 'jane@example.com',
        'password': 'securepassword',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"configured successfully" in res.data or b"configur" in res.data

    # Test Login with correct credentials & captcha
    res_login = client.post('/auth/login', data={
        'email': 'jane@example.com',
        'password': 'securepassword',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"prof_jane" in res_login.data
    assert b"My QCMs" in res_login.data

def test_captcha_verification(client):
    # Attempt setup with invalid captcha
    res = client.post('/auth/register', data={
        'username': 'prof_bad',
        'email': 'bad@example.com',
        'password': 'securepassword',
        'captcha': 'WRONG_CAPTCHA'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid verification code" in res.data or b"invalide" in res.data

    # Now succeed with valid captcha
    res_ok = client.post('/auth/register', data={
        'username': 'prof_ok',
        'email': 'ok@example.com',
        'password': 'securepassword',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)
    assert res_ok.status_code == 200

    # Attempt login with invalid captcha
    res_fail_login = client.post('/auth/login', data={
        'email': 'ok@example.com',
        'password': 'securepassword',
        'captcha': 'WRONG_CAPTCHA'
    }, follow_redirects=True)
    assert res_fail_login.status_code == 200
    assert b"Invalid verification code" in res_fail_login.data or b"invalide" in res_fail_login.data

def test_student_registration_requires_code(client):
    # Step 1: Initial setup
    client.post('/auth/register', data={
        'username': 'the_prof',
        'email': 'theprof@example.com',
        'password': 'password123',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)

    # Step 2: Attempt student registration without access code
    res_no_code = client.post('/auth/register', data={
        'username': 'student_attacker',
        'email': 'attacker@example.com',
        'password': 'password123',
        'captcha': 'TEST_CAPTCHA',
        'access_code': ''
    }, follow_redirects=True)
    assert res_no_code.status_code == 200
    assert b"required" in res_no_code.data or b"requis" in res_no_code.data

    # Step 3: Attempt student registration with invalid access code
    res_bad_code = client.post('/auth/register', data={
        'username': 'student_attacker',
        'email': 'attacker@example.com',
        'password': 'password123',
        'captcha': 'TEST_CAPTCHA',
        'access_code': 'FAKE-CODE-999'
    }, follow_redirects=True)
    assert res_bad_code.status_code == 200
    assert b"Invalid or already used" in res_bad_code.data or b"invalide ou" in res_bad_code.data

    # Step 4: Login as prof and generate code
    client.post('/auth/login', data={
        'email': 'theprof@example.com',
        'password': 'password123',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)

    res_gen = client.post('/professor/student-codes/generate', data={'count': 1}, follow_redirects=True)
    assert res_gen.status_code == 200
    assert b"STU-" in res_gen.data

    # Get the generated code from database
    prof_user = User.query.filter_by(email='theprof@example.com').first()
    code_obj = StudentAccessCode.query.filter_by(created_by_id=prof_user.id, is_used=False).first()
    assert code_obj is not None
    valid_code = code_obj.code

    # Logout prof
    client.get('/auth/logout', follow_redirects=True)

    # Step 5: Register student with the valid code
    res_student_reg = client.post('/auth/register', data={
        'username': 'valid_student',
        'email': 'student@school.com',
        'password': 'studentpassword',
        'captcha': 'TEST_CAPTCHA',
        'access_code': valid_code
    }, follow_redirects=True)
    assert res_student_reg.status_code == 200
    assert b"Account created successfully" in res_student_reg.data or b"Compte" in res_student_reg.data

    # Verify code is now used
    updated_code_obj = StudentAccessCode.query.filter_by(code=valid_code).first()
    assert updated_code_obj.is_used is True
    assert updated_code_obj.used_by.username == 'valid_student'

    # Step 6: Attempt reusing the same code
    res_reuse = client.post('/auth/register', data={
        'username': 'another_student',
        'email': 'another@school.com',
        'password': 'studentpassword',
        'captcha': 'TEST_CAPTCHA',
        'access_code': valid_code
    }, follow_redirects=True)
    assert res_reuse.status_code == 200
    assert b"Invalid or already used" in res_reuse.data or b"invalide ou" in res_reuse.data

    # Step 7: Student login
    res_stu_login = client.post('/auth/login', data={
        'email': 'student@school.com',
        'password': 'studentpassword',
        'captcha': 'TEST_CAPTCHA'
    }, follow_redirects=True)
    assert res_stu_login.status_code == 200
    assert b"valid_student" in res_stu_login.data
    assert b"Join a QCM" in res_stu_login.data or b"Rejoindre" in res_stu_login.data

def test_language_switch(client):
    # Switch to French
    res = client.get('/auth/set-language/fr', follow_redirects=True)
    assert res.status_code == 200
    assert b"Connexion" in res.data or b"Configuration" in res.data

    # Switch back to English
    res_en = client.get('/auth/set-language/en', follow_redirects=True)
    assert res_en.status_code == 200
    assert b"Log In" in res_en.data or b"Configuration" in res_en.data
