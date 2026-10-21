# 📁 Project File Structure: StudyBuddy Agent

This document provides a comprehensive overview of the repository's directory layout, file responsibilities, and internal dependency graphs.

---

## 🌳 Directory Tree

```text
Agent 1.0/
│
├── ⚙️ Configuration & Environment
│   ├── config.py                 # Global constants, paths, environment variable loader & log levels
│   ├── .env                      # Private environment variables (API keys)
│   ├── .env.example              # Environment variable template for repository cloning
│   └── requirements.txt          # Python package dependencies
│
├── 🧠 Core Application Modules
│   ├── main.py                   # Application entry point & async bootstrap
│   ├── ingestion.py              # PDF document loading, text chunking, embeddings & ChromaDB
│   ├── tools.py                  # OpenAI Agents SDK function tools (@function_tool)
│   ├── agent.py                  # StudyBuddy Agent configuration & Groq LLM setup
│   ├── commands.py               # Study mode slash commands & enhanced quiz parameter parser
│   └── cli.py                    # Interactive CLI loop, conversational memory & quiz engine
│
├── 📝 Interactive Quiz Subsystem
│   ├── quiz/
│   │   ├── __init__.py           # Package exports for models, evaluator, generator, and session
│   │   ├── models.py             # Pydantic models for MCQ schemas, validation, and quiz results
│   │   ├── generator.py          # Grounded question generation from ChromaDB context with Groq LLM
│   │   ├── evaluator.py          # Deterministic grading logic, score calculation & grade classification
│   │   └── session.py            # QuizSession manager for turn progression, state & retries
│
├── 📚 Knowledge & Vector Data
│   ├── lectures/                 # Directory for course lecture PDFs
│   │   ├── README.txt            # Usage instructions for placing PDF materials
│   │   ├── Software Development Models_Lesson 03_V2.0.pdf
│   │   ├── Software Project Management_V1.0.pdf
│   │   └── Software Requirements.pdf
│   └── chroma_db/                # Persistent local Chroma vector database files
│
├── 🧪 Testing
│   └── test_quiz_interactive.py  # Comprehensive test suite covering quiz generation, evaluation & session
│
└── 📖 Documentation
    ├── README.md                 # Project overview, installation, and user quickstart guide
    ├── ARCHITECTURE.md           # Technical architecture, system flow diagram, and component interaction guide
    └── FILE_STRUCTURE.md         # This comprehensive file structure reference
```

---

## 📄 File Details & Responsibilities

### 1. Application Entry & Modules

| File | Purpose | Key Exports / Functions | Key Dependencies |
| :--- | :--- | :--- | :--- |
| [main.py](file:///d:/Agent%201.0/main.py) | Application entry point. Coordinates initialization and launches CLI. | `main()` | `ingestion.py`, `agent.py`, `cli.py` |
| [config.py](file:///d:/Agent%201.0/config.py) | Centralizes all runtime configurations, model parameters, directories, and log suppressions. | `GROQ_API_KEY`, `GROQ_MODEL`, `LECTURES_DIR`, `CHROMA_DIR`, `EMBEDDING_MODEL_NAME`, `RETRIEVER_K` | `python-dotenv`, `pathlib`, `os` |
| [ingestion.py](file:///d:/Agent%201.0/ingestion.py) | Ingests PDF course documents, splits text into overlapping chunks, generates embeddings, and creates ChromaDB retriever. | `get_vectorstore_and_retriever()` | `langchain_community`, `langchain_text_splitters`, `chromadb`, `config.py` |
| [tools.py](file:///d:/Agent%201.0/tools.py) | Exposes document retrieval as an agent tool using OpenAI Agents SDK. | `create_search_tool(retriever)` | `openai-agents` (`@function_tool`) |
| [agent.py](file:///d:/Agent%201.0/agent.py) | Builds the Groq AsyncOpenAI client, configures LLM model wrapper, and instantiates the StudyBuddy Agent. | `create_study_agent(retriever)` | `openai-agents`, `openai.AsyncOpenAI`, `tools.py`, `config.py` |
| [commands.py](file:///d:/Agent%201.0/commands.py) | Implements study mode prompt templates and slash command router (`/quiz`, `/flashcards`, `/summary`, `/feynman`). | `HELP_TEXT`, `parse_quiz_command()`, `process_study_command()` | Standard Library |
| [cli.py](file:///d:/Agent%201.0/cli.py) | Runs the interactive terminal UI, manages multi-turn conversational history across turns, and handles interactive quiz sessions. | `start_cli_session(agent, retriever)` | `openai-agents` (`Runner`), `commands.py`, `quiz` package |
| `quiz/models.py` | Defines Pydantic data schemas and validation rules for questions, choices, and result summaries. | `QuizQuestion`, `QuizData`, `QuizResult` | `pydantic` |
| `quiz/generator.py` | Retrieves relevant lecture text and prompts Groq LLM to generate structured JSON MCQs. | `generate_quiz_from_lectures()` | `openai.AsyncOpenAI`, `quiz/models.py` |
| `quiz/evaluator.py` | Deterministically grades student responses, computes percentage scores, and assigns grades without LLM calls. | `evaluate_quiz()`, `get_grade_category()` | `quiz/models.py` |
| `quiz/session.py` | Manages quiz state, turn-by-turn question serving, answer recording, and retries. | `QuizSession` | `quiz/models.py`, `quiz/evaluator.py` |
| `test_quiz_interactive.py` | Automated tests verifying all 10 interactive quiz requirements. | `TestInteractiveQuiz` | `unittest`, `pytest` |

---

### 2. Configuration & Dependencies

| File | Description |
| :--- | :--- |
| [requirements.txt](file:///d:/Agent%201.0/requirements.txt) | Lists Python dependencies (`openai-agents`, `openai`, `langchain`, `chromadb`, `sentence-transformers`, `pypdf`, `python-dotenv`, `rich`, `pydantic`). |
| [.env.example](file:///d:/Agent%201.0/.env.example) | Template defining required keys (`GROQ_API_KEY`). |
| [chroma_db/](file:///d:/Agent%201.0/chroma_db) | Local persistent vector database generated by ChromaDB containing vector embeddings of all parsed PDF chunks. |
| [lectures/](file:///d:/Agent%201.0/lectures) | Local directory holding user lecture PDF files. |
