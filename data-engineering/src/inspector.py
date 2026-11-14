from pathlib import Path
import json
import pymupdf


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = BASE_DIR / "documents"


def inspect_pdf(file):

    print("\n--- PDF Inspection ---")

    with pymupdf.open(file) as pdf:

        print(f"Pages: {len(pdf)}")
        print(f"Metadata: {pdf.metadata}")

        empty_pages = []
        total_characters = 0

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text")

            if not text.strip():
                empty_pages.append(page_number)

            total_characters += len(text)

            # Detect tables
            try:
                tables = page.find_tables()
                table_count = len(tables.tables)

                if table_count > 0:
                    print(
                        f"Page {page_number}: "
                        f"{table_count} table(s) detected."
                    )

            except Exception:
                pass

        print(f"Total extracted characters: {total_characters}")

        if empty_pages:

            print(f"Pages without extractable text: {empty_pages}")

            print(
                "Warning: These pages may be scanned "
                "or contain images."
            )

        if total_characters == 0:
            print("Warning: No extractable text found.")

        else:

            first_page_text = pdf[0].get_text("text")

            print("\nFirst page preview:")
            print(first_page_text[:500])


def inspect_json(file):

    print("\n--- JSON Inspection ---")

    with open(file, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    print(f"Root data type: {type(data).__name__}")

    if isinstance(data, dict):

        print(f"Top-level keys: {list(data.keys())}")

    elif isinstance(data, list):

        print(f"Number of records: {len(data)}")

        if data:

            print(f"First record type: {type(data[0]).__name__}")

            if isinstance(data[0], dict):
                print(f"Record fields: {list(data[0].keys())}")

    print("\nData preview:")

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )[:500]
    )
    
def inspect_jsonl(file):
    print("\n--- JSONL Inspection ---")

    records = []

    with open(file, "r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as error:
                print(f"Invalid JSON on line {line_number}: {error}")
                return

    print(f"Number of records: {len(records)}")

    if records:
        print(f"First record type: {type(records[0]).__name__}")

        if isinstance(records[0], dict):
            print(f"Record fields: {list(records[0].keys())}")

        print("\nFirst record preview:")
        print(json.dumps(records[0], ensure_ascii=False, indent=2)[:500])

    if not records:
        print("Warning: Empty JSONL file.")

def inspect_txt(file):

    print("\n--- TXT Inspection ---")

    with open(file, "r", encoding="utf-8-sig") as f:
        text = f.read()

    print(f"Characters: {len(text)}")
    print(f"Words: {len(text.split())}")
    print(f"Lines: {len(text.splitlines())}")

    if not text.strip():
        print("Warning: Empty text file.")

    else:

        print("\nText preview:")
        print(text[:500])


def inspect_documents():

    if not DOCUMENTS_DIR.exists():

        print("Documents folder does not exist!")
        return

    files = sorted(
        [
            file for file in DOCUMENTS_DIR.iterdir()
            if file.is_file()
        ]
    )

    if not files:

        print("No documents found.")
        return

    for file in files:

        print("\n" + "=" * 50)

        print(f"File: {file.name}")
        print(f"Size: {file.stat().st_size} bytes")

        extension = file.suffix.lower()

        try:
            if extension == ".pdf":
                inspect_pdf(file)
            elif extension == ".json":
                inspect_json(file)
            elif extension == ".jsonl":
                inspect_jsonl(file)
            elif extension == ".txt":
                inspect_txt(file)
            else:
                print("Unsupported file type.")

        except Exception as error:

            print(f"Could not inspect file: {error}")


if __name__ == "__main__":
    inspect_documents()
    