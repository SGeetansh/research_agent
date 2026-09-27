async def stream_research_result(result: dict):

    if result.get("use_web"):
        yield "### Retrieval route\n\n`Uploaded documents + Web`\n\n"
    else:
        yield "### Retrieval route\n\n`Uploaded documents only`\n\n"

    yield f"### Retrieval query\n\n`{result['retrieval_query']}`\n\n---\n\n"
    yield result["answer"]
    yield "\n\n-------------------\n\n"

    document_results = result.get("document_results", [])

    if document_results:
        yield "### Uploaded sources\n\n"

        for i, item in enumerate(document_results, start=1):
            metadata = item["metadata"]

            source = metadata.get("source", "Unknown document")
            page = metadata.get("page")

            yield f"- **[D{i}]** {source}"

            if page is not None:
                yield f", page {page}"

            yield "\n"

        yield "\n"

    web_results = result.get("web_results", [])

    if web_results:
        yield "### Web sources\n\n"

        for i, item in enumerate(web_results, start=1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content_source = item.get("content_source", "unknown")

            yield (
                f"- **[W{i}]** "
                f"[{title}]({url}) "
                f"`{content_source}`\n"
            )