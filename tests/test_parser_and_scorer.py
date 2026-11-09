import pytest
from app import create_app, db
from app.models import User, Quiz, Question, Choice
from app.services.parser import parse_markdown_to_quiz
from app.services.scorer import calculate_question_score

@pytest.fixture
def test_app():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    with app.app_context():
        user = User(username='teacher1', email='teacher1@example.com', role='professor')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        yield app, user

def test_markdown_parsing_standard(test_app):
    app, user = test_app
    with app.app_context():
        md = """# Math & CS Quiz
A short quiz for students.

## Mathematics
### Calculate 2 + 2 [score: 2]
> Hint: It's an even number.
- [x] 4
- [ ] 5
- [ ] 22

## Computer Science
### Which of these are dynamic languages? [points: 3]
[hint: Python and Ruby are interpreted/dynamic]
- [x] Python
- [ ] C++
- [x] Ruby
- [ ] Rust

### Explain what an algorithm is.
- [t]
"""
        quiz = parse_markdown_to_quiz(md, author_id=user.id, code='TEST1234')
        db.session.add(quiz)
        db.session.commit()

        assert quiz.title == "Math & CS Quiz"
        assert quiz.code == "TEST1234"
        assert len(quiz.sections) == 2
        assert len(quiz.questions) == 3

        q1 = quiz.questions[0]
        assert q1.title == "Calculate 2 + 2"
        assert q1.max_score == 2.0
        assert q1.hint == "It's an even number."
        assert q1.is_multiple_choice is False
        assert q1.choice_type == 'single'
        assert len(q1.choices) == 3
        assert [c.is_correct for c in q1.choices] == [True, False, False]

        q2 = quiz.questions[1]
        assert q2.title == "Which of these are dynamic languages?"
        assert q2.max_score == 3.0
        assert "Python and Ruby" in q2.hint
        assert q2.is_multiple_choice is True
        assert q2.choice_type == 'multiple'
        assert len(q2.choices) == 4
        assert [c.is_correct for c in q2.choices] == [True, False, True, False]

        q3 = quiz.questions[2]
        assert q3.question_type == 'text'
        assert q3.max_score == 1.0  # default score 1

def test_scoring_single_choice(test_app):
    app, user = test_app
    with app.app_context():
        md = """# Single Choice
## Part 1
### What is 10 / 2?
- [x] 5
- [ ] 2
- [ ] 20
"""
        quiz = parse_markdown_to_quiz(md, author_id=user.id)
        db.session.add(quiz)
        db.session.commit()

        q = quiz.questions[0]
        c_correct = [c for c in q.choices if c.is_correct][0]
        c_wrong = [c for c in q.choices if not c.is_correct][0]

        # Correct selection: full points (1.0 default)
        score = calculate_question_score(q, [c_correct.id])
        assert score == 1.0

        # Wrong selection: 0.0 (min is 0)
        score_wrong = calculate_question_score(q, [c_wrong.id])
        assert score_wrong == 0.0

        # Both selected: 0.0
        score_both = calculate_question_score(q, [c_correct.id, c_wrong.id])
        assert score_both == 0.0

def test_scoring_multiple_choice_and_boundary(test_app):
    app, user = test_app
    with app.app_context():
        md = """# Multi Choice
## Part 1
### Select primes [score: 2]
- [x] 2
- [x] 3
- [ ] 4
- [ ] 6
"""
        quiz = parse_markdown_to_quiz(md, author_id=user.id)
        db.session.add(quiz)
        db.session.commit()

        q = quiz.questions[0]
        correct_ids = [c.id for c in q.choices if c.is_correct]
        wrong_ids = [c.id for c in q.choices if not c.is_correct]

        # Both correct chosen: max score 2.0
        assert calculate_question_score(q, correct_ids) == 2.0

        # 1 correct chosen, 0 wrong: half points (1.0)
        assert calculate_question_score(q, [correct_ids[0]]) == 1.0

        # 1 correct chosen, 1 wrong chosen: 1.0 - 1.0 = 0.0
        assert calculate_question_score(q, [correct_ids[0], wrong_ids[0]]) == 0.0

        # 0 correct chosen, 2 wrong chosen: raw -2.0, bounded to min 0.0
        assert calculate_question_score(q, wrong_ids) == 0.0

def test_markdown_parsing_case_tags(test_app):
    app, user = test_app
    with app.app_context():
        md = """# Tagged Quiz
## Section 1
### Question Case One [score: 1] [case: 1]
- [x] Option 1
- [ ] Option 2

### Question Case Two [case: 2]
- [x] Option A
- [x] Option B
- [ ] Option C

### Question Case Words [case: two]
- [x] Option X
- [ ] Option Y

### Question Type Radio [type: radio]
- [x] Radio 1
- [ ] Radio 2
"""
        quiz = parse_markdown_to_quiz(md, author_id=user.id)
        db.session.add(quiz)
        db.session.commit()

        q1 = quiz.questions[0]
        assert q1.title == "Question Case One"
        assert q1.choice_type == 'single'
        assert q1.is_multiple_choice is False

        q2 = quiz.questions[1]
        assert q2.title == "Question Case Two"
        assert q2.choice_type == 'multiple'
        assert q2.is_multiple_choice is True

        q3 = quiz.questions[2]
        assert q3.title == "Question Case Words"
        assert q3.choice_type == 'multiple'
        assert q3.is_multiple_choice is True

        q4 = quiz.questions[3]
        assert q4.title == "Question Type Radio"
        assert q4.choice_type == 'single'
        assert q4.is_multiple_choice is False
