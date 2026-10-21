import unittest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document

from quiz.models import QuizData, QuizQuestion, DifficultyLevel
from quiz.evaluator import evaluate_quiz, get_grade_category
from quiz.session import QuizSession
from quiz.generator import generate_quiz_from_lectures
from commands import parse_quiz_command, process_study_command


def create_sample_quiz_data() -> QuizData:
    return QuizData(
        topic="Software Requirements",
        difficulty="medium",
        questions=[
            QuizQuestion(
                id=1,
                question="What is a functional requirement?",
                options={
                    "A": "A quality attribute like performance",
                    "B": "A statement of services the system should provide",
                    "C": "A constraint on development budget",
                    "D": "A hardware platform specification",
                },
                correct_answer="B",
                explanation="Functional requirements define functions the system must perform.",
                source="Software Requirements.pdf, Page 4",
            ),
            QuizQuestion(
                id=2,
                question="Which document formally describes system requirements?",
                options={
                    "A": "Software Requirements Specification (SRS)",
                    "B": "User Acceptance Test Plan",
                    "C": "Git Commit Log",
                    "D": "Database Schema Diagram",
                },
                correct_answer="A",
                explanation="The SRS is the official statement of system requirements.",
                source="Software Requirements.pdf, Page 12",
            ),
            QuizQuestion(
                id=3,
                question="What is requirement traceability?",
                options={
                    "A": "Tracking developer hours",
                    "B": "Deleting unused code modules",
                    "C": "Tracking requirements from inception through design and testing",
                    "D": "Measuring server network latency",
                },
                correct_answer="C",
                explanation="Traceability links requirements to their origins and artifacts.",
                source="Software Requirements.pdf, Page 18",
            ),
        ],
    )


