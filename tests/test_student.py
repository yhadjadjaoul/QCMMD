import pytest
from app import create_app, db
from app.models import User, Quiz
from app.services.parser import parse_markdown_to_quiz

@pytest.fixture
def app_and_client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    with app.app_context():
        prof = User(username='prof1', email='prof1@test.com', role='professor')
        prof.set_password('pass123')
        student = User(username='student1', email='student1@test.com', role='student')
        student.set_password('pass123')
        db.session.add_all([prof, student])
        db.session.commit()

        # Add a sample Quiz
        md = """# Physics 101
## Mechanics
### What is the SI unit of Force? [score: 2]
> Hint: Named after Sir Isaac.
- [x] Newton
- [ ] Joule
- [ ] Pascal
"""
        quiz = parse_markdown_to_quiz(md, author_id=prof.id, code='PHYS123')
        db.session.add(quiz)
        db.session.commit()

    with app.test_client() as client:
        yield app, client

def test_student_flow(app_and_client):
    app, client = app_and_client

    # Log in as student
    client.post('/auth/login', data={'email': 'student1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)

    # Access take quiz page
    res_page = client.get('/student/quiz/PHYS123')
    assert res_page.status_code == 200
    assert b"Physics 101" in res_page.data
    assert b"What is the SI unit of Force?" in res_page.data

    with app.app_context():
        quiz = Quiz.query.filter_by(code='PHYS123').first()
        q = quiz.questions[0]
        correct_c = [c for c in q.choices if c.is_correct][0]
        correct_cid = correct_c.id

    # Submit correct answer
    res_submit = client.post('/student/quiz/PHYS123/submit', data={
        f'q_{q.id}': [str(correct_cid)]
    }, follow_redirects=True)

    assert res_submit.status_code == 200
    assert b"2.0" in res_submit.data  # full score 2.0 awarded
    assert b"Named after Sir Isaac" in res_submit.data  # Hint visible
