import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


def normalize_url(url: str) -> str:
    cleaned = (url or "").strip()
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if not parsed.scheme:
        cleaned = f"https://{cleaned}"
    return cleaned


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    return text[:limit]


async def fetch_landing_page(url: str) -> dict:
    normalized_url = normalize_url(url)
    if not normalized_url:
        return {
            "url": "",
            "final_url": "",
            "status_code": 0,
            "title": "",
            "text": "",
            "html_excerpt": "",
            "sections": [],
            "error": "Landing page URL is empty.",
        }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=18,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(normalized_url)
    except Exception as exc:
        return {
            "url": normalized_url,
            "final_url": normalized_url,
            "status_code": 0,
            "title": "",
            "text": "",
            "html_excerpt": "",
            "sections": [],
            "error": str(exc),
        }

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(soup.title.string if soup.title and soup.title.string else "")
    page_text = truncate(soup.get_text(" "), 14000)
    headings = [clean_text(node.get_text(" ")) for node in soup.find_all(["h1", "h2", "h3"]) if clean_text(node.get_text(" "))]
    ctas = [
        clean_text(node.get_text(" "))
        for node in soup.find_all(["button", "a"])
        if clean_text(node.get_text(" ")) and len(clean_text(node.get_text(" "))) <= 80
    ]

    paragraphs = [clean_text(node.get_text(" ")) for node in soup.find_all("p") if clean_text(node.get_text(" "))]
    sections = []
    hero_heading = headings[0] if headings else title
    hero_body = " ".join(paragraphs[:3]) if paragraphs else page_text[:700]
    sections.append(
        {
            "position": 1,
            "section_type": "hero",
            "heading": truncate(hero_heading, 220),
            "body": truncate(hero_body, 900),
            "cta_text": truncate(" | ".join(ctas[:4]), 260),
        }
    )

    for index, heading in enumerate(headings[1:8], start=2):
        sections.append(
            {
                "position": index,
                "section_type": "content",
                "heading": truncate(heading, 220),
                "body": "",
                "cta_text": "",
            }
        )

    return {
        "url": normalized_url,
        "final_url": str(response.url),
        "status_code": response.status_code,
        "title": title,
        "text": page_text,
        "html_excerpt": response.text[:5000],
        "sections": sections,
        "error": "",
    }

