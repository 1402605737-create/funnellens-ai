from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Workspace(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="Demo Workspace")

    brands: Mapped[list["Brand"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(120), default="")

    workspace: Mapped[Workspace] = relationship(back_populates="brands")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="brand", cascade="all, delete-orphan")


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"))
    name: Mapped[str] = mapped_column(String(180))
    goal: Mapped[str] = mapped_column(String(80), default="signup")
    target_audience: Mapped[str] = mapped_column(Text, default="")
    primary_kpi: Mapped[str] = mapped_column(String(80), default="CVR")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    diagnosis: Mapped[str] = mapped_column(Text, default="")
    message_match_score: Mapped[float] = mapped_column(Float, default=0)
    cta_friction_score: Mapped[float] = mapped_column(Float, default=0)
    trust_proof_score: Mapped[float] = mapped_column(Float, default=0)
    mobile_readiness_score: Mapped[float] = mapped_column(Float, default=0)
    experiment_priority_score: Mapped[float] = mapped_column(Float, default=0)

    brand: Mapped[Brand] = relationship(back_populates="campaigns")
    ad_assets: Mapped[list["AdAsset"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    landing_pages: Mapped[list["LandingPage"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    metrics: Mapped[list["PerformanceMetric"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    claims: Mapped[list["CreativeClaim"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    mappings: Mapped[list["ClaimPageMapping"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    agent_tasks: Mapped[list["AgentTask"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    ai_runs: Mapped[list["AIAnalysisRun"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    evidence_items: Mapped[list["EvidenceItem"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class AdAsset(TimestampMixin, Base):
    __tablename__ = "ad_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    asset_type: Mapped[str] = mapped_column(String(40), default="copy")
    source_label: Mapped[str] = mapped_column(String(120), default="Manual input")
    content: Mapped[str] = mapped_column(Text, default="")

    campaign: Mapped[Campaign] = relationship(back_populates="ad_assets")


class LandingPage(TimestampMixin, Base):
    __tablename__ = "landing_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    url: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(120), default="Primary landing page")

    campaign: Mapped[Campaign] = relationship(back_populates="landing_pages")
    snapshots: Mapped[list["PageSnapshot"]] = relationship(back_populates="landing_page", cascade="all, delete-orphan")
    sections: Mapped[list["PageSection"]] = relationship(back_populates="landing_page", cascade="all, delete-orphan")


class PageSnapshot(TimestampMixin, Base):
    __tablename__ = "page_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landing_page_id: Mapped[int] = mapped_column(ForeignKey("landing_pages.id"))
    title: Mapped[str] = mapped_column(String(240), default="")
    final_url: Mapped[str] = mapped_column(Text, default="")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    text_excerpt: Mapped[str] = mapped_column(Text, default="")
    raw_html_excerpt: Mapped[str] = mapped_column(Text, default="")
    crawl_error: Mapped[str] = mapped_column(Text, default="")

    landing_page: Mapped[LandingPage] = relationship(back_populates="snapshots")


class PageSection(TimestampMixin, Base):
    __tablename__ = "page_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    landing_page_id: Mapped[int] = mapped_column(ForeignKey("landing_pages.id"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    section_type: Mapped[str] = mapped_column(String(80), default="content")
    heading: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    cta_text: Mapped[str] = mapped_column(Text, default="")

    landing_page: Mapped[LandingPage] = relationship(back_populates="sections")


class CreativeClaim(TimestampMixin, Base):
    __tablename__ = "creative_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    text: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(80), default="benefit")
    confidence: Mapped[float] = mapped_column(Float, default=0.6)
    risk_level: Mapped[str] = mapped_column(String(40), default="medium")

    campaign: Mapped[Campaign] = relationship(back_populates="claims")
    mappings: Mapped[list["ClaimPageMapping"]] = relationship(back_populates="claim", cascade="all, delete-orphan")


class ClaimPageMapping(TimestampMixin, Base):
    __tablename__ = "claim_page_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    claim_id: Mapped[int] = mapped_column(ForeignKey("creative_claims.id"))
    status: Mapped[str] = mapped_column(String(40), default="missing")
    evidence_text: Mapped[str] = mapped_column(Text, default="")
    risk: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    campaign: Mapped[Campaign] = relationship(back_populates="mappings")
    claim: Mapped[CreativeClaim] = relationship(back_populates="mappings")


class PerformanceMetric(TimestampMixin, Base):
    __tablename__ = "performance_metrics"
    __table_args__ = (UniqueConstraint("campaign_id", "date", name="uq_campaign_metric_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    date: Mapped[str] = mapped_column(String(20))
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0)

    campaign: Mapped[Campaign] = relationship(back_populates="metrics")


class AgentTask(TimestampMixin, Base):
    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="running")
    final_summary: Mapped[str] = mapped_column(Text, default="")

    campaign: Mapped[Campaign] = relationship(back_populates="agent_tasks")
    actions: Mapped[list["AgentAction"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class AgentAction(TimestampMixin, Base):
    __tablename__ = "agent_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("agent_tasks.id"))
    step_order: Mapped[int] = mapped_column(Integer)
    tool_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="success")
    input_summary: Mapped[str] = mapped_column(Text, default="")
    output_summary: Mapped[str] = mapped_column(Text, default="")
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)

    task: Mapped[AgentTask] = relationship(back_populates="actions")


class AIAnalysisRun(TimestampMixin, Base):
    __tablename__ = "ai_analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    provider: Mapped[str] = mapped_column(String(80), default="deepseek")
    model: Mapped[str] = mapped_column(String(120), default="")
    prompt_version: Mapped[str] = mapped_column(String(40), default="growth-audit-v1")
    raw_response: Mapped[str] = mapped_column(Text, default="")
    used_fallback: Mapped[bool] = mapped_column(Boolean, default=False)

    campaign: Mapped[Campaign] = relationship(back_populates="ai_runs")


class EvidenceItem(TimestampMixin, Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    source_type: Mapped[str] = mapped_column(String(60), default="landing_page")
    source_url: Mapped[str] = mapped_column(Text, default="")
    quote: Mapped[str] = mapped_column(Text, default="")
    interpretation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.6)

    campaign: Mapped[Campaign] = relationship(back_populates="evidence_items")


class Recommendation(TimestampMixin, Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    confidence: Mapped[float] = mapped_column(Float, default=0.6)

    campaign: Mapped[Campaign] = relationship(back_populates="recommendations")


class Experiment(TimestampMixin, Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    title: Mapped[str] = mapped_column(String(180))
    hypothesis: Mapped[str] = mapped_column(Text)
    change_summary: Mapped[str] = mapped_column(Text)
    success_metric: Mapped[str] = mapped_column(String(120), default="CVR")
    priority: Mapped[str] = mapped_column(String(40), default="medium")
    effort: Mapped[str] = mapped_column(String(40), default="medium")
    confidence: Mapped[float] = mapped_column(Float, default=0.6)
    status: Mapped[str] = mapped_column(String(40), default="proposed")

    campaign: Mapped[Campaign] = relationship(back_populates="experiments")

