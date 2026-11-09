def calculate_question_score(question, selected_choice_ids, text_response=""):
    """
    Computes the score for a single question.

    Requirements:
    - Default score is 1 (or question.max_score).
    - Score for a question should vary between 0 and max_score.
    - Even if an error should result in a negative value, 0 is the min:
      0.0 <= score <= question.max_score

    Grading methodology for choice questions:
    - Let C be number of correct choices.
    - Let W be number of incorrect choices.
    - If C == 0: no correct answers defined, return 0.0.
    - Each correctly selected answer earns + (max_score / C).
    - Each incorrectly selected answer incurs a penalty - (max_score / (W if W > 0 else C)).
    - Raw score can be negative, but bounded strictly to min 0.0 and max max_score:
      score = max(0.0, min(float(question.max_score), round(raw_score, 4)))
    """
    max_score = float(question.max_score if question.max_score is not None else 1.0)

    if question.question_type == 'text':
        # Text responses need professor review or can be marked complete with partial/default score if not empty
        # Default behavior: award 0 until professor reviews or 0.0
        return 0.0

    choices = question.choices
    if not choices:
        return 0.0

    selected_ids = set()
    for cid in selected_choice_ids:
        try:
            selected_ids.add(int(cid))
        except (ValueError, TypeError):
            pass

    correct_choice_ids = {c.id for c in choices if c.is_correct}
    incorrect_choice_ids = {c.id for c in choices if not c.is_correct}

    total_correct = len(correct_choice_ids)
    total_incorrect = len(incorrect_choice_ids)

    if total_correct == 0:
        return 0.0

    # Single-choice scenario
    if total_correct == 1:
        # If student picked exactly the 1 correct choice and no incorrect choices:
        if selected_ids == correct_choice_ids:
            return max_score
        else:
            # An error results in 0 (min is 0)
            return 0.0

    # Multiple-choice scenario
    # Gain per correct selection
    point_per_correct = max_score / total_correct
    # Penalty per incorrect selection
    penalty_per_wrong = max_score / (total_incorrect if total_incorrect > 0 else total_correct)

    raw_score = 0.0
    for cid in selected_ids:
        if cid in correct_choice_ids:
            raw_score += point_per_correct
        elif cid in incorrect_choice_ids:
            raw_score -= penalty_per_wrong

    # Question score should vary between 0 and max_score
    bounded_score = max(0.0, min(max_score, round(raw_score, 4)))
    return bounded_score
