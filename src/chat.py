"""
Video Q&A chat — answers grounded in the YouTube transcript only.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def get_client(api_key: str = None) -> OpenAI:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API key is missing. Please set OPENAI_API_KEY.")
    return OpenAI(api_key=key)

CHAT_SYSTEM = """You are a tutor helping Urdu-speaking learners understand a YouTube video.

Rules:
- Answer ONLY using the transcript the user provides in the first message of the conversation. Do not invent scenes, quotes, or facts that are not supported by the transcript.
- If the transcript does not contain enough information, say so clearly (you may say this in English and briefly in Urdu if helpful).
- Be concise but clear. For difficult English, you may add a short Urdu explanation when it helps.
- If asked about vocabulary from the video, explain using the transcript context."""


def _truncate_transcript(text: str, max_words: int = 12000) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "\n\n[Transcript truncated for length. Earlier parts omitted.]"


def build_chat_completion_messages(
    *,
    title: str,
    transcript: str,
    conversation: list[dict],
) -> list[dict]:
    """Build OpenAI messages: system + transcript context + Q&A turns."""
    body = _truncate_transcript(transcript)
    return [
        {"role": "system", "content": CHAT_SYSTEM},
        {
            "role": "user",
            "content": f'Video title (hint): "{title}"\n\nTranscript (your only source of facts about this video):\n\n{body}\n\n---\nAnswer my following questions using only this transcript.',
        },
        {
            "role": "assistant",
            "content": "Understood. I will answer only from this transcript. What would you like to know?",
        },
        *conversation,
    ]


def chat_about_video(*, title: str, transcript: str, conversation: list[dict], api_key: str = None) -> str:
    """
    conversation: list of {"role": "user"|"assistant", "content": str} for the Q&A thread
    (should end with the latest user message).
    """
    messages = build_chat_completion_messages(
        title=title or "Unknown",
        transcript=transcript,
        conversation=conversation,
    )
    client = get_client(api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4,
        max_tokens=1024,
    )
    return (response.choices[0].message.content or "").strip()
