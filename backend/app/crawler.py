import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

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


def validate_public_url(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("落地页只支持 HTTP 或 HTTPS 地址。")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("落地页 URL 格式无效。")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        raise ValueError("为保护公开 Demo，不能抓取本机或内网地址。")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))}
    except socket.gaierror as exc:
        raise ValueError("无法解析落地页域名。") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("为保护公开 Demo，不能抓取本机、内网或保留地址。")
    return normalized


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def truncate(text: str, limit: int) -> str:
    text = clean_text(text)
    return text[:limit]


async def fetch_landing_page(url: str) -> dict:
    try:
        normalized_url = validate_public_url(url)
    except ValueError as exc:
        return {
            "url": normalize_url(url),
            "final_url": normalize_url(url),
            "status_code": 0,
            "title": "",
            "text": "",
            "html_excerpt": "",
            "sections": [],
            "error": str(exc),
        }

    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=18,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
        ) as client:
            current_url = normalized_url
            for _ in range(6):
                response = await client.get(current_url)
                if response.is_redirect:
                    target = response.headers.get("location")
                    if not target:
                        break
                    current_url = validate_public_url(urljoin(current_url, target))
                    continue
                break
            else:
                raise ValueError("落地页跳转次数过多。")
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
