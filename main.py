"""
English Vocabulary Extractor — FastAPI Server.

Serves the frontend and provides API endpoints for:
  - Extracting transcripts from YouTube videos
  - Generating vocabulary via OpenAI
  - Saving results to Google Sheets
"""

import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from src.transcript import get_transcript
from src.vocabulary import extract_vocabulary
from src.sheets import save_to_sheets

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
    sheet_id: str | None = None


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
        "sheets_configured": bool(os.getenv("GOOGLE_SHEET_ID")),
    }


@app.post("/api/extract")
async def extract_vocabulary_endpoint(request: ExtractRequest):
    """
    Full pipeline: YouTube URL → Transcript → OpenAI → Vocabulary JSON.

    1. Extracts transcript from the given YouTube video
    2. Sends transcript to OpenAI for vocabulary extraction
    3. Returns structured vocabulary data
    """
    try:
        # Step 1: Get transcript
        transcript_data = get_transcript(request.url)
        transcript_text = transcript_data["full_text"]
        video_id = transcript_data["video_id"]

        if not transcript_text or len(transcript_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Transcript is too short or empty. The video may not have captions.",
            )

        # Step 2: Extract vocabulary via OpenAI
        vocabulary_result = extract_vocabulary(
            transcript_text=transcript_text,
            video_title=request.video_title,
        )

        # Enrich response with metadata
        vocabulary_result["video_id"] = video_id
        vocabulary_result["transcript_language"] = transcript_data["language"]
        vocabulary_result["transcript_length"] = len(transcript_text.split())
        vocabulary_result["vocab_count"] = len(vocabulary_result.get("vocabulary", []))

        return vocabulary_result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/api/save-to-sheets")
async def save_to_sheets_endpoint(request: SaveRequest):
    """
    Save vocabulary data to Google Sheets with duplicate checking.
    """
    try:
        result = save_to_sheets(
            vocabulary_data=request.vocabulary_data,
            sheet_id=request.sheet_id,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Google Sheets error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
