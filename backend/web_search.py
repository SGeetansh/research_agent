from ddgs import DDGS
from trafilatura import fetch_url, extract


MAX_CHARS = 8_000


def extract_page(url: str) -> str | None:
    """
    Download a webpage and extract its main readable content.
    """

    html = fetch_url(url)

    if not html:
        return None

    content = extract(
        html,
        url=url,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )

    if not content:
        return None

    return content[:MAX_CHARS]


def search_web(
    query: str,
    k: int = 5,
) -> list[dict]:

    ddgs = DDGS()

    search_results = ddgs.text(
        query=query,
        backend="duckduckgo",
        max_results=k,
    )

    results = []

    for result in search_results:

        title = result.get("title", "")
        url = result.get("href", "")
        snippet = result.get("body", "")
        text = snippet
        content_source = "snippet"

        if url:
            try:
                page_content = extract_page(url)
                if page_content:
                    text = page_content
                    content_source = "webpage"
            except Exception as exc:
                print(
                    f"Failed to extract {url}: {exc}"
                )
        results.append(
            {
                "title": title,
                "url": url,
                "text": text,
                "content_source": content_source,
            }
        )

    return results