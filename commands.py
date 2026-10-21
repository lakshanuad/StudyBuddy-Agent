import re
from typing import Optional, Tuple, Dict, Any

HELP_TEXT = """
StudyBuddy Commands:
  /quiz [topic] [--questions N] [--difficulty easy|medium|hard]
                       - Launch an interactive MCQ quiz with automated evaluation & grading
  /flashcards [topic]  - Generate high-yield study flashcards for quick review
  /summary [topic]     - Generate a structured summary & cheat sheet
  /feynman [concept]   - Explain complex concepts using intuitive, simple analogies
  /clear               - Reset the conversation memory for a fresh session
  /history             - View current session turn count
  /help                - Show this menu
  exit / quit          - Exit the application
"""


def parse_quiz_command(user_input: str) -> Optional[Dict[str, Any]]:
    """Parses an enhanced quiz command with optional arguments.

    Examples:
        /quiz machine learning
        /quiz python --questions 10
        /quiz operating systems --difficulty hard
        /quiz agile models -n 3 -d easy

    Returns:
        dict with keys {"is_quiz": True, "topic": str, "num_questions": int, "difficulty": str}
        or None if not a quiz command.
    """
    trimmed = user_input.strip()
    if not trimmed:
        return None

    parts = trimmed.split()
    cmd = parts[0].lower()
    if cmd not in ("/quiz", "/q"):
        return None

    num_questions = 5
    difficulty = "medium"
    topic_tokens = []

    idx = 1
    while idx < len(parts):
        token = parts[idx]
        lower_token = token.lower()

        if lower_token in ("--questions", "-questions", "--q", "-n"):
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                num_questions = max(1, min(20, int(parts[idx + 1])))
                idx += 2
                continue
            idx += 1
            continue
        elif lower_token in ("--difficulty", "-difficulty", "--diff", "-d"):
            if idx + 1 < len(parts):
                cand = parts[idx + 1].lower()
                if cand in ("easy", "medium", "hard"):
                    difficulty = cand
                    idx += 2
                    continue
            idx += 1
            continue
        else:
            # Inline parameter checks like --questions=10 or --difficulty=hard
            if lower_token.startswith("--questions=") or lower_token.startswith("-n="):
                val = token.split("=", 1)[1]
                if val.isdigit():
                    num_questions = max(1, min(20, int(val)))
                idx += 1
                continue
            elif lower_token.startswith("--difficulty=") or lower_token.startswith("-d="):
                val = token.split("=", 1)[1].lower()
                if val in ("easy", "medium", "hard"):
                    difficulty = val
                idx += 1
                continue

            topic_tokens.append(token)
            idx += 1

    topic = " ".join(topic_tokens).strip()
    return {
        "is_quiz": True,
        "topic": topic,
        "num_questions": num_questions,
        "difficulty": difficulty,
    }


def process_study_command(user_input: str) -> Tuple[str, Optional[str]]:
    """Parse special study slash commands into tailored agent prompts.

    Returns:
        tuple of (processed_prompt, command_label)
    """
    parts = user_input.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    topic = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/quiz", "/q"):
        target = f"on '{topic}'" if topic else "from the course lecture materials"
        return (
            f"Generate a multiple-choice quiz {target} based on the lecture notes. "
            "Present clear questions and provide correct answers and thorough explanations citing specific lecture sources and page numbers.",
            "Quiz Mode",
        )
    elif cmd in ("/flashcards", "/flash"):
        target = f"for '{topic}'" if topic else "for key concepts in the lecture notes"
        return (
            f"Create a set of 5 comprehensive flashcards {target} using the lecture materials. "
            "Format each card as:\n**Card [N]: [Concept / Term]**\n- **Front (Question):** ...\n- **Back (Answer & Key Takeaway):** ... (Include Source & Page)",
            "Flashcards Mode",
        )
    elif cmd in ("/summary", "/sum"):
        target = f"of '{topic}'" if topic else "of the core concepts in the lecture notes"
        return (
            f"Provide a high-yield, structured summary and cheat-sheet {target} based on the lecture notes. "
            "Structure the output with: 1. Core Definition & Purpose, 2. Key Mechanisms/Formulas, 3. Important Takeaways, and 4. Source & Page Citations.",
            "Summary Mode",
        )
    elif cmd in ("/feynman", "/f"):
        target = f"'{topic}'" if topic else "the core concept"
        return (
            f"Explain {target} using the Feynman Technique: break it down in plain, conversational language using a relatable real-world analogy. "
            "Keep it intuitive and easy to grasp while remaining technically accurate based on the lecture notes.",
            "Feynman Mode",
        )

    return user_input, None
