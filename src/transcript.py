"""
YouTube Transcript Extraction Module.

Fetches transcripts from YouTube videos using the youtube-transcript-api library.
Supports auto-generated and manual captions in multiple languages.
Resolves redirect wrappers (Bing, Google) to the real YouTube URL when possible.
"""

import base64
import re
import time
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from youtube_transcript_api import YouTubeTranscriptApi, CouldNotRetrieveTranscript

# Instantiate the API client (v1.x instance-based API)
_ytt_api = YouTubeTranscriptApi()

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


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
        r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/|/live/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def _decode_bing_u_target(url: str) -> str | None:
    """Bing /ck/ links often carry the real URL base64-encoded in the `u` query param."""
    try:
        host = (urlparse(url).hostname or "").lower()
        if "bing.com" not in host:
            return None
        qs = parse_qs(urlparse(url).query)
        if "u" not in qs:
            return None
        raw = unquote(qs["u"][0]).strip()
        pad = (-len(raw)) % 4
        padded = raw + "=" * pad
        decoded_bytes = None
        for decoder in (base64.urlsafe_b64decode, base64.b64decode):
            try:
                decoded_bytes = decoder(padded)
                break
            except Exception:
                continue
        if not decoded_bytes:
            return None
        decoded = decoded_bytes.decode("utf-8", errors="strict").strip()
        if "youtube.com" in decoded or "youtu.be" in decoded:
            return decoded
    except Exception:
        return None
    return None


def _google_url_destination(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if "google." not in host:
        return None
    qs = parse_qs(urlparse(url).query)
    for key in ("q", "url"):
        if key in qs:
            dest = unquote(qs[key][0]).strip()
            if "youtube.com" in dest or "youtu.be" in dest:
                return dest
    return None


def resolve_youtube_url(url: str) -> str:
    """
    Turn pasted browser/search redirect links into a URL we can parse for a video ID.

    Handles: direct YouTube links, Bing ck/a wrappers, Google url?q= wrappers,
    and generic HTTP redirects ending on YouTube.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("Empty URL")

    try:
        extract_video_id(url)
        return url
    except ValueError:
        pass

    for extractor in (_decode_bing_u_target, _google_url_destination):
        inner = extractor(url)
        if inner:
            try:
                extract_video_id(inner)
                return inner
            except ValueError:
                continue

    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0),
            headers={"User-Agent": "Mozilla/5.0 (compatible; EnglishTutor/1.0)"},
        ) as client:
            r = client.get(url)
            final = str(r.url)
            extract_video_id(final)
            return final
    except Exception:
        pass

    raise ValueError(
        "Could not find a YouTube video in that link. Open the video on YouTube and copy "
        "the address bar URL (youtube.com/watch?v=… or youtu.be/…)."
    )


def _user_friendly_error(exc: Exception) -> str:
    """Convert youtube-transcript-api exceptions to user-friendly messages."""
    text = str(exc)
    if "Subtitles are disabled" in text or (
        "disabled" in text.lower() and "subtitle" in text.lower()
    ):
        return "This video has captions turned off (or no captions), so there is no transcript to analyze."
    if "Too many requests" in text or "captcha" in text.lower():
        return (
            "YouTube is temporarily limiting requests from this network (often a captcha). "
            "Wait several minutes and try again."
        )
    if "no longer available" in text.lower():
        return "That video appears unavailable or private."
    if "blocked" in text.lower():
        return (
            "YouTube has temporarily blocked requests from this IP. "
            "Wait a few minutes and try again."
        )
    line = text.strip().split("\n")[0]
    return line[:600] if line else "Could not load captions from YouTube."


def _build_result(video_id: str, fetched, language_code: str) -> dict:
    """Build a standardized transcript result dict from a FetchedTranscript."""
    full_text = " ".join(snippet.text for snippet in fetched)
    return {
        "video_id": video_id,
        "full_text": full_text,
        "segments": [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in fetched
        ],
        "language": language_code,
    }


def get_transcript(video_url: str) -> dict:
    """
    Fetch the transcript for a given YouTube video URL.

    Returns a dict with:
      - video_id: The YouTube video ID
      - full_text: The complete transcript as a single string
      - segments: List of {text, start, duration} dicts
      - language: The language code of the transcript used
    """
    resolved = resolve_youtube_url(video_url)
    video_id = extract_video_id(resolved)

    last_error = None

    # ── Strategy 1: Direct fetch (English) with retries ──────────────
    for attempt in range(MAX_RETRIES):
        try:
            fetched = _ytt_api.fetch(video_id, languages=["en"])
            if fetched and len(fetched) > 0:
                return _build_result(video_id, fetched, fetched.language_code)
        except CouldNotRetrieveTranscript:
            # English not available — fall through to list-based approach
            break
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            continue

    # ── Strategy 2: List all transcripts and try each ────────────────
    for attempt in range(MAX_RETRIES):
        try:
            transcript_list = _ytt_api.list(video_id)
            for transcript in transcript_list:
                try:
                    fetched = transcript.fetch()
                    if fetched and len(fetched) > 0:
                        return _build_result(video_id, fetched, transcript.language_code)
                except Exception:
                    continue
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            continue

    # ── All strategies exhausted ─────────────────────────────────────
    if last_error:
        raise ValueError(_user_friendly_error(last_error))

    raise ValueError(
        f"No usable transcript could be downloaded for this video ({video_id}). "
        "Confirm captions are available when you play it on YouTube."
    )
