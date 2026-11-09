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

        # Add a sample Quiz with single choice and multi choice
        md = """# Physics 101
## Mechanics
### What is the SI unit of Force? [score: 2]
> Hint: Named after Sir Isaac.
- [x] Newton
- [ ] Joule
- [ ] Pascal

### Select vector quantities [score: 2]
- [x] Velocity
- [ ] Speed
- [x] Acceleration
"""
        quiz = parse_markdown_to_quiz(md, author_id=prof.id, code='PHYS123')
        db.session.add(quiz)
        db.session.commit()

    with app.test_client() as client:
        yield app, client

def test_student_flow(app_and_client):
    app, client = app_and_client

    # Log in as student
    client.post('/auth/login', data={'email': 'student1@test.com', 'password': 'pass123'}, follow_redirects=True)

    # Access take quiz page
    res_page = client.get('/student/quiz/PHYS123')
    assert res_page.status_code == 200
    html = res_page.data.decode('utf-8')
    assert "Physics 101" in html
    assert "What is the SI unit of Force?" in html
    assert "Single choice" in html
    assert "Multiple choices" in html
    # Verify input types: radio for Q1, checkbox for Q2
    assert 'type="radio"' in html
    assert 'type="checkbox"' in html

    with app.app_context():
        quiz = Quiz.query.filter_by(code='PHYS123').first()
        q1 = quiz.questions[0]
        correct_c1 = [c for c in q1.choices if c.is_correct][0]
        correct_cid1 = correct_c1.id

        q2 = quiz.questions[1]
        correct_cids2 = [str(c.id) for c in q2.choices if c.is_correct]

    # Submit correct answers for both questions
    res_submit = client.post('/student/quiz/PHYS123/submit', data={
        f'q_{q1.id}': [str(correct_cid1)],
        f'q_{q2.id}': correct_cids2
    }, follow_redirects=True)

    assert res_submit.status_code == 200
    assert b"4.0" in res_submit.data  # full score 4.0 awarded
    assert b"Named after Sir Isaac" in res_submit.data  # Hint visible