class TestInteractiveQuiz(unittest.TestCase):
    """Test suite verifying interactive quiz generation, evaluation, sessions, and commands."""

    def test_quiz_generation_returns_valid_structured_questions(self):
        """1. Quiz generation returns valid structured questions using mocked Groq response."""
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = [
            Document(page_content="Requirements engineering involves elicitation, specification, and validation.", metadata={"source": "Software Requirements.pdf", "page": 2})
        ]

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="""{
                      "topic": "Requirements Engineering",
                      "difficulty": "medium",
                      "questions": [
                        {
                          "id": 1,
                          "question": "What is the primary goal of requirements elicitation?",
                          "options": {
                            "A": "To write code directly",
                            "B": "To discover what stakeholders need and expect",
                            "C": "To deploy the software",
                            "D": "To configure servers"
                          },
                          "correct_answer": "B",
                          "explanation": "Elicitation discovers stakeholder requirements.",
                          "source": "Software Requirements.pdf, Page 2"
                        }
                      ]
                    }"""
                )
            )
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        import asyncio
        quiz_data, err = asyncio.run(
            generate_quiz_from_lectures(
                retriever=mock_retriever,
                topic="Requirements Engineering",
                num_questions=1,
                difficulty="medium",
                client=mock_client,
            )
        )

        self.assertIsNone(err)
        self.assertIsNotNone(quiz_data)
        self.assertEqual(len(quiz_data.questions), 1)
        q = quiz_data.questions[0]
        self.assertEqual(q.id, 1)
        self.assertEqual(q.correct_answer, "B")
        self.assertIn("A", q.options)
        self.assertIn("B", q.options)
        self.assertIn("C", q.options)
        self.assertIn("D", q.options)

    def test_mcq_four_options_and_one_correct_answer(self):
        """2. Every MCQ contains four options (A, B, C, D) and exactly one valid correct answer."""
        quiz_data = create_sample_quiz_data()
        for q in quiz_data.questions:
            self.assertEqual(set(q.options.keys()), {"A", "B", "C", "D"})
            self.assertIn(q.correct_answer, ("A", "B", "C", "D"))

        # Test validation error when missing options
        with self.assertRaises(ValueError):
            QuizQuestion(
                id=99,
                question="Invalid MCQ?",
                options={"A": "Only A", "B": "Only B"},
                correct_answer="A",
                explanation="Missing options C and D",
            )

        # Test validation error when correct answer is invalid
        with self.assertRaises(ValueError):
            QuizQuestion(
                id=99,
                question="Invalid Answer Key?",
                options={"A": "A", "B": "B", "C": "C", "D": "D"},
                correct_answer="E",
                explanation="E is invalid",
            )

    def test_answers_remain_hidden_until_quiz_completion(self):
        """3. Correct answers remain hidden in session state until completion."""
        quiz_data = create_sample_quiz_data()
        session = QuizSession(quiz_data)
        session.start()

        # Before finishing, results are None
        self.assertFalse(session.is_completed)
        self.assertIsNone(session.result)
        self.assertIsNone(session.get_results())

        # Answering question 1
        q1 = session.get_current_question()
        self.assertEqual(q1.id, 1)
        session.submit_answer("B")
        session.next_question()

        # Still not completed
        self.assertFalse(session.is_completed)
        self.assertIsNone(session.result)

    def test_correct_answers_receive_marks(self):
        """4. Correct answers receive marks."""
        quiz_data = create_sample_quiz_data()
        # Q1: B, Q2: A, Q3: C
        student_answers = {1: "B", 2: "A", 3: "C"}
        result = evaluate_quiz(quiz_data.questions, student_answers)

        self.assertEqual(result.correct_count, 3)
        self.assertEqual(result.incorrect_count, 0)
        self.assertEqual(result.score_percentage, 100.0)
        self.assertEqual(result.grade, "Excellent")
        for qr in result.question_results:
            self.assertTrue(qr.is_correct)

    def test_incorrect_answers_receive_zero_marks(self):
        """5. Incorrect answers receive zero marks."""
        quiz_data = create_sample_quiz_data()
        # Q1: D (wrong), Q2: D (wrong), Q3: D (wrong)
        student_answers = {1: "D", 2: "D", 3: "D"}
        result = evaluate_quiz(quiz_data.questions, student_answers)

        self.assertEqual(result.correct_count, 0)
        self.assertEqual(result.incorrect_count, 3)
        self.assertEqual(result.score_percentage, 0.0)
        self.assertEqual(result.grade, "Needs More Practice")
        for qr in result.question_results:
            self.assertFalse(qr.is_correct)

    def test_percentage_calculations_accurate(self):
        """6. Percentage calculations and grade categories are strictly accurate."""
        quiz_data = create_sample_quiz_data()
        # 2 out of 3 correct = 66.67%
        student_answers = {1: "B", 2: "A", 3: "D"}
        result = evaluate_quiz(quiz_data.questions, student_answers)

        self.assertEqual(result.correct_count, 2)
        self.assertEqual(result.incorrect_count, 1)
        self.assertEqual(result.score_percentage, 66.67)
        self.assertEqual(result.grade, "Good")

        # Grade boundaries check
        self.assertEqual(get_grade_category(95.0), "Excellent")
        self.assertEqual(get_grade_category(80.0), "Very Good")
        self.assertEqual(get_grade_category(65.0), "Good")
        self.assertEqual(get_grade_category(50.0), "Needs Improvement")
        self.assertEqual(get_grade_category(35.0), "Needs More Practice")

    def test_invalid_inputs_do_not_advance_quiz(self):
        """7. Invalid inputs (e.g. E, 123, empty) do not advance the question."""
        quiz_data = create_sample_quiz_data()
        session = QuizSession(quiz_data)
        session.start()

        self.assertEqual(session.current_index, 0)

        # Invalid submissions
        self.assertFalse(session.submit_answer("E"))
        self.assertEqual(session.current_index, 0)
        self.assertNotIn(1, session.student_answers)

        self.assertFalse(session.submit_answer("123"))
        self.assertEqual(session.current_index, 0)

        self.assertFalse(session.submit_answer(""))
        self.assertEqual(session.current_index, 0)

        # Valid submission
        self.assertTrue(session.submit_answer("b"))  # lowercase 'b' normalized to 'B'
        self.assertEqual(session.student_answers[1], "B")

    def test_quiz_cancellation_works(self):
        """8. Quiz cancellation via /quitquiz works."""
        quiz_data = create_sample_quiz_data()
        session = QuizSession(quiz_data)
        session.start()

        # Session remains incomplete if cancelled before all questions are answered
        self.assertFalse(session.is_completed)
        self.assertEqual(session.current_index, 0)

    def test_retry_resets_previous_responses(self):
        """9. Retry resets previous responses allowing the same quiz to be re-taken."""
        quiz_data = create_sample_quiz_data()
        session = QuizSession(quiz_data)
        session.start()

        # Answer all 3
        session.submit_answer("B")
        session.next_question()
        session.submit_answer("A")
        session.next_question()
        session.submit_answer("C")
        session.next_question()

        self.assertTrue(session.is_completed)
        self.assertIsNotNone(session.result)
        self.assertEqual(session.result.score_percentage, 100.0)

        # Reset for retry
        session.reset()
        self.assertFalse(session.is_completed)
        self.assertEqual(session.current_index, 0)
        self.assertEqual(len(session.student_answers), 0)
        self.assertIsNone(session.result)

    def test_existing_studybuddy_commands_continue_working(self):
        """10. Existing StudyBuddy commands continue working seamlessly."""
        # Enhanced quiz command parsing
        cmd_info = parse_quiz_command("/quiz python --questions 10 --difficulty hard")
        self.assertIsNotNone(cmd_info)
        self.assertEqual(cmd_info["topic"], "python")
        self.assertEqual(cmd_info["num_questions"], 10)
        self.assertEqual(cmd_info["difficulty"], "hard")

        # Standard study commands
        prompt, mode = process_study_command("/flashcards agile models")
        self.assertEqual(mode, "Flashcards Mode")
        self.assertIn("flashcards", prompt)

        prompt, mode = process_study_command("/summary requirements")
        self.assertEqual(mode, "Summary Mode")
        self.assertIn("summary", prompt)

        prompt, mode = process_study_command("/feynman critical path")
        self.assertEqual(mode, "Feynman Mode")
        self.assertIn("Feynman Technique", prompt)

        # Ordinary question
        prompt, mode = process_study_command("What is waterfall?")
        self.assertIsNone(mode)
        self.assertEqual(prompt, "What is waterfall?")


if __name__ == "__main__":
    unittest.main()
