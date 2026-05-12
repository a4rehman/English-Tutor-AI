"""
English Vocabulary Extractor — FastAPI Server.

Serves the frontend and provides API endpoints for:
  - Extracting transcripts from YouTube videos
  - Generating vocabulary via OpenAI
  - Saving results to Excel (full or English+Urdu)
  - Chat Q&A grounded in the video transcript
"""

import os
import time
import traceback
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from src.transcript import get_transcript
from src.vocabulary import extract_vocabulary
from src.excel import save_to_excel, save_english_urdu_excel
from src.chat import chat_about_video

SESSION_TTL_SEC = 4 * 60 * 60
_transcript_sessions: dict[str, dict] = {}


def _cleanup_sessions() -> None:
    now = time.time()
    dead = [sid for sid, s in _transcript_sessions.items() if now - s.get("created", 0) > SESSION_TTL_SEC]
    for sid in dead:
        del _transcript_sessions[sid]


def _register_transcript_session(transcript: str, title: str) -> str:
    _cleanup_sessions()
    sid = str(uuid.uuid4())
    _transcript_sessions[sid] = {
        "transcript": transcript,
        "title": title or "Unknown",
        "messages": [],
        "created": time.time(),
    }
    return sid

app = FastAPI(
    title="English Vocabulary Extractor",
    description="Extract English vocabulary from YouTube videos for Urdu-speaking learners",
    version="1.0.0",
)

# Serve static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ─── Pydantic Models ────────────────────────────────────────────

class ExtractRequest(BaseModel):
    url: str
    video_title: str | None = None


class SaveRequest(BaseModel):
    vocabulary_data: dict


class ChatRequest(BaseModel):
    chat_session_id: str
    message: str = Field(..., min_length=1, max_length=4000)


# ─── Routes ─────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/api/extract")
async def extract_vocabulary_endpoint(request: ExtractRequest):
    """
    Full pipeline: YouTube URL → Transcript → OpenAI → Vocabulary JSON.
    """
    try:
        transcript_data = get_transcript(request.url)
        transcript_text = transcript_data["full_text"]
        video_id = transcript_data["video_id"]

        if not transcript_text or len(transcript_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Transcript is too short or empty. The video may not have captions.",
            )

        vocabulary_result = extract_vocabulary(
            transcript_text=transcript_text,
            video_title=request.video_title,
        )

        vocabulary_result["video_id"] = video_id
        vocabulary_result["transcript_language"] = transcript_data["language"]
        vocabulary_result["transcript_length"] = len(transcript_text.split())
        vocabulary_result["vocab_count"] = len(vocabulary_result.get("vocabulary", []))
        vocabulary_result["chat_session_id"] = _register_transcript_session(
            transcript_text,
            vocabulary_result.get("movie_title") or request.video_title or "",
        )

        return vocabulary_result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/api/save-to-excel")
async def save_to_excel_endpoint(request: SaveRequest):
    """
    Save vocabulary data to Excel with duplicate checking.
    """
    try:
        result = save_to_excel(
            vocabulary_data=request.vocabulary_data,
        )
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Excel error: {str(e)}")


@app.post("/api/save-english-urdu")
async def save_english_urdu_endpoint(request: SaveRequest):
    """Save only English word + Urdu meaning columns (second sheet in the workbook)."""
    try:
        result = save_english_urdu_excel(vocabulary_data=request.vocabulary_data)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Excel error: {str(e)}")


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Ask questions about the video; answers use only the stored transcript."""
    _cleanup_sessions()
    session = _transcript_sessions.get(request.chat_session_id)
    if not session:
        raise HTTPException(
            status_code=400,
            detail="Chat session expired or invalid. Extract vocabulary again from the video.",
        )
    try:
        session["messages"].append({"role": "user", "content": request.message.strip()})
        conv = session["messages"]
        max_msgs = 24
        if len(conv) > max_msgs:
            conv = conv[-max_msgs:]

        reply = chat_about_video(
            title=session["title"],
            transcript=session["transcript"],
            conversation=conv,
        )
        session["messages"].append({"role": "assistant", "content": reply})
        if len(session["messages"]) > max_msgs + 2:
            session["messages"] = session["messages"][-(max_msgs + 2) :]
        return {"reply": reply}
    except ValueError as e:
        session["messages"].pop()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if session["messages"] and session["messages"][-1].get("role") == "user":
            session["messages"].pop()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
