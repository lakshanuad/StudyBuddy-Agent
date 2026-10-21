# 📚 StudyBuddy: CLI Study Agent

A Python-based CLI study agent using the **OpenAI Agents SDK**, **Groq** (`llama3-8b-8192`), and **LangChain** for local PDF lecture retrieval with **ChromaDB** and Hugging Face sentence embeddings.

---

## 🛠️ Project Structure

- [main.py](file:///d:/Agent%201.0/main.py): Lightweight application entry point that bootstraps and runs StudyBuddy.
- [config.py](file:///d:/Agent%201.0/config.py): Centralized configuration for environment variables, paths, model names, and logger settings.
- [ingestion.py](file:///d:/Agent%201.0/ingestion.py): PDF loading, text chunking, HuggingFace embeddings, and ChromaDB vector store retriever setup.
- [tools.py](file:///d:/Agent%201.0/tools.py): Agent tool definitions (`@function_tool search_lectures`) with page/source citations.
- [agent.py](file:///d:/Agent%201.0/agent.py): StudyBuddy Agent configuration with OpenAI Agents SDK and Groq client.
- [commands.py](file:///d:/Agent%201.0/commands.py): Specialized study mode parsers (`/quiz`, `/flashcards`, `/summary`, `/feynman`) and help text.
- [cli.py](file:///d:/Agent%201.0/cli.py): Interactive CLI session loop, conversational memory manager, and terminal output formatter.
- [ARCHITECTURE.md](file:///d:/Agent%201.0/ARCHITECTURE.md): Comprehensive technical architecture, system flow diagram, and component interaction guide.
- [FILE_STRUCTURE.md](file:///d:/Agent%201.0/FILE_STRUCTURE.md): Detailed directory tree, file-by-file breakdown, and module import graph.
- [requirements.txt](file:///d:/Agent%201.0/requirements.txt): Required Python dependencies.
- [.env.example](file:///d:/Agent%201.0/.env.example): Environment variable template.
- `lectures/`: Directory where you place course PDF files.

---

## 🚀 Getting Started

### 1. Install Dependencies

Create a virtual environment (optional but recommended) and install the packages:

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Obtain a Groq API key from [Groq Console](https://console.groq.com/keys).

Set it in your terminal or create a `.env` file from the template:

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your_groq_api_key_here"
```

**Windows (CMD):**
```cmd
set GROQ_API_KEY=your_groq_api_key_here
```

**Linux / macOS:**
```bash
export GROQ_API_KEY="your_groq_api_key_here"
```

Or copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Add Lecture PDFs

Place your course notes or lecture slides (`.pdf`) into the `./lectures` directory:

```bash
mkdir lectures
# copy your PDFs into ./lectures/
```

### 4. Run the Agent

Run the CLI application:

```bash
python main.py
```

---

## 🎯 Study Modes & Commands

StudyBuddy includes built-in interactive study modes and an advanced quiz evaluation engine:

| Command | Description | Example |
| :--- | :--- | :--- |
| **`/quiz [topic] [--questions N] [--difficulty easy\|medium\|hard]`** | Launches an interactive multiple-choice quiz with automated grading | `/quiz requirements --questions 5 --difficulty hard` |
| **`/flashcards [topic]`** | Creates structured term & definition study cards | `/flashcards agile models` |
| **`/summary [topic]`** | Produces a high-yield study sheet / summary | `/summary chapter 2` |
| **`/feynman [concept]`** | Explains complex topics using simple intuitive analogies | `/feynman eigenvalues` |
| **`/history`** | Checks how many interaction turns are held in context memory | `/history` |
| **`/clear`** | Clears conversation memory for a fresh session | `/clear` |
| **`/help`** | Shows the available command cheat-sheet | `/help` |
| **`exit` / `quit`** | Exits the application | `exit` |

---

## 📝 Interactive Quiz & Automatic Grading

StudyBuddy features an interactive examination system:

1. **Grounded Question Generation**: Questions are generated strictly from your local course lecture PDFs using Groq and ChromaDB vector retrieval.
2. **Hidden Answers**: Correct answers remain securely in the application state and are never exposed before completion.
3. **Turn-by-Turn Answering**: Questions are presented one at a time. Enter `A`, `B`, `C`, or `D`. Invalid inputs re-prompt without skipping. Type `/quitquiz` to cancel anytime.
4. **Deterministic Grading**: Automatically evaluated with zero extra LLM calls:
   - 90–100%: Excellent
   - 75–89%: Very Good
   - 60–74%: Good
   - 40–59%: Needs Improvement
   - Below 40%: Needs More Practice
5. **Post-Quiz Review**: Review incorrect answers, examine full explanations and page citations, retry the same quiz, or generate a fresh set.

### Running Tests

```bash
pytest test_quiz_interactive.py -v
```

---

## 🧠 Multi-turn Conversational Memory

StudyBuddy maintains context across turns during a session. You can ask follow-up questions seamlessly:

1. `You > What is gradient descent?`
2. `You > Can you give a numerical example of what you just explained?`
3. `You > /summary gradient descent`