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
    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)

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

    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)

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

def test_professor_grade_text_question(app_and_client):
    app, client = app_and_client

    # 1. Log in as professor and create quiz with text question
    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)
    res_import = client.post('/professor/import', data={
        'markdown_text': "# Essay Quiz\n## General\n### Explain recursion [score: 5]\n- [t] A function that calls itself."
    }, follow_redirects=True)
    assert res_import.status_code == 200

    with app.app_context():
        quiz = Quiz.query.filter_by(title="Essay Quiz").first()
        quiz_id = quiz.id
        quiz_code = quiz.code
        q = quiz.questions[0]
        assert q.answer_key == "A function that calls itself."

    # 2. Log in as student and submit answer
    client.post('/auth/login', data={'email': 'stud1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)
    res_sub = client.post(f'/student/quiz/{quiz_code}/submit', data={
        f'q_{q.id}': "Recursion is when a function calls itself repeatedly until a base condition."
    }, follow_redirects=True)
    assert res_sub.status_code == 200
    assert b"Pending Review" in res_sub.data
    assert b"A function that calls itself." in res_sub.data

    with app.app_context():
        from app.models import Submission
        sub = Submission.query.filter_by(quiz_id=quiz_id).first()
        submission_id = sub.id
        assert sub.total_score == 0.0
        assert sub.answers[0].is_graded is False

    # 3. Log in as professor and view submission detail
    client.post('/auth/login', data={'email': 'prof1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)
    res_detail = client.get(f'/professor/submission/{submission_id}')
    assert res_detail.status_code == 200
    assert b"A function that calls itself." in res_detail.data
    assert b"Pending Review" in res_detail.data

    # 4. Grade the submission with 4.5 out of 5
    with app.app_context():
        ans_id = sub.answers[0].id
    res_grade = client.post(f'/professor/submission/{submission_id}/grade', data={
        f'score_{ans_id}': '4.5'
    }, follow_redirects=True)
    assert res_grade.status_code == 200
    assert b"Grade successfully updated!" in res_grade.data
    assert b"4.5" in res_grade.data
    assert b"Graded" in res_grade.data

    with app.app_context():
        sub_updated = db.session.get(Submission, submission_id)
        assert sub_updated.total_score == 4.5
        assert sub_updated.answers[0].score_awarded == 4.5
        assert sub_updated.answers[0].is_graded is True

    # 5. Log in as student and verify score is now updated
    client.post('/auth/login', data={'email': 'stud1@test.com', 'password': 'pass123', 'captcha': 'TEST_CAPTCHA'}, follow_redirects=True)
    res_stud_res = client.get(f'/student/result/{submission_id}')
    assert res_stud_res.status_code == 200
    assert b"4.5" in res_stud_res.data
    assert b"Pending Review" not in res_stud_res.data
