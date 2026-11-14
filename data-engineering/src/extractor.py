from pathlib import Path

import json

import pymupdf

def extract_pdf(file):

    extracted_data = []

    with pymupdf.open(file) as pdf:

        for page_number, page in enumerate(pdf, start=1):

            text = page.get_text("text", sort=True)

            extracted_data.append({

                "text": text,

                "source": file.name,

                "page": page_number

            })

    return extracted_data

def extract_txt(file):

    with open(file, "r", encoding="utf-8-sig") as f:

        text = f.read()

    return [{

        "text": text,

        "source": file.name,

        "page": None

    }]

def extract_json(file):

    with open(file, "r", encoding="utf-8-sig") as f:

        data = json.load(f)

    extracted_data = []

    records = data if isinstance(data, list) else [data]

    for index, record in enumerate(records):

        text = json.dumps(

            record,

            ensure_ascii=False,

            indent=2

        )

        item = {

            "text": text,

            "source": file.name,

            "page": None

        }

        if isinstance(record, dict):

            url = record.get("url") or record.get("source_url")

            record_id = record.get("record_id") or record.get("id")

            if url is not None:

                item["url"] = url

            if record_id is not None:

                item["record_id"] = record_id

        extracted_data.append(item)

    return extracted_data

def extract_jsonl(file):

    extracted_data = []

    with open(file, "r", encoding="utf-8-sig") as f:

        for line_number, line in enumerate(f, start=1):

            if not line.strip():
                continue

            try:
                record = json.loads(line)

            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {file.name}: {error}"
                )

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number} in {file.name}"
                )

            metadata = record.get("metadata", {})

            if not isinstance(metadata, dict):
                metadata = {}

            item = {
                "text": record.get("text", ""),
                "source": (
                    metadata.get("source_url")
                    or record.get("source")
                    or file.name
                ),
                "page": record.get("page")
            }

            record_id = record.get("record_id") or record.get("id")

            if record_id is not None:
                item["record_id"] = record_id

            url = (
                metadata.get("source_url")
                or record.get("url")
                or record.get("source_url")
            )

            if url is not None:
                item["url"] = url

            item["metadata"] = metadata

            extracted_data.append(item)

    return extracted_data

def extract_document(file):

    file = Path(file)

    extension = file.suffix.lower()

    if extension == ".pdf":

        return extract_pdf(file)

    elif extension == ".txt":

        return extract_txt(file)

    elif extension == ".json":

        return extract_json(file)

    elif extension == ".jsonl":

        return extract_jsonl(file)

    else:

        raise ValueError(

            f"Unsupported file type: {extension}"

        )