import pymupdf4llm
import pymupdf
from typing import Any
import uuid
from markdown_it import MarkdownIt
from markdown_it.token import Token

md = MarkdownIt("commonmark")

def get_source_from_token(token: Token, lines: list[str]):
    """Get the source lines of this token"""
    if token.map is None:
        return ""

    start_line, end_line = token.map

    return "\n".join(lines[start_line:end_line]).strip()


def update_heading_path(
        heading_state,
        level,
        heading,
) -> None:
    for existing_level in list(heading_state):
        if existing_level >= level:
            del heading_state[existing_level]

    heading_state[level] = heading

def get_section_path(heading_state):
    return tuple(
        heading_state[level] for level in sorted(heading_state)
    )

def markdown_to_blocks(markdown: str, page_number: int, file_name: str, heading_state: dict,):
    lines = markdown.splitlines()
    tokens = md.parse(markdown)
    headings = dict(heading_state)
    block_index = 0
    blocks = []

    i = 0

    while i<len(tokens):
        print(i)
        print("__________________")
        token = tokens[i]
        # if token.level != 0:
        #     continue

        # block_type = None
        token_type = token.type

        if (token_type == "heading_open" and token.level == 0):
            level = int(token.tag[1:])
            print("LEVEL AILA LEVEL")
            print(level)

            if i+1<len(tokens):
                inline = tokens[i+1]
                if inline.type == "inline":
                    update_heading_path(
                        heading_state=headings,
                        level=level,
                        heading=inline.content.strip(),
                    )
            i += 1
            continue

        if token.level != 0:
            i+=1
            continue

        block_type = None

        if token_type == "paragraph_open":
            block_type = "paragraph"

        elif token_type in ["bullet_list_open", "ordered_list_open"]:
            block_type = "list"

        elif token_type in ["fence", "code_block"]:
            block_type = "code"

        elif token_type == "blockquote_open":
            block_type = "blockquote"

        if block_type is not None:
            text = get_source_from_token(token, lines)
            if text:
                block_index+=1

                blocks.append(
                    {
                        "source": file_name,
                        "page": page_number,
                        "block_type": block_type,
                        "block_index": block_index,
                        "section_path": get_section_path(heading_state=headings),
                        "text": text,
                    }
                )

        i += 1

    return blocks, headings


def parse_pdf(file: bytes, file_name: str):
    """
    Convert PDFs to documents. Each document is a page from the PDF.
    """
    all_blocks = []
    doc = pymupdf.Document(stream=file)
    pages = pymupdf4llm.to_markdown(doc, page_chunks = True)

    heading_state: dict[int, str] = {}
    for page_number, page in enumerate(
        pages, start=1,
    ):
        blocks, heading_state = (
            markdown_to_blocks(
                markdown=page["text"],
                page_number=page_number,
                file_name=file_name,
                heading_state=heading_state,         
            )
        )
        all_blocks.extend(blocks)

    return all_blocks

