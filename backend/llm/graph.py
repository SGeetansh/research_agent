import asyncio
import os
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    REWRITE_QUERY_SYSTEM_PROMPT,
    build_answer_prompt,
)
from vector_storage import search_chunks
from .client import llm


class ResearchState(TypedDict, total=False):
    request: str
    retrieval_query: str
    results: list[dict]
    answer: str


async def rewrite_query(
    state: ResearchState,
) -> dict:
    """Agent responsible for rewriting the query optimized for vector search"""

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": REWRITE_QUERY_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": state["request"],
            },
        ]
    )

    return {
        "retrieval_query": response.content.strip(),
    }



async def retrieve_documents(
    state: ResearchState
) -> dict:
    """TODO"""
    results = await asyncio.to_thread(
        search_chunks,
        state["retrieval_query"],
        5,
    )

    return {
        "results": results,
    }


def build_context(
    results: list[dict]
) -> str:

    sources = []

    for index, result in enumerate(
        results,
        start=1,
    ):
        metadata = result["metadata"]

        source = metadata.get(
            "source",
            "Unknown source",
        )

        page = metadata.get("page")

        chunk_index = metadata.get(
            "chunk_index"
        )

        text = result["text"]

        sources.append(
            f"""
[S{index}]
Source: {source}
Page: {page}
Chunk: {chunk_index}

{text}
""".strip()
        )

    return "\n\n\n SOURCES: \n\n\n".join(
        sources
    )


async def generate_answer(
    state: ResearchState,
) -> dict:

    results = state["results"]

    if not results:
        return {
            "answer": (
                "I couldn't find relevant information "
                "in the uploaded sources."
            )
        }

    context = build_context(
        results
    )

    user_prompt = build_answer_prompt(
        request=state["request"],
        context=context,
    )

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": ANSWER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
    )

    return {
        "answer": response.content,
    }


builder = StateGraph(
    ResearchState
)


builder.add_node("rewrite_query", rewrite_query)
builder.add_node("retrieve_documents", retrieve_documents)
builder.add_node("generate_answer", generate_answer)

builder.add_edge(START, "rewrite_query")
builder.add_edge("rewrite_query", "retrieve_documents")
builder.add_edge("retrieve_documents", "generate_answer")
builder.add_edge("generate_answer",END)

research_agent = builder.compile()