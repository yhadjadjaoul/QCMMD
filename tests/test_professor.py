import pytest
import io
from app import create_app, db
from app.models import User, Quiz

@pytest.fixture
def app_and_client():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False
    })
    with app.app_context():
        # Create Professor
        prof = User(username='prof1', email='prof1@test.com', role='professor')
        prof.set_password('pass123')
        # Create Student
        student = User(username='stud1', email='stud1@test.com', role='student')
        student.set_password('pass123')
        db.session.add_all([prof, student])
        db.session.commit()

    with app.test_client() as client:
        yield app, client

def test_professor_import_markdown(app_and_client):
    app, client = app_and_client

    # Log in as professor
    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123'}, follow_redirects=True)

    md_content = """# Biology Quiz
## Cellular Biology
### What is the powerhouse of the cell? [score: 2]
> Hint: It starts with M.
- [x] Mitochondria
- [ ] Ribosome
- [ ] Nucleus
"""
    res = client.post('/professor/import', data={
        'markdown_text': md_content
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Biology Quiz" in res.data

    with app.app_context():
        quiz = Quiz.query.filter_by(title="Biology Quiz").first()
        assert quiz is not None
        assert quiz.code is not None
        assert len(quiz.questions) == 1
        assert quiz.questions[0].max_score == 2.0
        assert quiz.questions[0].hint == "It starts with M."

def test_professor_toggle_and_csv_export(app_and_client):
    app, client = app_and_client

    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123'}, follow_redirects=True)

    # Import
    client.post('/professor/import', data={
        'markdown_text': "# Geo\n## World\n### Capital of France?\n- [x] Paris\n- [ ] Lyon"
    }, follow_redirects=True)

    with app.app_context():
        quiz = Quiz.query.first()
        quiz_id = quiz.id
        assert quiz.is_open is True

    # Toggle
    res_toggle = client.get(f'/professor/quiz/{quiz_id}/toggle', follow_redirects=True)
    assert res_toggle.status_code == 200
    with app.app_context():
        quiz = Quiz.query.get(quiz_id)
        assert quiz.is_open is False

    # Export CSV
    res_csv = client.get(f'/professor/quiz/{quiz_id}/export-csv')
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.content_type
    assert b"Student Username,Student Email,Score,Max Score,Percentage,Submitted At" in res_csv.data
