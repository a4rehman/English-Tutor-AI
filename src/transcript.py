"""
YouTube Transcript Extraction Module.

Fetches transcripts from YouTube videos using the youtube-transcript-api library.
Supports auto-generated and manual captions in multiple languages.
"""

import re
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str:
    """
    Extract the video ID from various YouTube URL formats.

    Supports:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/v/VIDEO_ID
    """
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_transcript(video_url: str) -> dict:
    """
    Fetch the transcript for a given YouTube video URL.

    Returns a dict with:
      - video_id: The YouTube video ID
      - full_text: The complete transcript as a single string
      - segments: List of {text, start, duration} dicts
      - language: The language code of the transcript used
    """
    video_id = extract_video_id(video_url)

    # Try fetching English transcript first, then fall back to any available
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    transcript = None
    language = "en"

    # Priority: manual English -> auto-generated English -> any available
    try:
        transcript = transcript_list.find_manually_created_transcript(["en"])
        language = "en"
    except Exception:
        try:
            transcript = transcript_list.find_generated_transcript(["en"])
            language = "en"
        except Exception:
            # Fall back to first available transcript
            for t in transcript_list:
                transcript = t
                language = t.language_code
                break

    if transcript is None:
        raise ValueError(f"No transcript available for video: {video_id}")

    segments = transcript.fetch()
    full_text = " ".join(seg.text for seg in segments)

    return {
        "video_id": video_id,
        "full_text": full_text,
        "segments": [
            {"text": seg.text, "start": seg.start, "duration": seg.duration}
            for seg in segments
        ],
        "language": language,
    }
