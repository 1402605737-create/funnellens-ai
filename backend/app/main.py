from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent import run_growth_audit, summarize_metrics
from app.database import get_db, init_db, settings
from app.models import (
    AdAsset,
    Brand,
    Campaign,
    LandingPage,
    PerformanceMetric,
    Workspace,
)
from app.sample_data import create_demo_campaign


app = FastAPI(title="FunnelLens AI API", version="0.1.0")

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
    date: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0
    revenue: float = 0


class CampaignCreate(BaseModel):
    brand_name: str = Field(default="Demo Brand", min_length=1)
    campaign_name: str = Field(default="Conversion Audit", min_length=1)
    product_category: str = ""
    goal: str = "signup"
    target_audience: str = ""
    primary_kpi: str = "CVR"
    landing_page_url: str = ""
    ad_text: str = ""
    metrics: list[MetricInput] = Field(default_factory=list)


class MetricsReplace(BaseModel):
    metrics: list[MetricInput]


class AnalyzeRequest(BaseModel):
    locale: str = "zh-CN"


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, Any]:
    database_kind = "sqlite" if settings.database_url.startswith("sqlite") else "postgres"
    return {
        "status": "ok",
        "model": settings.deepseek_model,
        "database": database_kind,
        "deepseek_configured": bool(settings.deepseek_api_key),
    }


@app.get("/demo-landing/ad-platform", response_class=HTMLResponse)
@app.get("/demo-landing/chinese-devtool-ad", response_class=HTMLResponse)
def demo_ad_platform_landing() -> str:
    return """
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>云栈 DevBox - 中文开发者的 AI 应用后端</title>
      </head>
      <body>
        <main>
          <section>
            <h1>中文开发者的 AI 应用后端工作台</h1>
            <p>云栈 DevBox 帮助独立开发者和小团队快速搭建认证、数据库、文件存储、任务队列和部署流水线。</p>
            <a href="/signup">预约产品演示</a>
          </section>
          <section>
            <h2>从后端模板开始构建 AI 产品</h2>
            <p>内置中文文档、常见 SaaS 模板、API 调试台和团队权限管理，适合从 0 到 1 做 AI 应用。</p>
          </section>
          <section>
            <h2>面向真实上线流程</h2>
            <p>支持生产环境变量、日志查看、Webhook、数据库迁移和灰度发布，方便中文开发者把 demo 推到线上。</p>
          </section>
          <section>
            <h2>开发者团队协作</h2>
            <p>支持项目空间、成员角色、审计日志和工单流转，让技术团队能持续迭代产品。</p>
          </section>
          <section>
            <h2>客户案例</h2>
            <p>多个中文 AI 工具团队使用云栈 DevBox 缩短后端搭建周期，并把更多时间放到核心产品体验上。</p>
            <a href="/signup">开始搭建</a>
          </section>
        </main>
      </body>
    </html>
    """


@app.get("/api/campaigns")
def list_campaigns(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [campaign_summary(campaign) for campaign in campaigns]


@app.post("/api/campaigns")
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
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
    )
    db.add(campaign)
    db.flush()

    db.add(AdAsset(campaign_id=campaign.id, asset_type="copy", source_label="Manual creative input", content=payload.ad_text))
    db.add(LandingPage(campaign_id=campaign.id, label="Primary landing page", url=payload.landing_page_url))
    for row in payload.metrics:
        db.add(PerformanceMetric(campaign_id=campaign.id, **row.model_dump()))

    db.commit()
    db.refresh(campaign)
    return campaign_detail(campaign)


@app.post("/api/demo")
def create_demo(db: Session = Depends(get_db)) -> dict[str, Any]:
    campaign = create_demo_campaign(db)
    return campaign_detail(campaign)


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    campaign = load_campaign(db, campaign_id)
    return campaign_detail(campaign)


@app.post("/api/campaigns/{campaign_id}/analyze")
async def analyze_campaign(
    campaign_id: int,
    payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    campaign = load_campaign(db, campaign_id)
    locale = payload.locale if payload else "zh-CN"
    analyzed = await run_growth_audit(db, campaign, locale=locale)
    return campaign_detail(analyzed)


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
