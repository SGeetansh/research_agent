import asyncio

import uvicorn

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from parsers import parse_pdf
from vector_storage import search_chunks, clear_store, store_chunks
from llm.graph import research_agent
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins="http://localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


stored_chunks: list[dict] = []


class ResearchRequest(BaseModel):
    request: str


@app.post("/api/sources")
async def upload_sources(
    files: list[UploadFile] = File(...),
):
    global stored_chunks

    stored_chunks = []

    uploaded = []

    await asyncio.to_thread(clear_store)

    for file in files:
        if not file.filename:
            continue

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"{file.filename} is not a PDF.",
            )
        
        file_name = file.filename
        file_bytes = await file.read()
        chunks = await asyncio.to_thread(
            parse_pdf,
            file_bytes,
            file.filename,
        )
        await asyncio.to_thread(
            store_chunks,
            chunks,
            file_name,
        )


        # stored_chunks.extend(chunks)

        uploaded.append(
            {
                "name": file.filename,
                "chunks": len(chunks),
            }
        )

    return {
        "uploaded": uploaded,
    }


# @app.post("/api/research")
# async def research(
#     payload: ResearchRequest,
# ):
#     results = await asyncio.to_thread(
#         search_chunks,
#         payload.request,
#         10,
#     )
#     async def generate():
#         # yield f"____________CHUNKS______________"
#         # yield f"Total chunks: {len(stored_chunks)}"

#         # yield f"Input text: {payload.request}\n"

#         # if not stored_chunks:
#         #     yield "Chunk storage is empty.\n"
#         #     return

#         # for chunk in stored_chunks:
#         #     metadata = chunk["metadata"]

#         #     yield f"Chunk index: {metadata['chunk_index']}"
#         #     yield f"Source: {metadata['source']}\n"
#         #     yield f"Page: {metadata['page']}\n"
#         #     yield f"Token count: {metadata['token_count']}\n"
#         #     yield f"Characters: {metadata['start_index']} -> {metadata['end_index']}"

#         #     yield "-----Markdown: \n"
#         #     yield chunk["text"]
#         #     yield "\n\n"

#         yield f"Query: {payload.request}\n" 
#         yield f"results: {len(results)}"

#         for rank, result in enumerate(results, start=1):
#             metadata = result["metadata"]
#             yield f'RANK: {rank}'
#             yield f'DISTANCE: {result['distance']}'
#             yield f'SOURCE DOC: {metadata['source']}'
#             yield f'PAGE: {metadata['page']}'
#             yield f'RESULT TEXT: {result['text']}'

#     return StreamingResponse(
#         generate(),
#         media_type="text/markdown",
#     )


@app.post("/api/research")
async def research(
    payload: ResearchRequest,
):

    result = await research_agent.ainvoke(
        {
            "request": payload.request,
        }
    )

    async def generate():

        yield "Query by LLM for vector search\n"
        yield f"{result['retrieval_query']}\n"
        yield f'result["answer"]\n\n\n'

        yield "Sources\n"

        for index, result_item in enumerate(result["results"], start=1):
            metadata = result_item["metadata"]
            source = metadata.get(
                "source",
                "unknown",
            )
            page = metadata.get("page")
            yield (
                f"- [Source {index}] - "
                f"{source}"
            )
            if page is not None:
                yield f", page {page}"
            yield "\n\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/markdown",
    )

@app.get("/health")
def health():
    return {"status": "ok"}


def main() -> None:
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8787,
    )


if __name__ == "__main__":
    main()
