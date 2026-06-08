from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent import run_growth_audit, summarize_metrics
from app.crawler import validate_public_url
from app.database import get_db, init_db, run_migrations, settings
from app.models import (
    AdAsset,
    Brand,
    Campaign,
    LandingPage,
    PerformanceMetric,
    Workspace,
)
from app.sample_data import create_official_demos, render_demo_landing, reset_official_demos
from app.security import enforce_rate_limit, require_admin


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    init_db()
    yield


app = FastAPI(title="FunnelLens AI API", version="0.1.0", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origin.split(",")
    if origin.strip()
]
allowed_origins.extend(["http://localhost:5173", "http://127.0.0.1:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MetricInput(BaseModel):
    date: str = Field(max_length=20)
    impressions: int = Field(default=0, ge=0, le=1_000_000_000)
    clicks: int = Field(default=0, ge=0, le=1_000_000_000)
    conversions: int = Field(default=0, ge=0, le=1_000_000_000)
    spend: float = Field(default=0, ge=0, le=1_000_000_000)
    revenue: float = Field(default=0, ge=0, le=1_000_000_000)


class CampaignCreate(BaseModel):
    brand_name: str = Field(default="Demo Brand", min_length=1, max_length=160)
    campaign_name: str = Field(default="Conversion Audit", min_length=1, max_length=180)
    product_category: str = Field(default="", max_length=120)
    goal: str = Field(default="signup", max_length=80)
    target_audience: str = Field(default="", max_length=1000)
    primary_kpi: str = Field(default="CVR", max_length=80)
    landing_page_url: str = Field(min_length=1, max_length=2048)
    ad_text: str = Field(min_length=1, max_length=8000)
    metrics: list[MetricInput] = Field(default_factory=list, max_length=90)


class MetricsReplace(BaseModel):
    metrics: list[MetricInput] = Field(max_length=90)


class AnalyzeRequest(BaseModel):
    locale: str = "zh-CN"


@app.get("/health")
def health() -> dict[str, Any]:
    database_kind = "sqlite" if settings.database_url.startswith("sqlite") else "postgres"
    return {
        "status": "ok",
        "model": settings.deepseek_model,
        "database": database_kind,
        "deepseek_configured": bool(settings.deepseek_api_key),
    }


@app.get("/demo-landing/{demo_key}", response_class=HTMLResponse)
def demo_landing(demo_key: str) -> str:
    html = render_demo_landing(demo_key)
    if not html:
        raise HTTPException(status_code=404, detail="Demo landing page not found")
    return html


@app.get("/api/campaigns")
def list_campaigns(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    cleanup_public_projects(db)
    official = db.query(Campaign).filter(Campaign.source == "official_demo").order_by(Campaign.demo_key).all()
    public = (
        db.query(Campaign)
        .filter(Campaign.source == "public")
        .order_by(Campaign.created_at.desc())
        .limit(15)
        .all()
    )
    campaigns = official + public
    return [campaign_summary(campaign) for campaign in campaigns]


@app.post("/api/campaigns")
def create_campaign(payload: CampaignCreate, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    enforce_rate_limit(db, request, "create_campaign", hourly_limit=10)
    try:
        landing_page_url = validate_public_url(payload.landing_page_url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    workspace = db.query(Workspace).first()
    if not workspace:
        workspace = Workspace(name="Growth Lab")
        db.add(workspace)
        db.flush()

    brand = Brand(workspace_id=workspace.id, name=payload.brand_name, category=payload.product_category)
    db.add(brand)
    db.flush()

    campaign = Campaign(
        brand_id=brand.id,
        name=payload.campaign_name,
        goal=payload.goal,
        target_audience=payload.target_audience,
        primary_kpi=payload.primary_kpi,
        source="public",
    )
    db.add(campaign)
    db.flush()

    db.add(AdAsset(campaign_id=campaign.id, asset_type="copy", source_label="Manual creative input", content=payload.ad_text))
    db.add(LandingPage(campaign_id=campaign.id, label="Primary landing page", url=landing_page_url))
    for row in payload.metrics:
        db.add(PerformanceMetric(campaign_id=campaign.id, **row.model_dump()))

    db.commit()
    db.refresh(campaign)
    return campaign_detail(campaign)


@app.post("/api/demo")
def create_demo(db: Session = Depends(get_db)) -> dict[str, Any]:
    campaigns = create_official_demos(db)
    return campaign_detail(campaigns[0])


@app.post("/api/admin/reset-demo")
def reset_demo(request: Request, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    require_admin(request)
    campaigns = reset_official_demos(db)
    return [campaign_summary(campaign) for campaign in campaigns]


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    campaign = load_campaign(db, campaign_id)
    return campaign_detail(campaign)


@app.post("/api/campaigns/{campaign_id}/analyze")
async def analyze_campaign(
    campaign_id: int,
    request: Request,
    payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    campaign = load_campaign(db, campaign_id)
    enforce_rate_limit(db, request, "analyze_campaign", hourly_limit=3, daily_limit=10)
    now = datetime.now(UTC).replace(tzinfo=None)
    if campaign.analysis_started_at and campaign.analysis_started_at >= now - timedelta(minutes=5):
        raise HTTPException(status_code=409, detail="该项目正在诊断中，请稍后刷新查看结果。")
    campaign.analysis_started_at = now
    campaign.status = "running"
    db.commit()
    locale = payload.locale if payload else "zh-CN"
    try:
        analyzed = await run_growth_audit(db, campaign, locale=locale)
        analyzed.analysis_started_at = None
        db.commit()
        return campaign_detail(analyzed)
    except Exception:
        db.rollback()
        campaign = load_campaign(db, campaign_id)
        campaign.analysis_started_at = None
        campaign.status = "draft"
        db.commit()
        raise


@app.put("/api/campaigns/{campaign_id}/metrics")
def replace_metrics(campaign_id: int, payload: MetricsReplace, db: Session = Depends(get_db)) -> dict[str, Any]:
    campaign = load_campaign(db, campaign_id)
    db.query(PerformanceMetric).filter(PerformanceMetric.campaign_id == campaign.id).delete()
    for row in payload.metrics:
        db.add(PerformanceMetric(campaign_id=campaign.id, **row.model_dump()))
    db.commit()
    db.refresh(campaign)
    return campaign_detail(campaign)


def load_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def campaign_summary(campaign: Campaign) -> dict[str, Any]:
    summary = summarize_metrics(campaign)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "brand": campaign.brand.name,
        "category": campaign.brand.category,
        "goal": campaign.goal,
        "source": campaign.source,
        "demo_key": campaign.demo_key,
        "status": campaign.status,
        "created_at": campaign.created_at.isoformat(),
        "scores": score_payload(campaign),
        "metrics_summary": summary,
    }


def campaign_detail(campaign: Campaign) -> dict[str, Any]:
    return {
        **campaign_summary(campaign),
        "target_audience": campaign.target_audience,
        "primary_kpi": campaign.primary_kpi,
        "diagnosis": campaign.diagnosis,
        "ad_assets": [
            {
                "id": asset.id,
                "asset_type": asset.asset_type,
                "source_label": asset.source_label,
                "content": asset.content,
            }
            for asset in sorted(campaign.ad_assets, key=lambda item: item.id)
        ],
        "landing_pages": [
            {
                "id": page.id,
                "label": page.label,
                "url": page.url,
                "snapshots": [
                    {
                        "id": snapshot.id,
                        "title": snapshot.title,
                        "final_url": snapshot.final_url,
                        "status_code": snapshot.status_code,
                        "text_excerpt": snapshot.text_excerpt,
                        "crawl_error": snapshot.crawl_error,
                        "created_at": snapshot.created_at.isoformat(),
                    }
                    for snapshot in sorted(page.snapshots, key=lambda item: item.id, reverse=True)
                ],
                "sections": [
                    {
                        "id": section.id,
                        "position": section.position,
                        "section_type": section.section_type,
                        "heading": section.heading,
                        "body": section.body,
                        "cta_text": section.cta_text,
                    }
                    for section in sorted(page.sections, key=lambda item: item.position)
                ],
            }
            for page in sorted(campaign.landing_pages, key=lambda item: item.id)
        ],
        "metrics": [
            {
                "id": metric.id,
                "date": metric.date,
                "impressions": metric.impressions,
                "clicks": metric.clicks,
                "conversions": metric.conversions,
                "spend": metric.spend,
                "revenue": metric.revenue,
            }
            for metric in sorted(campaign.metrics, key=lambda item: item.date)
        ],
        "claims": [
            {
                "id": claim.id,
                "text": claim.text,
                "claim_type": claim.claim_type,
                "confidence": claim.confidence,
                "risk_level": claim.risk_level,
                "mappings": [
                    {
                        "id": mapping.id,
                        "status": mapping.status,
                        "evidence_text": mapping.evidence_text,
                        "risk": mapping.risk,
                        "reasoning": mapping.reasoning,
                        "confidence": mapping.confidence,
                    }
                    for mapping in sorted(claim.mappings, key=lambda item: item.id)
                ],
            }
            for claim in sorted(campaign.claims, key=lambda item: item.id)
        ],
        "agent_tasks": [
            {
                "id": task.id,
                "objective": task.objective,
                "status": task.status,
                "final_summary": task.final_summary,
                "created_at": task.created_at.isoformat(),
                "actions": [
                    {
                        "id": action.id,
                        "step_order": action.step_order,
                        "tool_name": action.tool_name,
                        "status": action.status,
                        "input_summary": action.input_summary,
                        "output_summary": action.output_summary,
                        "requires_human_review": action.requires_human_review,
                    }
                    for action in sorted(task.actions, key=lambda item: item.step_order)
                ],
            }
            for task in sorted(campaign.agent_tasks, key=lambda item: item.id, reverse=True)
        ],
        "evidence_items": [
            {
                "id": item.id,
                "source_type": item.source_type,
                "source_url": item.source_url,
                "quote": item.quote,
                "interpretation": item.interpretation,
                "confidence": item.confidence,
            }
            for item in sorted(campaign.evidence_items, key=lambda item: item.id, reverse=True)
        ],
        "recommendations": [
            {
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "priority": item.priority,
                "confidence": item.confidence,
            }
            for item in sorted(campaign.recommendations, key=lambda item: item.id)
        ],
        "experiments": [
            {
                "id": item.id,
                "title": item.title,
                "hypothesis": item.hypothesis,
                "change_summary": item.change_summary,
                "success_metric": item.success_metric,
                "priority": item.priority,
                "effort": item.effort,
                "confidence": item.confidence,
                "status": item.status,
            }
            for item in sorted(campaign.experiments, key=lambda item: item.id)
        ],
        "ai_runs": [
            {
                "id": run.id,
                "provider": run.provider,
                "model": run.model,
                "prompt_version": run.prompt_version,
                "used_fallback": run.used_fallback,
                "created_at": run.created_at.isoformat(),
            }
            for run in sorted(campaign.ai_runs, key=lambda item: item.id, reverse=True)
        ],
    }


def score_payload(campaign: Campaign) -> dict[str, float]:
    return {
        "message_match": campaign.message_match_score,
        "cta_friction": campaign.cta_friction_score,
        "trust_proof": campaign.trust_proof_score,
        "mobile_readiness": campaign.mobile_readiness_score,
        "experiment_priority": campaign.experiment_priority_score,
    }


def cleanup_public_projects(db: Session) -> None:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=settings.public_project_ttl_hours)
    expired = db.query(Campaign).filter(Campaign.source == "public", Campaign.created_at < cutoff).all()
    for campaign in expired:
        db.delete(campaign)
    if expired:
        db.commit()
