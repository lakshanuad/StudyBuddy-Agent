import uuid
from datetime import datetime
from typing import Dict, List, Optional
from .models import QuizQuestion, QuizData, QuestionResult, QuizResult
from .evaluator import evaluate_quiz


class QuizSession:
    """Manages the lifecycle and state of an interactive quiz session."""

    def __init__(self, quiz_data: QuizData):
        self.quiz_id = str(uuid.uuid4())
        self.topic = quiz_data.topic
        self.difficulty = quiz_data.difficulty
        self.questions: List[QuizQuestion] = list(quiz_data.questions)
        self.student_answers: Dict[int, str] = {}
        self.current_index: int = 0
        self.start_time: datetime = datetime.now()
        self.completion_time: Optional[datetime] = None
        self.is_completed: bool = False
        self.result: Optional[QuizResult] = None

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def current_question_number(self) -> int:
        return self.current_index + 1

    def start(self):
        """Initializes or restarts the quiz session."""
        self.current_index = 0
        self.student_answers.clear()
        self.start_time = datetime.now()
        self.completion_time = None
        self.is_completed = False
        self.result = None

    def get_current_question(self) -> Optional[QuizQuestion]:
        """Returns the current QuizQuestion to be answered, or None if completed."""
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def submit_answer(self, answer: str) -> bool:
        """Validates and records the student's answer for the current question.

        Args:
            answer: Raw input string from the student (e.g. 'A', 'b', etc.)

        Returns:
            True if answer is a valid option (A, B, C, D) and recorded, False otherwise.
        """
        if self.is_completed:
            return False

        current_q = self.get_current_question()
        if not current_q:
            return False

        clean_ans = answer.strip().upper()
        if clean_ans not in ("A", "B", "C", "D"):
            # Invalid input does NOT advance question
            return False

        self.student_answers[current_q.id] = clean_ans
        return True

    def next_question(self) -> bool:
        """Advances to the next question.

        Returns:
            True if there is another question, False if the quiz is now completed.
        """
        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.is_completed = True
            self.completion_time = datetime.now()
            self.calculate_score()
            return False
        return True

    def calculate_score(self) -> QuizResult:
        """Calculates deterministic score and saves results."""
        self.result = evaluate_quiz(
            questions=self.questions,
            student_answers=self.student_answers,
            topic=self.topic,
            difficulty=self.difficulty,
        )
        return self.result

    def get_results(self) -> Optional[QuizResult]:
        """Returns the evaluated QuizResult."""
        if not self.result and self.is_completed:
            self.calculate_score()
        return self.result

    def review_answers(self, incorrect_only: bool = False) -> List[QuestionResult]:
        """Returns list of QuestionResult for review."""
        res = self.get_results()
        if not res:
            return []
        if incorrect_only:
            return [qr for qr in res.question_results if not qr.is_correct]
        return res.question_results

    def reset(self):
        """Resets student answers to allow retrying the exact same quiz."""
        self.start()
