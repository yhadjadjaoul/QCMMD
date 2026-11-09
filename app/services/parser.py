import re
import secrets
import string
from app.models import Quiz, Section, Question, Choice

def generate_quiz_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def parse_markdown_to_quiz(markdown_text, author_id, code=None):
    """
    Parses markdown text into Quiz, Section, Question, and Choice objects.

    Syntax supported:
    - Frontmatter (optional):
        ---
        title: "..."
        ---
    - # Title
    - ## Section / Part
    - ### Question title
        Question body / subtext (supports LaTeX, markdown, code blocks, images)
        [score: 2] or [points: 2] or score code in question (defaults to 1.0)
        [hint: Some helpful hint for student] or > Hint: Some helpful hint
        - [x] Correct choice
        - [ ] Incorrect choice
        - [t] Text answer question
    """
    lines = markdown_text.replace('\r\n', '\n').split('\n')

    # Check frontmatter
    idx = 0
    title_from_frontmatter = None
    if len(lines) > 0 and lines[0].strip() == '---':
        idx = 1
        frontmatter_lines = []
        while idx < len(lines) and lines[idx].strip() != '---':
            frontmatter_lines.append(lines[idx])
            idx += 1
        if idx < len(lines) and lines[idx].strip() == '---':
            idx += 1
        for fline in frontmatter_lines:
            if ':' in fline:
                k, v = fline.split(':', 1)
                k = k.strip().lower()
                v = v.strip().strip('"\'')
                if k == 'title':
                    title_from_frontmatter = v

    quiz_title = title_from_frontmatter or "Untitled QCM"
    quiz_description = []

    # We will process line by line
    in_code_block = False

    parsed_sections = []
    current_section = None
    current_question = None

    # State tracking
    def ensure_section():
        nonlocal current_section
        if current_section is None:
            current_section = {
                'title': 'General',
                'subtext': '',
                'questions': []
            }
            parsed_sections.append(current_section)

    def finalize_question():
        nonlocal current_question
        if current_question:
            # Clean up subtext and extract inline tags if any remain
            subtext = '\n'.join(current_question['subtext_lines']).strip()

            # Check for [score: X] or [points: X]
            score_match = re.search(r'\[(?:score|points):\s*([0-9]+(?:\.[0-9]+)?)\]', current_question['title'], re.IGNORECASE)
            if not score_match:
                score_match = re.search(r'\[(?:score|points):\s*([0-9]+(?:\.[0-9]+)?)\]', subtext, re.IGNORECASE)
            if score_match:
                current_question['max_score'] = float(score_match.group(1))
                # remove tag from title/subtext
                current_question['title'] = re.sub(r'\[(?:score|points):\s*([0-9]+(?:\.[0-9]+)?)\]', '', current_question['title'], flags=re.IGNORECASE).strip()
                subtext = re.sub(r'\[(?:score|points):\s*([0-9]+(?:\.[0-9]+)?)\]', '', subtext, flags=re.IGNORECASE).strip()

            # Check for [hint: ...] or > Hint: ... or Hint: ...
            hint_match = re.search(r'\[hint:\s*([^\]]+)\]', subtext, re.IGNORECASE)
            if hint_match:
                current_question['hint'] = hint_match.group(1).strip()
                subtext = re.sub(r'\[hint:\s*([^\]]+)\]', '', subtext, flags=re.IGNORECASE).strip()
            else:
                hint_line_match = re.search(r'(?:^|\n)>\s*(?:Hint|Indice)\s*:\s*(.+)$', subtext, re.IGNORECASE | re.MULTILINE)
                if hint_line_match:
                    current_question['hint'] = hint_line_match.group(1).strip()
                    subtext = re.sub(r'(?:^|\n)>\s*(?:Hint|Indice)\s*:\s*(.+)$', '', subtext, flags=re.IGNORECASE | re.MULTILINE).strip()
                else:
                    hint_simple = re.search(r'(?:^|\n)(?:Hint|Indice)\s*:\s*(.+)$', subtext, re.IGNORECASE | re.MULTILINE)
                    if hint_simple:
                        current_question['hint'] = hint_simple.group(1).strip()
                        subtext = re.sub(r'(?:^|\n)(?:Hint|Indice)\s*:\s*(.+)$', '', subtext, flags=re.IGNORECASE | re.MULTILINE).strip()

            current_question['subtext'] = subtext
            current_section['questions'].append(current_question)
            current_question = None

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if stripped.startswith('```'):
            in_code_block = not in_code_block
            if current_question:
                current_question['subtext_lines'].append(line)
            elif current_section:
                current_section['subtext'] += line + '\n'
            else:
                quiz_description.append(line)
            idx += 1
            continue

        if not in_code_block:
            # Check for # Title
            if stripped.startswith('# ') and not stripped.startswith('##'):
                if not title_from_frontmatter:
                    quiz_title = stripped[2:].strip()
                idx += 1
                continue

            # Check for ## Section
            if stripped.startswith('## ') and not stripped.startswith('###'):
                finalize_question()
                current_section = {
                    'title': stripped[3:].strip(),
                    'subtext': '',
                    'questions': []
                }
                parsed_sections.append(current_section)
                idx += 1
                continue

            # Check for ### Question
            if stripped.startswith('### '):
                finalize_question()
                ensure_section()
                q_title = stripped[4:].strip()
                current_question = {
                    'title': q_title,
                    'subtext_lines': [],
                    'question_type': 'choice',
                    'max_score': 1.0,
                    'hint': '',
                    'choices': []
                }
                idx += 1
                continue

            # Check for choices inside a question
            if current_question is not None:
                # - [x] or - [ ] or - [t]
                choice_match = re.match(r'^[-\*]\s*\[([ xXtT])\]\s*(.*)$', stripped)
                if choice_match:
                    mark = choice_match.group(1).lower()
                    text = choice_match.group(2).strip()
                    if mark == 't':
                        current_question['question_type'] = 'text'
                    else:
                        is_correct = (mark == 'x')
                        current_question['choices'].append({
                            'text': text,
                            'is_correct': is_correct
                        })
                    idx += 1
                    continue

        # Regular line
        if current_question:
            current_question['subtext_lines'].append(line)
        elif current_section:
            current_section['subtext'] += line + '\n'
        else:
            quiz_description.append(line)

        idx += 1

    finalize_question()

    if not parsed_sections:
        ensure_section()

    # Now create Database objects
    quiz = Quiz(
        code=code or generate_quiz_code(),
        title=quiz_title,
        description='\n'.join(quiz_description).strip(),
        raw_markdown=markdown_text,
        author_id=author_id
    )

    q_order = 0
    for s_idx, s_data in enumerate(parsed_sections):
        section = Section(
            title=s_data['title'],
            subtext=s_data['subtext'].strip(),
            order_index=s_idx
        )
        quiz.sections.append(section)

        for q_data in s_data['questions']:
            q_order += 1
            question = Question(
                title=q_data['title'],
                subtext=q_data['subtext'],
                question_type=q_data['question_type'],
                max_score=q_data['max_score'],
                hint=q_data['hint'],
                order_index=q_order,
                section=section,
                quiz=quiz
            )
            quiz.questions.append(question)

            for c_idx, c_data in enumerate(q_data['choices']):
                choice = Choice(
                    text=c_data['text'],
                    is_correct=c_data['is_correct'],
                    order_index=c_idx,
                    question=question
                )
                question.choices.append(choice)

    return quiz
