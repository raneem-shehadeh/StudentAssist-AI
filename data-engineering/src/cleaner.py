import re
import unicodedata
import hashlib


def clean_text(text):
    if not isinstance(text, str):
        return ""

    text = unicodedata.normalize("NFC", text)

    # Remove null characters
    text = text.replace("\x00", "")

    # Remove invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize whitespace
    text = re.sub(r"[^\S\n]+", " ", text)

    # Remove unnecessary spaces around lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove excessive empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def normalize_for_comparison(text):
    """
    Normalize text only for duplicate detection.
    Preserve the original cleaned text.
    """

    text = unicodedata.normalize("NFC", text)

    # Ignore capitalization
    text = text.casefold()

    # Treat multiple whitespace characters as one
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def get_text_hash(text):
    normalized_text = normalize_for_comparison(text)

    return hashlib.sha256(
        normalized_text.encode("utf-8")
    ).hexdigest()


def remove_duplicate_records(records):

    unique_records = []
    seen = {}

    for record in records:

        text = record.get("text", "")

        if not isinstance(text, str) or not text.strip():
            continue

        text_hash = get_text_hash(text)

        location = {
            "source": record.get("source"),
            "page": record.get("page")
        }

        # Check whether this information already exists
        if text_hash in seen:

            existing_record = seen[text_hash]

            # Preserve the additional source for citations
            if location not in existing_record["also_found_in"]:

                existing_record["also_found_in"].append(location)

            continue

        # Keep the first occurrence
        cleaned_record = record.copy()

        cleaned_record["also_found_in"] = []

        unique_records.append(cleaned_record)

        seen[text_hash] = cleaned_record

    return unique_records


def clean_records(records):

    cleaned_records = []

    for record in records:

        if not isinstance(record, dict):
            continue

        cleaned_record = record.copy()

        cleaned_record["text"] = clean_text(
            record.get("text", "")
        )

        if cleaned_record["text"]:
            cleaned_records.append(cleaned_record)

    # Remove duplicates across ALL sources
    cleaned_records = remove_duplicate_records(cleaned_records)

    return cleaned_records