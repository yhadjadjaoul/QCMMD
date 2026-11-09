import pytest
from app import create_app, db
from app.models import User

@pytest.fixture
def client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    with app.test_client() as client:
        yield client

def test_user_registration_and_login(client):
    # Test Registration
    res = client.post('/auth/register', data={
        'username': 'prof_jane',
        'email': 'jane@example.com',
        'password': 'securepassword',
        'role': 'professor'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Account created successfully" in res.data or b"Compte" in res.data

    # Test Login
    res_login = client.post('/auth/login', data={
        'email': 'jane@example.com',
        'password': 'securepassword'
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"prof_jane" in res_login.data
    assert b"My QCMs" in res_login.data

def test_language_switch(client):
    # Switch to French
    res = client.get('/auth/set-language/fr', follow_redirects=True)
    assert res.status_code == 200
    assert b"Connexion" in res.data or b"Mes QCMs" in res.data

    # Switch back to English
    res_en = client.get('/auth/set-language/en', follow_redirects=True)
    assert res_en.status_code == 200
    assert b"Log In" in res_en.data or b"My QCMs" in res_en.data
