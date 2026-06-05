from sqlalchemy.orm import Session

from app.models import AdAsset, Brand, Campaign, LandingPage, PerformanceMetric, Workspace


DEMO_AD_COPY = """10 分钟搭好 AI 应用后端。
专为中文开发者和独立产品团队设计。
7 天免费试用，无需信用卡。
用一套模板把部署成本降低 30%。"""


DEMO_METRICS = [
    {"date": "2026-05-27", "impressions": 18400, "clicks": 680, "conversions": 9, "spend": 742.5, "revenue": 891},
    {"date": "2026-05-28", "impressions": 19250, "clicks": 731, "conversions": 10, "spend": 781.2, "revenue": 990},
    {"date": "2026-05-29", "impressions": 17610, "clicks": 602, "conversions": 7, "spend": 694.8, "revenue": 693},
    {"date": "2026-05-30", "impressions": 20120, "clicks": 774, "conversions": 12, "spend": 823.3, "revenue": 1188},
    {"date": "2026-05-31", "impressions": 21600, "clicks": 833, "conversions": 13, "spend": 862.0, "revenue": 1287},
    {"date": "2026-06-01", "impressions": 23100, "clicks": 884, "conversions": 14, "spend": 902.4, "revenue": 1386},
    {"date": "2026-06-02", "impressions": 22680, "clicks": 861, "conversions": 11, "spend": 881.1, "revenue": 1089},
]


def create_demo_campaign(db: Session) -> Campaign:
    workspace = db.query(Workspace).first()
    if not workspace:
        workspace = Workspace(name="中文增长实验室")
        db.add(workspace)
        db.flush()

    brand = Brand(workspace_id=workspace.id, name="云栈 DevBox", category="中文开发者工具 / AI 应用后端")
    db.add(brand)
    db.flush()

    campaign = Campaign(
        brand_id=brand.id,
        name="中文开发者工具免费试用投放",
        goal="signup",
        target_audience="中文独立开发者、AI 应用创业团队、增长工程师",
        primary_kpi="CVR",
    )
    db.add(campaign)
    db.flush()

    db.add(AdAsset(campaign_id=campaign.id, asset_type="copy", source_label="信息流广告素材", content=DEMO_AD_COPY))
    db.add(
        LandingPage(
            campaign_id=campaign.id,
            label="中文开发者工具落地页",
            url="http://127.0.0.1:8000/demo-landing/chinese-devtool-ad",
        )
    )
    for row in DEMO_METRICS:
        db.add(PerformanceMetric(campaign_id=campaign.id, **row))
    db.commit()
    db.refresh(campaign)
    return campaign
