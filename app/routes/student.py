import random
import markdown
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.models import db, Quiz, Question, Choice, Submission, AnswerSubmission
from app.services.scorer import calculate_question_score
from app.i18n import translate as _

student_bp = Blueprint('student', __name__)

@student_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code:
            flash(_('invalid_code'), 'warning')
            return render_template('student/dashboard.html')

        quiz = Quiz.query.filter_by(code=code).first()
        if not quiz:
            flash(_('invalid_code'), 'danger')
            return render_template('student/dashboard.html')

        return redirect(url_for('student.take_quiz', code=code))

    # Get student's previous submissions
    my_submissions = Submission.query.filter_by(student_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    # Also fetch currently open quizzes
    available_quizzes = Quiz.query.filter_by(is_open=True).order_by(Quiz.created_at.desc()).all()

    return render_template('student/dashboard.html', submissions=my_submissions, available_quizzes=available_quizzes)

@student_bp.route('/quiz/<string:code>')
@login_required
def take_quiz(code):
    quiz = Quiz.query.filter_by(code=code).first_or_404()

    if not quiz.is_open:
        flash(_('quiz_closed_message'), 'warning')
        return redirect(url_for('student.dashboard'))

    # Check if student already submitted
    existing = Submission.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).first()
    if existing:
        flash(_('already_submitted'), 'info')
        return redirect(url_for('student.view_result', submission_id=existing.id))

    # Prepare questions (optionally shuffle choices or questions)
    sections_data = []
    for section in quiz.sections:
        q_list = list(section.questions)
        questions_data = []
        for q in q_list:
            c_list = list(q.choices)
            # Shuffle choices for anti-cheat
            random.shuffle(c_list)
            # Convert markdown subtext to HTML
            rendered_subtext = markdown.markdown(q.subtext, extensions=['fenced_code', 'tables']) if q.subtext else ''
            questions_data.append({
                'obj': q,
                'choices': c_list,
                'html_subtext': rendered_subtext
            })
        sections_data.append({
            'obj': section,
            'questions': questions_data
        })

    return render_template('student/take_quiz.html', quiz=quiz, sections=sections_data)

@student_bp.route('/quiz/<string:code>/submit', methods=['POST'])
@login_required
def submit_quiz(code):
    quiz = Quiz.query.filter_by(code=code).first_or_404()

    if not quiz.is_open:
        flash(_('quiz_closed_message'), 'danger')
        return redirect(url_for('student.dashboard'))

    existing = Submission.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).first()
    if existing:
        flash(_('already_submitted'), 'info')
        return redirect(url_for('student.view_result', submission_id=existing.id))

    submission = Submission(
        quiz_id=quiz.id,
        student_id=current_user.id,
        total_score=0.0,
        max_score=quiz.total_max_score
    )
    db.session.add(submission)
    db.session.flush()

    total_awarded = 0.0

    for q in quiz.questions:
        if q.question_type == 'choice':
            # Checkbox values or radio values: name="q_{q.id}"
            selected_ids = request.form.getlist(f'q_{q.id}')
            score = calculate_question_score(q, selected_ids)
            ans = AnswerSubmission(
                submission_id=submission.id,
                question_id=q.id,
                selected_choice_ids=','.join(selected_ids),
                score_awarded=score,
                is_graded=True
            )
            total_awarded += score
            db.session.add(ans)
        elif q.question_type == 'text':
            text_resp = request.form.get(f'q_{q.id}', '').strip()
            score = 0.0
            ans = AnswerSubmission(
                submission_id=submission.id,
                question_id=q.id,
                text_response=text_resp,
                score_awarded=score,
                is_graded=False
            )
            db.session.add(ans)

    submission.total_score = round(total_awarded, 2)
    db.session.commit()

    flash(_('congratulations'), 'success')
    return redirect(url_for('student.view_result', submission_id=submission.id))

@student_bp.route('/result/<int:submission_id>')
@login_required
def view_result(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id and submission.quiz.author_id != current_user.id:
        abort(403)

    return render_template('student/result.html', submission=submission)
