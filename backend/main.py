from fastapi import FastAPI, status, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from parsers import parse_pdf
import asyncio
from fastapi.responses import StreamingResponse

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="http://localhost:5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    request: str

storage = []

@app.post("/api/sources")
async def sources(files: list[UploadFile] = File(...)):
    """
    Check uploaded files for filetype == pdf

    Parse the pdf to markdown
    parse markdown -> seperate headings subheadings text tables etc
    put them into docs which are semantically aware where they belong + pagenumber
    chunking and getting documents for feeding into embedding and then to vector store
    
    """
    global storage

    uploaded_docs = []

    uploaded_docs.clear()
    storage.clear()

    for file in files:
        filename = file.filename or "unknown.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Please upload only PDF files"
        )

        content = await file.read()

        parsed_pdf = await asyncio.to_thread(parse_pdf, content, filename)

        storage.extend(parsed_pdf)

        uploaded_docs.append(
            {
                "name": filename,
                "pages": len(storage),
            }
        )

    return {"uploaded": uploaded_docs}


@app.post("/api/research")
async def research(payload: ResearchRequest):
    """
    Stream output for now. We just need to check. All the chunking and document conversion is happenign in the sources endpoint

    """
    

    def data_generator():
        yield '++++++.  Structured blocks.  ++++++++++\n\n\n'
        yield f'Request: {payload.request}'
        for block in storage:
            section = (
                " > ".join(block["section_path"])
                if block["section_path"] else "NONE"
            )

            yield f'Page: {block["page"]}'
            yield f'Block: {block['block_index']}\n\n'

            yield f'Section: {section}\n\n'
            yield f'Type: {block["block_type"]}\n\n'

    return StreamingResponse(data_generator(), media_type="text/markdown")
 

def main() -> None:
    """Entrypoint to invoke when this module is invoked on the remote server."""
    uvicorn.run("main:app", host="0.0.0.0")

if __name__ == "__main__":
    main()

