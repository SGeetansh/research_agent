from typing import cast

import pymupdf
import pymupdf4llm
import tiktoken

from chonkie import RecursiveChunker
from chonkie.tokenizer import TokenizerProtocol

CHUNK_SIZE = 200

encoding = tiktoken.get_encoding("cl100k_base")

chunker = RecursiveChunker.from_recipe(
    name="markdown",
    lang="en",
    tokenizer=cast(
        TokenizerProtocol,
        encoding,
    ),
    chunk_size=CHUNK_SIZE,
)


def parse_pdf(
    file: bytes,
    file_name: str,
) -> list[dict]:

    with pymupdf.open(
        stream=file,
        filetype="pdf",
    ) as document:
        pages = pymupdf4llm.to_markdown(
            document,
            page_chunks=True,
            force_ocr=False,
        )

    chunks = []

    for page_number, page in enumerate(
        pages,
        start=1,
    ):
        page_chunks = chunker(page["text"])

        for chunk in page_chunks:
            text = chunk.text.strip()

            if not text:
                continue

            chunk_index = len(chunks)

            chunks.append(
                {
                    "text": text,
                    "metadata": {
                        "source": file_name,
                        "page": page_number,
                        "chunk_index": chunk_index,
                        "chunk_id": (f"{file_name}:chunk:{chunk_index}"),
                        "token_count": chunk.token_count,
                        "start_index": chunk.start_index,
                        "end_index": chunk.end_index,
                    },
                }
            )

    return chunks
