# QCM Platform

A web platform for Multiple Choice Questions (QCM) inspired by [qcm_alchemy](https://github.com/qkzk/qcm_alchemy).

## Features
- **User Authentication**: Student and Professor roles with password hashing and session management.
- **Bilingual Support**: English and French (EN / FR) interface switchable at any time.
- **Markdown Import**: Create QCMs by uploading `.md` files or copying and pasting markdown source.
- **Hints and Solution Guidance**: Questions support hints (`> Hint: ...` or `[hint: ...]`) for students.
- **Custom Question Scores**: Score codes per question (`[score: X]` or `[points: X]`, default 1.0).
- **Bounded Scoring**: Question scores vary between 0.0 and max score. Penalties for wrong selections are deducted but bounded at 0.0 minimum.
- **LaTeX and Code Support**: Native LaTeX math rendering with MathJax and markdown code block support.
- **Professor Management & Export**: Dashboard to view, toggle open/close status, view student submissions, and export results to CSV.

## Running the Application
```bash
python3 run.py
```
Default URL: `http://localhost:5000`

## Running Tests
```bash
PYTHONPATH=. pytest tests/ -k "not verify_frontend"
```
