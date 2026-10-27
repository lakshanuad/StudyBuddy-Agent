import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from agents import Runner

from config import LECTURES_DIR, GROQ_MODEL, GROQ_API_KEY
from ingestion import get_vectorstore_and_retriever
from agent import create_study_agent
from commands import process_study_command
from quiz.generator import generate_quiz_from_lectures
from quiz.models import DifficultyLevel

# Initialize FastAPI App
app = FastAPI(title="StudyBuddy Web API", version="1.0.0")

# Global instances for agent and retriever
vectorstore = None
retriever = None
agent = None


def initialize_system():
    """Initializes the vectorstore and StudyBuddy agent."""
    global vectorstore, retriever, agent
    try:
        vectorstore, retriever = get_vectorstore_and_retriever()
        agent = create_study_agent(retriever)
        print("[*] StudyBuddy backend agent and retriever successfully initialized.")
    except Exception as e:
        print(f"[!] Warning during system initialization: {e}")


# Run initialization on module load
initialize_system()


# Request Schemas
class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 5
    difficulty: str = "medium"


# API Endpoints
@app.get("/api/status")
async def get_status():
    """Returns the current operational status of the agent and indexed materials."""
    pdf_files = list(LECTURES_DIR.glob("*.pdf")) if LECTURES_DIR.exists() else []
    return {
        "status": "online",
        "model": GROQ_MODEL,
        "has_api_key": bool(GROQ_API_KEY),
        "document_count": len(pdf_files),
        "documents": [p.name for p in pdf_files],
    }


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Processes user queries or study commands and returns the agent's response."""
    global agent
    if not agent:
        raise HTTPException(status_code=500, detail="Agent is not initialized.")

    raw_message = req.message.strip()
    if not raw_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Process study slash commands if present
    prompt, mode_label = process_study_command(raw_message)

    try:
        current_input = req.history + [{"role": "user", "content": prompt}]
        result = await Runner.run(agent, input=current_input)
        
        return {
            "reply": result.final_output,
            "mode_label": mode_label,
            "history": result.to_input_list(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/quiz/generate")
async def generate_quiz_endpoint(req: QuizRequest):
    """Generates an interactive MCQ quiz based on indexed lecture notes."""
    global retriever
    if not retriever:
        raise HTTPException(status_code=500, detail="Retriever not initialized.")

    diff_str = req.difficulty.lower()
    if diff_str == "easy":
        diff_enum = DifficultyLevel.EASY
    elif diff_str == "hard":
        diff_enum = DifficultyLevel.HARD
    else:
        diff_enum = DifficultyLevel.MEDIUM

    try:
        quiz_data, err = await generate_quiz_from_lectures(
            retriever=retriever,
            topic=req.topic,
            num_questions=max(1, min(20, req.num_questions)),
            difficulty=diff_enum,
        )

        if err or not quiz_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": err or "Failed to generate quiz."},
            )

        # Convert Pydantic quiz model to clean serializable dict
        questions_payload = []
        for q in quiz_data.questions:
            source_citation = getattr(q, "source", "Course Lecture Notes")
            questions_payload.append({
                "id": q.id,
                "question": q.question,
                "options": q.options,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "source": source_citation,
                "source_document": source_citation,
            })

        diff_val = quiz_data.difficulty.value if hasattr(quiz_data.difficulty, "value") else str(quiz_data.difficulty)

        return {
            "success": True,
            "quiz": {
                "topic": quiz_data.topic,
                "difficulty": diff_val,
                "total_questions": len(questions_payload),
                "questions": questions_payload,
            },
        }
    except Exception as e:
        print(f"[!] Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Quiz generation error: {str(e)}")


@app.get("/api/documents")
async def list_documents():
    """Lists all PDF documents in the lectures directory with size and modification timestamp."""
    if not LECTURES_DIR.exists():
        return {"documents": []}

    pdf_files = list(LECTURES_DIR.glob("*.pdf"))
    docs = []
    for f in pdf_files:
        stats = f.stat()
        docs.append({
            "name": f.name,
            "size_kb": round(stats.st_size / 1024, 1),
            "last_modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })

    return {"documents": docs}


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads a new lecture PDF and triggers vector store re-indexing."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    LECTURES_DIR.mkdir(parents=True, exist_ok=True)
    destination = LECTURES_DIR / file.filename

    content = await file.read()
    with open(destination, "wb") as f:
        f.write(content)

    # Automatically reindex vectorstore after upload
    initialize_system()

    return {
        "success": True,
        "filename": file.filename,
        "message": f"Successfully uploaded and re-indexed '{file.filename}'.",
    }


@app.post("/api/documents/reindex")
async def reindex_documents():
    """Manually re-indexes all PDF files into ChromaDB."""
    try:
        initialize_system()
        pdf_count = len(list(LECTURES_DIR.glob("*.pdf"))) if LECTURES_DIR.exists() else 0
        return {
            "success": True,
            "message": f"Successfully re-indexed {pdf_count} lecture PDF(s).",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reindexing failed: {str(e)}")


# Mount static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serves the main minimalist UI."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(content={"message": "StudyBuddy API is running. UI file is loading..."})


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
