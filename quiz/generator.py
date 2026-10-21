import json
import re
from pathlib import Path
from typing import Optional, Tuple
from openai import AsyncOpenAI

from config import GROQ_API_KEY, GROQ_MODEL
from .models import QuizData, QuizQuestion, DifficultyLevel


QUIZ_SYSTEM_PROMPT = """You are an expert university professor and senior academic examiner in computer science and software engineering.
Your task is to create intellectually challenging, conceptual multiple choice questions (MCQs) evaluating deep subject knowledge based on the provided course lecture materials.

### STRICT RULES FOR QUESTION QUALITY:
1. **FOCUS ON REAL SUBJECT KNOWLEDGE**:
   - Questions MUST test domain concepts, technical definitions, mechanisms, methodologies, architectural trade-offs, and practical application.
   - For example: functional vs non-functional requirements, risk impact in project management, Agile vs Waterfall lifecycles, critical path determination, validation vs verification.

2. **ABSOLUTE PROHIBITION ON META-QUESTIONS**:
   - NEVER ask about document layout, document headings, titles of slides, page numbers, author names, lesson numbers, or document formatting.
   - FORBIDDEN examples: "What is the title of page 1?", "What is the heading of this document?", "Which chapter covers X?", "What is the first word on slide 2?". Any question of this type is completely unacceptable.

3. **COMPLEXITY & DEPTH**:
   - Frame questions with realistic scenarios, "why/how" problems, comparisons, or situational decision-making.
   - Avoid trivial superficial questions. Test understanding of principles, not rote memorization.

4. **DISTRACTORS (OPTIONS A, B, C, D)**:
   - Exactly 4 options (A, B, C, D).
   - Exactly ONE unambiguously correct answer.
   - The 3 distractors must be plausible technical alternatives or common student misconceptions, not absurd or obviously wrong options.

5. **EXPLANATION & CITATION**:
   - Detailed conceptual explanation clarifying why the correct choice is accurate and why the distractors are incorrect.
   - Cite the source document name and page number.

6. **OUTPUT FORMAT**:
   - Return valid, raw JSON conforming strictly to the requested schema.
"""



def extract_json_payload(text: str) -> dict:
    """Extracts a dictionary from raw LLM output, handling markdown fences and stray text."""
    # Try direct parse
    clean = text.strip()
    try:
        return json.loads(clean)
    except Exception:
        pass

    # Try extracting inside markdown json block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Try finding outer JSON object bounds { ... }
    first_brace = clean.find("{")
    last_brace = clean.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = clean[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError("Could not parse valid JSON from model response.")


async def generate_quiz_from_lectures(
    retriever,
    topic: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    client: Optional[AsyncOpenAI] = None,
    model_name: Optional[str] = None,
) -> Tuple[Optional[QuizData], Optional[str]]:
    """Retrieves lecture materials via ChromaDB and generates validated structured MCQs using Groq LLM.

    Args:
        retriever: ChromaDB LangChain retriever.
        topic: Concept or topic for the quiz.
        num_questions: Number of questions to generate (default 5).
        difficulty: "easy", "medium", or "hard".
        client: AsyncOpenAI client (optional, default configured with Groq).
        model_name: Model identifier (optional, default GROQ_MODEL).

    Returns:
        tuple of (QuizData or None, error_message or None)
    """
    # 1. Retrieve lecture context
    try:
        docs = retriever.invoke(topic)
    except Exception as e:
        return None, f"Failed to search lecture notes: {e}"

    if not docs:
        return None, (
            f"No lecture notes found matching topic '{topic}'. "
            "Please ensure relevant PDF documents are placed in the './lectures' folder."
        )

    # Format context chunks with citation metadata
    context_chunks = []
    for doc in docs:
        raw_source = doc.metadata.get("source", "Unknown")
        clean_source = Path(raw_source).name if raw_source != "Unknown" else "Lecture Material"
        page_num = doc.metadata.get("page", 0) + 1
        context_chunks.append(f"[Source: {clean_source} | Page: {page_num}]\n{doc.page_content}")

    context_text = "\n\n---\n\n".join(context_chunks)
    if len(context_text.strip()) < 50:
        return None, f"Insufficient lecture content found for '{topic}' to construct a grounded quiz."

    # 2. Build Groq prompt
    diff_level = DifficultyLevel.from_str(difficulty)
    difficulty_instructions = {
        DifficultyLevel.EASY: "Focus on fundamental definitions, core terminology, and basic direct concepts.",
        DifficultyLevel.MEDIUM: "Focus on conceptual comprehension, comparisons, processes, and practical application.",
        DifficultyLevel.HARD: "Focus on analytical reasoning, scenario analysis, trade-offs, and edge-case evaluation.",
    }[diff_level]

    user_prompt = f"""Generate a {num_questions}-question multiple choice quiz testing deep subject knowledge on the topic '{topic}'.
Target Difficulty: {diff_level.value.upper()} ({difficulty_instructions})

CRITICAL QUALITY REQUIREMENTS:
1. Every question MUST evaluate actual domain concepts, engineering principles, methodologies, comparisons, or realistic problem-solving scenarios.
2. ABSOLUTELY NO META-QUESTIONS: Never ask "What is the heading on page X?", "What is the title of the document?", or questions about slide layouts.
3. Make all 4 options (A, B, C, D) detailed, plausible, and technically substantive.

Available Lecture Materials:
{context_text}

JSON Output Schema:
{{
  "topic": "{topic}",
  "difficulty": "{diff_level.value}",
  "questions": [
    {{
      "id": 1,
      "question": "Question text here?",
      "options": {{
        "A": "Choice A text",
        "B": "Choice B text",
        "C": "Choice C text",
        "D": "Choice D text"
      }},
      "correct_answer": "B",
      "explanation": "Explanation grounded in the context.",
      "source": "Document.pdf, Page X"
    }}
  ]
}}
"""

    # 3. Call Groq
    if client is None:
        if not GROQ_API_KEY:
            return None, "GROQ_API_KEY is not configured in .env."
        client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )

    target_model = model_name or GROQ_MODEL

    try:
        response = await client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        payload = extract_json_payload(content)
        quiz_data = QuizData.model_validate(payload)

        # Normalize question IDs to 1..N
        for idx, q in enumerate(quiz_data.questions, start=1):
            q.id = idx

        # Limit to requested number of questions if model returned extra
        if len(quiz_data.questions) > num_questions:
            quiz_data.questions = quiz_data.questions[:num_questions]

        return quiz_data, None

    except Exception as e:
        # Fallback retry without response_format if model or endpoint had JSON schema restriction
        try:
            response = await client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt + "\nRespond with raw JSON only."},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            payload = extract_json_payload(content)
            quiz_data = QuizData.model_validate(payload)
            for idx, q in enumerate(quiz_data.questions, start=1):
                q.id = idx
            if len(quiz_data.questions) > num_questions:
                quiz_data.questions = quiz_data.questions[:num_questions]
            return quiz_data, None
        except Exception as retry_err:
            return None, f"Failed to generate structured quiz questions: {retry_err}"
