from pathlib import Path

import json

from src.extractor import extract_document

from src.cleaner import clean_records

from src.chunker import chunk_records

from src.chunker import count_tokens

# Project directories

BASE_DIR = Path(__file__).resolve().parent.parent

DOCUMENTS_DIR = BASE_DIR / "documents"

OUTPUT_DIR = BASE_DIR / "output"

def validate_chunks(chunks):

    required_fields = {
        "id",
        "text",
        "source",
        "page",
        "chunk_index"
    }

    for index, chunk in enumerate(chunks):

        missing_fields = required_fields - set(chunk.keys())

        if missing_fields:
            raise ValueError(
                f"Chunk {index} is missing: {missing_fields}"
            )

        if not chunk["text"].strip():
            raise ValueError(
                f"Chunk {index} contains empty text."
            )

    # Check unique IDs
    ids = [chunk["id"] for chunk in chunks]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected.")

    # Check token limit
    for index, chunk in enumerate(chunks):

        if count_tokens(chunk["text"]) > 128:
            raise ValueError(
                f"Chunk {index} exceeds the 128 token limit."
            )

def main():

    print("\nStarting RAG Data Pipeline...")

    # Check documents folder

    if not DOCUMENTS_DIR.exists():

        print("Documents folder does not exist!")

        return

    supported_extensions = {
    ".pdf",
    ".json",
    ".jsonl",
    ".txt"
}

    files = sorted(

        [

            file for file in DOCUMENTS_DIR.iterdir()

            if file.is_file()

        ]

    )

    if not files:

        print("No documents found.")

        return

    all_records = []

    successful_files = 0

    failed_files = 0

    # Step 1: Data Extraction

    print("\n[1] Extracting documents...")

    for file in files:

        if file.suffix.lower() not in supported_extensions:

            print(f"Skipping unsupported file: {file.name}")

            continue

        try:

            records = extract_document(file)

            all_records.extend(records)

            successful_files += 1

            print(

                f"Extracted: {file.name} "

                f"({len(records)} records)"

            )

        except Exception as error:

            failed_files += 1

            print(

                f"Error processing {file.name}: {error}"

            )

    if not all_records:

        print("\nNo records were extracted.")

        return

    # Step 2: Data Cleaning

    print("\n[2] Cleaning data...")

    original_count = len(all_records)

    cleaned_records = clean_records(all_records)

    print(f"Records before cleaning: {original_count}")

    print(f"Records after cleaning: {len(cleaned_records)}")

    # Step 3: Chunking

    print("\n[3] Creating chunks...")

    chunks = chunk_records(cleaned_records)

    print(f"Total chunks created: {len(chunks)}")

    if not chunks:

        print("No chunks were created.")

        return

    # Step 4: Validation

    print("\n[4] Validating chunks...")

    validate_chunks(chunks)


    print("All chunks passed validation.")

    # Step 5: Export

    print("\n[5] Exporting results...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "chunks.json"

    temporary_file = OUTPUT_DIR / "chunks.tmp"

    with open(temporary_file, "w", encoding="utf-8") as f:

        json.dump(

            chunks,

            f,

            ensure_ascii=False,

            indent=4

        )

    temporary_file.replace(output_file)

    # Final Summary

    print("\n" + "=" * 40)

    print("PIPELINE COMPLETED SUCCESSFULLY")

    print("=" * 40)

    print(f"Files processed: {successful_files}")

    print(f"Files failed: {failed_files}")

    print(f"Original records: {original_count}")

    print(f"Cleaned records: {len(cleaned_records)}")

    print(f"Total chunks: {len(chunks)}")

    print(f"\nOutput saved to: {output_file}")

if __name__ == "__main__":

    main()