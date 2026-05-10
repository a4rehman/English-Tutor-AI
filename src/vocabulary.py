"""
Vocabulary Extraction Module.

Sends YouTube transcripts to OpenAI GPT-4o and extracts structured vocabulary
data tailored for Urdu-speaking English learners.
"""

import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an English Vocabulary Extraction Assistant.

Your task is to analyze the transcript of a YouTube movie/video and extract useful English vocabulary words that can help an Urdu speaker improve English.

Instructions:

1. Read the full transcript carefully.
2. Extract only meaningful, high-value English vocabulary words and phrases.
3. Ignore:
   - very basic words (the, is, are, was, go, come, etc.)
   - names of people or places
   - slang with no educational value
   - repeated words
4. Prioritize:
   - advanced vocabulary
   - conversational phrases
   - movie/dialogue expressions
   - phrasal verbs
   - emotional expressions
   - practical spoken English
5. For each extracted word or phrase provide:
   - English Word/Phrase
   - Urdu Meaning (in Urdu script, simple and natural)
   - Simple English Meaning
   - Example sentence from the transcript (if available, otherwise create one)
   - Difficulty Level (Beginner, Intermediate, or Advanced)
6. Try to detect the movie/video title from the transcript context. If not detectable, use "Unknown".

Rules:
- Avoid duplicate words.
- Extract minimum 20 and maximum 100 useful vocabulary items depending on transcript size.
- Keep Urdu meanings simple and natural.
- Prefer practical spoken English over academic words.

IMPORTANT: Return your response as a valid JSON object with this exact structure:
{
  "movie_title": "Detected Title",
  "vocabulary": [
    {
      "word": "devastated",
      "urdu_meaning": "تباہ حال",
      "english_meaning": "extremely shocked or sad",
      "example_sentence": "I was devastated when I heard the news.",
      "level": "Intermediate"
    }
  ]
}

Return ONLY the JSON object, no markdown formatting, no code blocks, no extra text."""


def extract_vocabulary(transcript_text: str, video_title: str = None) -> dict:
    """
    Send transcript to OpenAI and extract structured vocabulary.

    Args:
        transcript_text: The full transcript text from YouTube
        video_title: Optional video title hint

    Returns:
        A dict with movie_title and vocabulary list
    """
    user_message = f"Here is the transcript of a YouTube video"
    if video_title:
        user_message += f' titled "{video_title}"'
    user_message += f":\n\n{transcript_text}"

    # Truncate very long transcripts to avoid token limits (roughly 15k words)
    words = transcript_text.split()
    if len(words) > 15000:
        transcript_text = " ".join(words[:15000])
        user_message = f"Here is the transcript (truncated) of a YouTube video"
        if video_title:
            user_message += f' titled "{video_title}"'
        user_message += f":\n\n{transcript_text}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content.strip()

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from potential markdown code blocks
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse OpenAI response as JSON: {content[:200]}")

    # Validate structure
    if "vocabulary" not in result:
        raise ValueError("OpenAI response missing 'vocabulary' key")

    if "movie_title" not in result:
        result["movie_title"] = video_title or "Unknown"

    return result
