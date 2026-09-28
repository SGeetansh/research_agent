async def stream_sources(result: dict):
    document_results = result.get("document_results", [])

    if document_results:
        yield "\n\n------\n\n"
        yield "### Document sources\n\n"

        for i, item in enumerate(document_results, start=1):
            metadata = item["metadata"]
            source = metadata.get("source", "Unknown document")
            page = metadata.get("page")

            line = f"- **[D{i}]** {source}"

            if page is not None:
                line += f", page {page}"

            yield line + "\n"

    web_results = result.get("web_results", [])

    if web_results:
        yield "\n### Web sources\n\n"

        for i, item in enumerate(web_results, start=1):
            title = item.get("title", "Untitled")
            url = item.get("url", "")

            yield f"- **[W{i}]** [{title}]({url})\n"