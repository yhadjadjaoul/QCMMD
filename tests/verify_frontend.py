import time
from playwright.sync_api import sync_playwright
from app import create_app, db
from app.models import User, StudentAccessCode

def setup_demo_users():
    app = create_app()
    with app.app_context():
        # Clean users if any
        User.query.delete()
        StudentAccessCode.query.delete()
        db.session.commit()

        # Create Professor
        prof = User(username="prof_demo", email="prof@demo.com", role="professor")
        prof.set_password("password123")
        db.session.add(prof)
        db.session.commit()

        # Create Student
        code = StudentAccessCode(code="STU-DEMO1234", created_by_id=prof.id, is_used=True)
        db.session.add(code)
        db.session.flush()

        student = User(username="student_demo", email="student@demo.com", role="student")
        student.set_password("password123")
        db.session.add(student)
        db.session.flush()
        code.used_by_id = student.id
        db.session.commit()

def run():
    setup_demo_users()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 1. Login page & test language toggle (French)
        page.goto("http://127.0.0.1:5000/auth/login")
        page.click("text=English")
        page.click("text=Français")
        page.wait_for_timeout(500)
        assert "Connexion" in page.content()

        # Switch back to English
        page.click("text=Français")
        page.click("text=English")
        page.wait_for_timeout(500)

        # 2. Login as Professor
        page.fill('input[name="email"]', "prof@demo.com")
        page.fill('input[name="password"]', "password123")
        page.fill('input[name="captcha"]', "TEST_CAPTCHA")
        page.click('button[type="submit"]')
        page.wait_for_url("**/professor/dashboard")

        # 3. Create a QCM with score code, hints, math, code
        page.goto("http://127.0.0.1:5000/professor/import")
        qcm_content = """# Algorithmique et Mathématiques
Un QCM complet pour évaluer les compétences.

## Mathématiques
### Calculer $2^3$ [score: 2]
> Hint: 2 multiplié par lui-même 3 fois.
- [x] 8
- [ ] 6
- [ ] 4

## Programmation Python
### Que produit l'instruction `len([10, 20, 30])` ? [score: 1]
[hint: Compter le nombre d'éléments dans la liste]
- [x] 3
- [ ] 2
- [ ] 4

### Écrire une boucle for en Python
- [t]
"""
        page.fill('textarea[name="markdown_text"]', qcm_content)
        page.click('button[type="submit"]')
        page.wait_for_url("**/professor/dashboard")

        # Generate a student code from dashboard
        page.click('button:has-text("Generate Access Code(s)")')
        page.wait_for_timeout(500)

        # Capture Professor Dashboard Screenshot
        page.screenshot(path="tests/professor_dashboard.png")

        # Get the QCM code
        qcm_code = page.locator("table tbody tr td span.badge.bg-dark").first.inner_text().strip()
        print(f"Created QCM with code: {qcm_code}")

        # Logout professor
        page.click("text=Log Out")
        page.wait_for_url("**/auth/login")

        # 4. Login as Student
        page.fill('input[name="email"]', "student@demo.com")
        page.fill('input[name="password"]', "password123")
        page.fill('input[name="captcha"]', "TEST_CAPTCHA")
        page.click('button[type="submit"]')
        page.wait_for_url("**/student/dashboard")

        # 5. Join QCM via code
        page.fill('input[name="code"]', qcm_code)
        page.click('button:has-text("Start Quiz")')
        page.wait_for_url(f"**/student/quiz/{qcm_code}")

        # Fill answers
        # Select first option for Q1 (8)
        page.locator('input[type="checkbox"]').first.check()
        # Answer text question
        page.fill('textarea', "for i in range(5): print(i)")

        # Screenshot student taking quiz
        page.screenshot(path="tests/student_taking_quiz.png")

        # Submit quiz
        page.click('button[type="submit"]')
        page.wait_for_timeout(1000)

        # Screenshot quiz results with hints and score
        page.screenshot(path="tests/student_results.png")

        browser.close()
        print("Frontend verification completed successfully!")

if __name__ == '__main__':
    run()
