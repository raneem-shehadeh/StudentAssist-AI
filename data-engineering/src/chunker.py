from uuid import uuid4

from transformers import AutoTokenizer


# Replace with the tokenizer corresponding
# to your actual embedding model.

TOKENIZER_NAME = "intfloat/multilingual-e5-small"

tokenizer = AutoTokenizer.from_pretrained(
    TOKENIZER_NAME
)

CHUNK_SIZE = 100
OVERLAP = 15


def count_tokens(text):

    return len(
        tokenizer.encode(
            text,
            add_special_tokens=True
        )
    )


def split_by_tokens(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):

    if chunk_size <= 0:

        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:

        raise ValueError("Invalid overlap")

    token_ids = tokenizer.encode(
        text,
        add_special_tokens=False
    )

    chunks = []

    start = 0

    while start < len(token_ids):

        end = min(
            start + chunk_size,
            len(token_ids)
        )

        chunk_tokens = token_ids[start:end]

        chunk = tokenizer.decode(
            chunk_tokens,
            skip_special_tokens=True
        ).strip()

        if chunk:

            chunks.append(chunk)

        if end >= len(token_ids):

            break

        start = end - overlap

    return chunks


def is_table_line(line):

    return "|" in line or "\t" in line


def split_table(lines, chunk_size=CHUNK_SIZE):

    if not lines:

        return []

    header = lines[0]

    chunks = []

    current_rows = []

    for row in lines[1:]:

        candidate = "\n".join(
            [header] + current_rows + [row]
        )

        if count_tokens(candidate) <= chunk_size:

            current_rows.append(row)

        else:

            if current_rows:

                chunks.append(
                    "\n".join(
                        [header] + current_rows
                    )
                )

            current_rows = [row]

            # Handle a row that exceeds the token limit.

            if count_tokens(
                "\n".join([header, row])
            ) > chunk_size:

                row_chunks = split_by_tokens(
                    row,
                    chunk_size - count_tokens(header) - 5,
                    0
                )

                for part in row_chunks:

                    chunks.append(
                        "\n".join([header, part])
                    )

                current_rows = []

    if current_rows:

        chunks.append(
            "\n".join(
                [header] + current_rows
            )
        )

    return chunks


def split_text(text, chunk_size=CHUNK_SIZE, overlap=OVERLAP):

    if not text.strip():

        return []

    lines = text.splitlines()

    if len(lines) >= 2 and is_table_line(lines[0]):

        return split_table(
            lines,
            chunk_size
        )

    return split_by_tokens(
        text,
        chunk_size,
        overlap
    )


def chunk_records(records, chunk_size=CHUNK_SIZE, overlap=OVERLAP):

    final_chunks = []

    document_indexes = {}

    for record in records:

        text = record.get("text", "")

        source = record.get("source", "unknown")

        if not isinstance(text, str) or not text.strip():

            continue

        text_chunks = split_text(
            text,
            chunk_size,
            overlap
        )

        for chunk in text_chunks:

            chunk_index = document_indexes.get(
                source,
                0
            )

            item = {

                "id": str(uuid4()),

                "text": chunk,

                "source": source,

                "page": record.get("page"),

                "chunk_index": chunk_index

            }

            # Preserve original record ID.

            if record.get("id") is not None:

                item["record_id"] = record["id"]

            # Preserve all additional metadata.

            metadata = record.get("metadata", {})

            if isinstance(metadata, dict):

                item["metadata"] = metadata.copy()

            final_chunks.append(item)

            document_indexes[source] = chunk_index + 1

    return final_chunks