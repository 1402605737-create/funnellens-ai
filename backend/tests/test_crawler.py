import socket

import pytest

from app.crawler import validate_public_url
from app.sample_data import DEMO_CASES, render_demo_landing


def test_official_demo_cases_are_unique() -> None:
    keys = [item["key"] for item in DEMO_CASES]
    names = [item["campaign"] for item in DEMO_CASES]
    assert len(keys) == len(set(keys)) == 5
    assert len(names) == len(set(names)) == 5
    assert all(render_demo_landing(key) for key in keys)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/private",
        "http://localhost/private",
        "ftp://public.example/file",
    ],
)
def test_private_or_unsupported_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        validate_public_url(url)


def test_public_url_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    assert validate_public_url("https://public.example/page") == "https://public.example/page"
