import csv
import io
import secrets
import string
from flask import Blueprint, render_template, redirect, url_for, request, flash, Response, abort
from flask_login import login_required, current_user
from app.models import db, Quiz, Question, Choice, Submission, AnswerSubmission, StudentAccessCode
from app.services.parser import parse_markdown_to_quiz
from app.i18n import translate as _

professor_bp = Blueprint('professor', __name__)

@professor_bp.before_request
@login_required
def require_professor():
    if not current_user.is_professor:
        abort(403)

@professor_bp.route('/dashboard')
def dashboard():
    qcms = Quiz.query.filter_by(author_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    student_codes = StudentAccessCode.query.filter_by(created_by_id=current_user.id).order_by(StudentAccessCode.created_at.desc()).all()
    return render_template('professor/dashboard.html', qcms=qcms, student_codes=student_codes)

@professor_bp.route('/student-codes/generate', methods=['POST'])
def generate_student_code():
    num_codes = int(request.form.get('count', 1))
    num_codes = max(1, min(num_codes, 50))  # generate between 1 and 50 codes
    for i in range(num_codes):
        code = 'STU-' + ''.join(secrets.choice(string.ascii_uppercase + string.digits) for j in range(8))
        student_code = StudentAccessCode(code=code, created_by_id=current_user.id)
        db.session.add(student_code)
    db.session.commit()
    msg = _('codes_generated_success', count=num_codes) if num_codes > 1 else _('code_generated_success')
    flash(msg, 'success')
    return redirect(url_for('professor.dashboard'))

@professor_bp.route('/student-codes/<int:code_id>/delete', methods=['POST'])
def delete_student_code(code_id):
    student_code = StudentAccessCode.query.filter_by(id=code_id, created_by_id=current_user.id).first_or_404()
    db.session.delete(student_code)
    db.session.commit()
    flash(_('code_deleted_success'), 'info')
    return redirect(url_for('professor.dashboard'))

@professor_bp.route('/import', methods=['GET', 'POST'])
def import_qcm():
    if request.method == 'POST':
        markdown_text = ""
        # Check if file uploaded
        if 'md_file' in request.files and request.files['md_file'].filename:
            file = request.files['md_file']
            try:
                markdown_text = file.read().decode('utf-8')
            except Exception as e:
                flash(f"{_('import_error')} {str(e)}", 'danger')
                return render_template('professor/import.html')
        elif request.form.get('markdown_text', '').strip():
            markdown_text = request.form.get('markdown_text', '').strip()

        if not markdown_text:
            flash("Please provide markdown content via file or text input.", 'warning')
            return render_template('professor/import.html')

        try:
            quiz = parse_markdown_to_quiz(markdown_text, author_id=current_user.id)
            db.session.add(quiz)
            db.session.commit()
            flash(_('import_success'), 'success')
            return redirect(url_for('professor.dashboard'))
        except Exception as e:
            flash(f"{_('import_error')} {str(e)}", 'danger')

    return render_template('professor/import.html')

@professor_bp.route('/quiz/<int:quiz_id>/toggle')
def toggle_status(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, author_id=current_user.id).first_or_404()
    quiz.is_open = not quiz.is_open
    db.session.commit()
    flash(f"QCM is now {'Open' if quiz.is_open else 'Closed'}.", 'info')
    return redirect(url_for('professor.dashboard'))

@professor_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
def delete_quiz(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, author_id=current_user.id).first_or_404()
    db.session.delete(quiz)
    db.session.commit()
    flash("QCM deleted successfully.", 'info')
    return redirect(url_for('professor.dashboard'))

@professor_bp.route('/quiz/<int:quiz_id>/submissions')
def view_submissions(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, author_id=current_user.id).first_or_404()
    submissions = Submission.query.filter_by(quiz_id=quiz.id).order_by(Submission.submitted_at.desc()).all()
    return render_template('professor/submissions.html', quiz=quiz, submissions=submissions)

@professor_bp.route('/submission/<int:submission_id>')
def view_submission_detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.quiz.author_id != current_user.id:
        abort(403)
    return render_template('professor/submission_detail.html', submission=submission)

@professor_bp.route('/quiz/<int:quiz_id>/export-csv')
def export_csv(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, author_id=current_user.id).first_or_404()
    submissions = Submission.query.filter_by(quiz_id=quiz.id).order_by(Submission.submitted_at.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Username', 'Student Email', 'Score', 'Max Score', 'Percentage', 'Submitted At'])

    for sub in submissions:
        pct = (sub.total_score / sub.max_score * 100) if sub.max_score > 0 else 0
        writer.writerow([
            sub.student.username,
            sub.student.email,
            f"{sub.total_score:.2f}",
            f"{sub.max_score:.2f}",
            f"{pct:.1f}%",
            sub.submitted_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=qcm_{quiz.code}_results.csv"}
    )
