"""
Excel Integration Module.

Saves extracted vocabulary to a local Excel file with duplicate checking.
Adds a heading for each new movie.
"""

import os
from typing import Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

EXCEL_FILE = "English_tutor.xlsx"
SHEET_EN_UR = "English_Urdu"
HEADERS_EN_UR = ["English Word", "Urdu Meaning"]

# Expected column headers (without Movie Title, since we will use a heading row)
HEADERS = [
    "English Word",
    "Urdu Meaning",
    "English Meaning",
    "Example Sentence",
    "Level",
]

def _get_workbook_and_sheet():
    """Load the existing workbook or create a new one."""
    if os.path.exists(EXCEL_FILE):
        wb = openpyxl.load_workbook(EXCEL_FILE)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Vocabulary"
        
    # Ensure headers exist if sheet is empty
    if ws.max_row == 1 and not ws.cell(row=1, column=1).value:
        for col_num, header in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="33334C", end_color="33334C", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
            
        # Set some default column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 50
        ws.column_dimensions['E'].width = 15

    return wb, ws


def get_existing_words() -> set:
    """Fetch all existing English words from the excel file to enable duplicate checking."""
    try:
        if not os.path.exists(EXCEL_FILE):
            return set()
            
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        ws = wb.active
        
        # Assume 'English Word' is in column A
        words = set()
        for row in range(2, ws.max_row + 1):
            val = ws.cell(row=row, column=1).value
            if val and isinstance(val, str):
                # Ignore heading rows which might span columns
                words.add(val.lower().strip())
        return words
    except Exception:
        return set()


def _ensure_en_ur_sheet(wb):
    """Return the English+Urdu sheet, creating it with headers if missing."""
    if SHEET_EN_UR in wb.sheetnames:
        return wb[SHEET_EN_UR]
    ws = wb.create_sheet(SHEET_EN_UR)
    for col_num, header in enumerate(HEADERS_EN_UR, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="33334C", end_color="33334C", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 32
    return ws


def get_existing_words_en_ur() -> set:
    """English words already stored on the English_Urdu sheet (column A, data rows only)."""
    try:
        if not os.path.exists(EXCEL_FILE):
            return set()
        wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
        if SHEET_EN_UR not in wb.sheetnames:
            return set()
        ws = wb[SHEET_EN_UR]
        words = set()
        for row in range(2, ws.max_row + 1):
            a = ws.cell(row=row, column=1).value
            b = ws.cell(row=row, column=2).value
            if a and isinstance(a, str) and b:
                words.add(a.lower().strip())
        return words
    except Exception:
        return set()


def save_english_urdu_excel(vocabulary_data: dict) -> dict:
    """
    Append English word + Urdu meaning only to sheet "English_Urdu" in the same workbook.
    """
    wb, _ = _get_workbook_and_sheet()
    ws = _ensure_en_ur_sheet(wb)

    existing_words = get_existing_words_en_ur()
    movie_title = vocabulary_data.get("movie_title", "Unknown")
    vocab_list = vocabulary_data.get("vocabulary", [])

    rows_to_add = []
    skipped_words = []

    for item in vocab_list:
        word = (item.get("word") or "").strip()
        if not word:
            continue
        if word.lower() in existing_words:
            skipped_words.append(word)
            continue
        rows_to_add.append([word, item.get("urdu_meaning", "")])
        existing_words.add(word.lower())

    if rows_to_add:
        next_row = ws.max_row + 1
        ws.merge_cells(
            start_row=next_row,
            start_column=1,
            end_row=next_row,
            end_column=len(HEADERS_EN_UR),
        )
        heading_cell = ws.cell(row=next_row, column=1, value=f"🎬 Movie/Video: {movie_title}")
        heading_cell.font = Font(bold=True, size=14, color="FFFFFF")
        heading_cell.fill = PatternFill(start_color="6366F1", end_color="6366F1", fill_type="solid")
        heading_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[next_row].height = 30

        for row_data in rows_to_add:
            ws.append(row_data)

        wb.save(EXCEL_FILE)

    return {
        "total": len(vocab_list),
        "saved": len(rows_to_add),
        "skipped": len(skipped_words),
        "duplicates": skipped_words,
        "file": EXCEL_FILE,
        "sheet": SHEET_EN_UR,
    }


def save_to_excel(vocabulary_data: dict) -> dict:
    """
    Save vocabulary data to Excel with duplicate checking.

    Args:
        vocabulary_data: Dict with 'movie_title' and 'vocabulary' list

    Returns:
        Dict with stats: total, saved, skipped, duplicates
    """
    wb, ws = _get_workbook_and_sheet()

    existing_words = get_existing_words()

    movie_title = vocabulary_data.get("movie_title", "Unknown")
    vocab_list = vocabulary_data.get("vocabulary", [])

    rows_to_add = []
    skipped_words = []

    for item in vocab_list:
        word = item.get("word", "").strip()
        if not word:
            continue

        if word.lower() in existing_words:
            skipped_words.append(word)
            continue

        rows_to_add.append([
            word,
            item.get("urdu_meaning", ""),
            item.get("english_meaning", ""),
            item.get("example_sentence", ""),
            item.get("level", "Intermediate"),
        ])
        existing_words.add(word.lower())

    if rows_to_add:
        # 1. Add Movie Heading
        next_row = ws.max_row + 1
        ws.merge_cells(start_row=next_row, start_column=1, end_row=next_row, end_column=len(HEADERS))
        heading_cell = ws.cell(row=next_row, column=1, value=f"🎬 Movie/Video: {movie_title}")
        heading_cell.font = Font(bold=True, size=14, color="FFFFFF")
        heading_cell.fill = PatternFill(start_color="6366F1", end_color="6366F1", fill_type="solid")
        heading_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[next_row].height = 30
        
        # 2. Add the new words
        for row_data in rows_to_add:
            ws.append(row_data)

        wb.save(EXCEL_FILE)

    return {
        "total": len(vocab_list),
        "saved": len(rows_to_add),
        "skipped": len(skipped_words),
        "duplicates": skipped_words,
        "file": EXCEL_FILE,
    }
