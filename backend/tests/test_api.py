from datetime import UTC, datetime

from fastapi.testclient import TestClient

import app.main as main
from app.database import SessionLocal
from app.models import Campaign, RateLimitEvent


def test_official_demo_endpoint_is_idempotent() -> None:
    with TestClient(main.app) as client:
        first = client.post("/api/demo")
        second = client.post("/api/demo")
        rows = client.get("/api/campaigns").json()

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert len(rows) == 5
    assert len({row["name"] for row in rows}) == 5
    assert all(row["source"] == "official_demo" for row in rows)


def test_private_landing_url_is_rejected() -> None:
    with TestClient(main.app) as client:
        response = client.post(
            "/api/campaigns",
            json={
                "brand_name": "测试品牌",
                "campaign_name": "测试项目",
                "landing_page_url": "http://127.0.0.1/private",
                "ad_text": "测试广告",
            },
        )
    assert response.status_code == 422


def test_create_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr(main, "validate_public_url", lambda url: url)
    with SessionLocal() as db:
        db.query(RateLimitEvent).delete()
        db.commit()

    statuses = []
    with TestClient(main.app) as client:
        for index in range(11):
            response = client.post(
                "/api/campaigns",
                json={
                    "brand_name": "公开品牌",
                    "campaign_name": f"公开项目 {index}",
                    "landing_page_url": "https://public.example",
                    "ad_text": "公开广告",
                },
            )
            statuses.append(response.status_code)

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


def test_concurrent_analysis_returns_conflict() -> None:
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.source == "official_demo").first()
        campaign.source = "public"
        campaign.analysis_started_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        campaign_id = campaign.id
        db.query(RateLimitEvent).delete()
        db.commit()

    with TestClient(main.app) as client:
        response = client.post(f"/api/campaigns/{campaign_id}/analyze", json={"locale": "zh-CN"})

    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign.source = "official_demo"
        campaign.analysis_started_at = None
        db.commit()

    assert response.status_code == 409


def test_official_analysis_is_read_only() -> None:
    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.source == "official_demo").first()
        campaign.status = "analyzed"
        db.commit()
        campaign_id = campaign.id
        run_count = len(campaign.ai_runs)

    with TestClient(main.app) as client:
        response = client.post(f"/api/campaigns/{campaign_id}/analyze", json={"locale": "en-US"})

    with SessionLocal() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        assert len(campaign.ai_runs) == run_count

    assert response.status_code == 200


def test_public_cannot_replace_metrics() -> None:
    with SessionLocal() as db:
        campaign = db.query(Campaign).first()
        campaign_id = campaign.id

    with TestClient(main.app) as client:
        response = client.put(f"/api/campaigns/{campaign_id}/metrics", json={"metrics": []})

    assert response.status_code == 403
