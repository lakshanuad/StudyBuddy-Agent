import sys
from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel
from config import GROQ_API_KEY, GROQ_MODEL
from tools import create_search_tool

SYSTEM_INSTRUCTIONS = """You are StudyBuddy, an expert academic tutor and study assistant.
Your goal is to provide clear, structured, and easy-to-read explanations based on the student's lecture notes.

### Rules & Guidelines:
1. **Always Search Notes**: Use the 'search_lectures' tool to look up information from course lecture PDFs before answering questions about concepts, definitions, processes, or syllabus content.
2. **Direct & Uncluttered**: Do not use filler openings like "Sure, I can help!" or "Based on the retrieved documents...". Go straight to the answer.
3. **Structured Format**: Format your responses with clear Markdown headings and bullet points:
   - **### 💡 Overview / Direct Answer**: 1-2 concise sentences answering the question directly.
   - **### 🔍 Key Concepts & Breakdown**: Bullet points highlighting core terms in bold, steps in numbered lists, or comparisons in small tables.
   - **### 🎯 Practical Example / Intuition** (if relevant): A quick intuitive analogy or example.
   - **### 📚 Sources & References**: A bulleted list at the very bottom citing each source document and page number (e.g. `- Software Requirements.pdf (Page 4)`).
4. **Quiz / Flashcards / Summaries**: When asked for quizzes or flashcards, present questions and options clearly with spaced formatting, followed by answer keys with explanations.
"""


def create_study_agent(retriever):
    """Configures the Groq LLM client and instantiates the StudyBuddy Agent."""
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY is missing. Please set GROQ_API_KEY in your .env file.")
        sys.exit(1)

    client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    model = OpenAIChatCompletionsModel(
        model=GROQ_MODEL,
        openai_client=client,
    )

    search_tool = create_search_tool(retriever)

    agent = Agent(
        name="StudyBuddy",
        instructions=SYSTEM_INSTRUCTIONS,
        model=model,
        tools=[search_tool],
    )

    return agent
