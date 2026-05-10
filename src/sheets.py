"""
Google Sheets Integration Module.

Saves extracted vocabulary to a Google Sheet with duplicate checking.
Uses a service account for authentication via gspread.
"""

import os
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Expected column headers
HEADERS = [
    "Movie Title",
    "English Word",
    "Urdu Meaning",
    "English Meaning",
    "Example Sentence",
    "Level",
]


def _get_client() -> gspread.Client:
    """Create an authenticated gspread client using service account credentials."""
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/service_account.json")
    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"Google credentials file not found at: {creds_path}\n"
            "Please download your service account JSON from Google Cloud Console "
            "and place it in the credentials/ directory."
        )
    credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(credentials)


def _get_worksheet(client: gspread.Client, sheet_id: str) -> gspread.Worksheet:
    """Open the spreadsheet and get/create the first worksheet with proper headers."""
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet("Vocabulary")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Vocabulary", rows=1000, cols=6)

    # Ensure headers exist
    existing_headers = worksheet.row_values(1)
    if not existing_headers or existing_headers != HEADERS:
        worksheet.update("A1:F1", [HEADERS])
        worksheet.format("A1:F1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.3},
            "horizontalAlignment": "CENTER",
        })

    return worksheet


def get_existing_words(sheet_id: str) -> set:
    """Fetch all existing English words from the sheet to enable duplicate checking."""
    try:
        client = _get_client()
        worksheet = _get_worksheet(client, sheet_id)
        # Column B = English Word
        all_words = worksheet.col_values(2)
        # Skip the header row, normalize to lowercase
        return {word.lower().strip() for word in all_words[1:] if word.strip()}
    except Exception:
        return set()


def save_to_sheets(
    vocabulary_data: dict,
    sheet_id: Optional[str] = None,
) -> dict:
    """
    Save vocabulary data to Google Sheets with duplicate checking.

    Args:
        vocabulary_data: Dict with 'movie_title' and 'vocabulary' list
        sheet_id: Google Sheet ID (falls back to env variable)

    Returns:
        Dict with stats: total, saved, skipped, duplicates
    """
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError(
            "No Google Sheet ID provided. Set GOOGLE_SHEET_ID in your .env file."
        )

    client = _get_client()
    worksheet = _get_worksheet(client, sheet_id)

    # Get existing words for duplicate check
    existing_words = get_existing_words(sheet_id)

    movie_title = vocabulary_data.get("movie_title", "Unknown")
    vocab_list = vocabulary_data.get("vocabulary", [])

    rows_to_add = []
    skipped_words = []

    for item in vocab_list:
        word = item.get("word", "").strip()
        if not word:
            continue

        # Duplicate check (case-insensitive)
        if word.lower() in existing_words:
            skipped_words.append(word)
            continue

        rows_to_add.append([
            movie_title,
            word,
            item.get("urdu_meaning", ""),
            item.get("english_meaning", ""),
            item.get("example_sentence", ""),
            item.get("level", "Intermediate"),
        ])

        # Track to avoid duplicates within the same batch
        existing_words.add(word.lower())

    # Append all new rows at once
    if rows_to_add:
        worksheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")

    return {
        "total": len(vocab_list),
        "saved": len(rows_to_add),
        "skipped": len(skipped_words),
        "duplicates": skipped_words,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
    }
