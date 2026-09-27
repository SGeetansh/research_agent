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
from format_response import stream_research_result
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
#     result = await research_agent.ainvoke(
#         {
#             "request": payload.request,
#         }
#     )

#     return StreamingResponse(
#         stream_research_result(result),
#         media_type="text/markdown",
#     )

@app.post("/api/research")
async def research(payload: ResearchRequest):

    async def generate():
        async for message, metadata in research_agent.astream(
            {
                "request": payload.request,
            },
            stream_mode="messages",
        ):
            if metadata.get("langgraph_node") != "generate_answer":
                continue

            if message.content:
                yield message.content

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
