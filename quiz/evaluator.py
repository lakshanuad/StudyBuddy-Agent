from typing import Dict, List
from .models import QuizQuestion, QuestionResult, QuizResult


def get_grade_category(percentage: float) -> str:
    """Categorizes score percentage into academic grade labels."""
    if percentage >= 90.0:
        return "Excellent"
    elif percentage >= 75.0:
        return "Very Good"
    elif percentage >= 60.0:
        return "Good"
    elif percentage >= 40.0:
        return "Needs Improvement"
    else:
        return "Needs More Practice"


def evaluate_quiz(
    questions: List[QuizQuestion],
    student_answers: Dict[int, str],
    topic: str = "",
    difficulty: str = "medium",
) -> QuizResult:
    """Deterministically grades student answers against the stored correct answer key without LLM calls.

    Args:
        questions: List of QuizQuestion objects with stored correct answers.
        student_answers: Mapping of question ID (or index) to student selected option (A/B/C/D).
        topic: Quiz topic.
        difficulty: Quiz difficulty level.

    Returns:
        QuizResult containing complete statistics, score percentage, grade, and question results.
    """
    total = len(questions)
    if total == 0:
        return QuizResult(
            topic=topic,
            difficulty=difficulty,
            total_questions=0,
            correct_count=0,
            incorrect_count=0,
            score_percentage=0.0,
            grade="Needs More Practice",
            question_results=[],
        )

    correct_count = 0
    question_results: List[QuestionResult] = []

    for q in questions:
        raw_ans = student_answers.get(q.id)
        student_ans = raw_ans.strip().upper() if raw_ans else None
        is_correct = bool(student_ans and student_ans == q.correct_answer.strip().upper())
        if is_correct:
            correct_count += 1

        question_results.append(
            QuestionResult(
                question=q,
                student_answer=student_ans,
                is_correct=is_correct,
            )
        )

    incorrect_count = total - correct_count
    score_percentage = round((correct_count / total) * 100.0, 2)
    grade = get_grade_category(score_percentage)

    return QuizResult(
        topic=topic,
        difficulty=difficulty,
        total_questions=total,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        score_percentage=score_percentage,
        grade=grade,
        question_results=question_results,
    )
