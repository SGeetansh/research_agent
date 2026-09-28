import asyncio
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    REWRITE_QUERY_SYSTEM_PROMPT,
    WEB_ROUTER_SYSTEM_PROMPT,
    build_answer_prompt,
)
from vector_storage import search_chunks
from .client import llm
from web_search import search_web
from logger import get_logger

logger = get_logger(__name__)

class ResearchState(TypedDict, total=False):
    request: str
    retrieval_query: str
    document_results: list[dict]
    web_results: list[dict]
    use_web: bool
    route_reason: str
    answer: str


async def rewrite_query(
    state: ResearchState,
) -> dict:
    """Agent responsible for rewriting the query optimized for vector search"""
    logger.info(
        "Rewriting query for retrieval"
    )
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
    logger.info(
        "Retrieval query generated"
    )

    return {
        "retrieval_query": response.content.strip(),
    }



async def retrieve_documents(
    state: ResearchState
) -> dict:
    """TODO"""
    logger.info(
        "Searching uploaded documents"
    )
    results = await asyncio.to_thread(
        search_chunks,
        state["retrieval_query"],
        5,
    )
    logger.info(
        "Retrieved %d document chunks",
        len(results),
    )

    return {
        "document_results": results,
    }


async def decide_web_search(
    state: ResearchState,
) -> dict:
    logger.info(
        "Deciding whether web search is required"
    )
    document_results = state.get(
        "document_results",
        [],
    )

    document_preview = "\n\n".join(
        result["text"][:500]
        for result in document_results[:3]
    )

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": WEB_ROUTER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"""
User request:
{state["request"]}

Retrieved document evidence:
{document_preview or "No relevant uploaded documents were found."}
""".strip(),
            },
        ]
    )

    decision = response.content.strip().upper()
    use_web = decision == "WEB"
    
    logger.info(
        "Router decision: %s",
        "web search required"
        if use_web
        else "documents sufficient",
    )

    return {
        "use_web": use_web,
        "route_reason": decision,
    }


def route_after_orchestrator(
    state: ResearchState,
) -> str:

    if state.get("use_web", False):
        return "web"

    return "answer"


async def retrieve_web(
    state: ResearchState,
) -> dict:
    """
    TODO
    """
    logger.info(
        "Retrieving external web sources"
    )
    results = await asyncio.to_thread(
        search_web,
        state["retrieval_query"],
        5,
    )
    logger.info(
        "Retrieved %d web sources",
        len(results),
    )
    return {
        "web_results": results,
    }


def build_context(
    document_results: list[dict],
    web_results: list[dict],
) -> str:
    """
    Uploaded documents: [Di]
    Internet sources: [Wi]
    """

    sources = []

    for index, result in enumerate(
        document_results,
        start=1,
    ):
        metadata = result["metadata"]

        source = metadata.get(
            "source",
            "Unknown document",
        )

        page = metadata.get(
            "page",
        )

        text = result["text"]

        sources.append(
            f"""
[D{index}]
Type: Uploaded document
Source: {source}
Page: {page}

{text}
""".strip()
        )

    for index, result in enumerate(
        web_results,
        start=1,
    ):
        sources.append(
    f"""
        [W{index}]
        Type: Web source
        Title: {result["title"]}
        URL: {result["url"]}
        Content source: {result.get("content_source", "unknown")}

        {result["text"]}
        """.strip()
        )

    return "\n\n------\n\n".join(
        sources
    )

async def generate_answer(
    state: ResearchState,
) -> dict:
    logger.info(
        "Generating grounded answer"
    )

    document_results = state.get(
        "document_results",
        [],
    )

    web_results = state.get(
        "web_results",
        [],
    )

    if (
        not document_results
        and not web_results
    ):
        return {
            "answer": (
                "Couldn't find relevant information "
                "in the uploaded documents or on the web."
            )
        }

    context = build_context(
        document_results=document_results,
        web_results=web_results,
    )

    response = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": ANSWER_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_answer_prompt(
                    request=state["request"],
                    context=context,
                ),
            },
        ]
    )
    logger.info(
        "Answer generation complete"
    )

    return {
        "answer": response.content,
    }


builder = StateGraph(ResearchState)
builder.add_node("rewrite_query", rewrite_query)
builder.add_node("retrieve_documents", retrieve_documents)
builder.add_node("decide_web_search", decide_web_search)
builder.add_node("retrieve_web", retrieve_web)
builder.add_node("generate_answer", generate_answer)


builder.add_edge(START, "rewrite_query")
builder.add_edge("rewrite_query", "retrieve_documents")
builder.add_edge("retrieve_documents", "decide_web_search")

builder.add_conditional_edges(
    "decide_web_search",
    route_after_orchestrator,
    {
        "web": "retrieve_web",
        "answer": "generate_answer",
    },
)

builder.add_edge("retrieve_web", "generate_answer")
builder.add_edge("generate_answer",END)

research_agent = builder.compile()