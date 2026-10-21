from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

    @classmethod
    def from_str(cls, val: str) -> "DifficultyLevel":
        v = val.strip().lower()
        if v in ("easy", "e", "1"):
            return cls.EASY
        if v in ("hard", "h", "3"):
            return cls.HARD
        return cls.MEDIUM


class QuizQuestion(BaseModel):
    id: int
    question: str = Field(..., description="The multiple choice question text")
    options: Dict[str, str] = Field(..., description="Dictionary with exactly keys A, B, C, D")
    correct_answer: str = Field(..., description="The correct option key: A, B, C, or D")
    explanation: str = Field(..., description="Explanation grounded in course lecture notes")
    source: str = Field(default="Course Lecture Notes", description="Document source name and page citation")

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ("A", "B", "C", "D"):
            raise ValueError(f"correct_answer must be one of 'A', 'B', 'C', 'D', got: {v}")
        return clean

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Dict[str, str]) -> Dict[str, str]:
        normalized = {}
        for k, text in v.items():
            key_upper = k.strip().upper()
            if key_upper in ("A", "B", "C", "D"):
                normalized[key_upper] = str(text).strip()

        required = {"A", "B", "C", "D"}
        if set(normalized.keys()) != required:
            missing = required - set(normalized.keys())
            raise ValueError(f"options must contain exactly keys A, B, C, D. Missing: {missing}")

        for k in required:
            if not normalized[k]:
                raise ValueError(f"Option {k} cannot be empty.")

        return normalized


class QuizData(BaseModel):
    topic: str
    difficulty: str = "medium"
    questions: List[QuizQuestion]

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, v: List[QuizQuestion]) -> List[QuizQuestion]:
        if not v:
            raise ValueError("Quiz must contain at least 1 question.")
        # Check for duplicate question texts
        seen_questions = set()
        for q in v:
            norm_q = " ".join(q.question.lower().split())
            if norm_q in seen_questions:
                # Discard or raise error on duplicate question
                pass
            seen_questions.add(norm_q)
        return v


class QuestionResult(BaseModel):
    question: QuizQuestion
    student_answer: Optional[str] = None
    is_correct: bool


class QuizResult(BaseModel):
    topic: str
    difficulty: str
    total_questions: int
    correct_count: int
    incorrect_count: int
    score_percentage: float
    grade: str
    question_results: List[QuestionResult]
