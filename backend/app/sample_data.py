from html import escape

from sqlalchemy.orm import Session

from app.database import settings
from app.models import AdAsset, Brand, Campaign, LandingPage, PerformanceMetric, RateLimitEvent, Workspace


DEMO_CASES = [
    {
        "key": "ai-coding-assistant",
        "brand": "码伴 Copilot",
        "campaign": "AI 编程助手永久免费投放",
        "category": "AI 编程助手",
        "audience": "中文独立开发者、前端工程师和小型研发团队",
        "ad_copy": "面向中文开发者的 AI 编程助手，核心功能永久免费。安装后立即使用，支持主流 IDE。",
        "landing_title": "码伴 Copilot 专业版",
        "landing_heading": "让 AI 参与你的每一次提交",
        "landing_body": "提供 7 天专业版试用。试用结束后按席位付费，团队版支持代码库上下文和审计日志。",
        "landing_cta": "开始 7 天试用",
    },
    {
        "key": "cloud-database",
        "brand": "云栈 DevBox",
        "campaign": "云数据库快速搭建投放",
        "category": "云数据库 / AI 应用后端",
        "audience": "中文独立开发者、AI 应用创业团队和增长工程师",
        "ad_copy": "10 分钟搭好 AI 应用后端。专为中文开发者设计。7 天免费试用，无需信用卡。部署成本降低 30%。",
        "landing_title": "云栈 DevBox - 中文开发者的 AI 应用后端",
        "landing_heading": "中文开发者的 AI 应用后端工作台",
        "landing_body": "快速搭建认证、数据库、文件存储、任务队列和部署流水线。企业客户可预约产品演示。",
        "landing_cta": "预约产品演示",
    },
    {
        "key": "api-monitoring",
        "brand": "脉冲 API Watch",
        "campaign": "API 监控 99.99% SLA 投放",
        "category": "API 监控平台",
        "audience": "SaaS 技术负责人、后端工程师和运维团队",
        "ad_copy": "为关键 API 提供 99.99% SLA 保障。异常秒级告警，5 分钟接入，免费试用 14 天。",
        "landing_title": "脉冲 API Watch - 实时接口监控",
        "landing_heading": "更早发现接口异常",
        "landing_body": "从全球节点检查接口延迟和可用性，通过企微、钉钉与 Webhook 发送告警。服务等级以合同为准。",
        "landing_cta": "预约接入咨询",
    },
    {
        "key": "privacy-browser-extension",
        "brand": "页净 Browser Guard",
        "campaign": "隐私浏览器插件投放",
        "category": "浏览器插件",
        "audience": "重视隐私的中文互联网用户和开发者",
        "ad_copy": "所有网页内容仅在本地处理，绝不上传。兼容 Chrome、Edge 和 Firefox，一键安装永久免费。",
        "landing_title": "页净 Browser Guard",
        "landing_heading": "更清爽的网页阅读体验",
        "landing_body": "自动隐藏干扰元素并生成阅读摘要。目前提供 Chrome 扩展，其他浏览器版本正在规划中。",
        "landing_cta": "添加到 Chrome",
    },
    {
        "key": "low-code-automation",
        "brand": "流转 FlowCraft",
        "campaign": "低代码自动化效率投放",
        "category": "低代码自动化",
        "audience": "运营团队、增长产品经理和中小企业负责人",
        "ad_copy": "使用 500+ 中文业务模板，让运营效率提升 3 倍。零代码搭建自动化流程，立即免费开始。",
        "landing_title": "流转 FlowCraft - 团队自动化平台",
        "landing_heading": "连接工具，自动推进工作",
        "landing_body": "通过可视化流程连接表单、消息和 CRM。提交企业信息后，顾问将为你配置专属方案。",
        "landing_cta": "填写企业需求",
    },
]


BASE_METRICS = [
    {"date": "2026-05-27", "impressions": 18400, "clicks": 680, "conversions": 9, "spend": 742.5, "revenue": 891},
    {"date": "2026-05-28", "impressions": 19250, "clicks": 731, "conversions": 10, "spend": 781.2, "revenue": 990},
    {"date": "2026-05-29", "impressions": 17610, "clicks": 602, "conversions": 7, "spend": 694.8, "revenue": 693},
    {"date": "2026-05-30", "impressions": 20120, "clicks": 774, "conversions": 12, "spend": 823.3, "revenue": 1188},
    {"date": "2026-05-31", "impressions": 21600, "clicks": 833, "conversions": 13, "spend": 862.0, "revenue": 1287},
    {"date": "2026-06-01", "impressions": 23100, "clicks": 884, "conversions": 14, "spend": 902.4, "revenue": 1386},
    {"date": "2026-06-02", "impressions": 22680, "clicks": 861, "conversions": 11, "spend": 881.1, "revenue": 1089},
]


def get_demo_case(key: str) -> dict | None:
    return next((item for item in DEMO_CASES if item["key"] == key), None)


def render_demo_landing(key: str) -> str | None:
    item = get_demo_case(key)
    if not item:
        return None
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(item["landing_title"])}</title>
  </head>
  <body>
    <main>
      <section>
        <h1>{escape(item["landing_heading"])}</h1>
        <p>{escape(item["landing_body"])}</p>
        <a href="/signup">{escape(item["landing_cta"])}</a>
      </section>
      <section>
        <h2>面向真实上线流程</h2>
        <p>支持中文文档、团队权限、操作日志、Webhook 和生产环境配置。</p>
      </section>
      <section>
        <h2>客户案例</h2>
        <p>已有多个中文开发者团队使用产品缩短交付周期，具体效果因团队而异。</p>
      </section>
    </main>
  </body>
</html>"""


def create_official_demos(db: Session) -> list[Campaign]:
    workspace = db.query(Workspace).filter(Workspace.name == "FunnelLens 官方样例").first()
    if not workspace:
        workspace = Workspace(name="FunnelLens 官方样例")
        db.add(workspace)
        db.flush()

    campaigns: list[Campaign] = []
    base_url = settings.public_api_base.rstrip("/")
    for index, item in enumerate(DEMO_CASES):
        existing = db.query(Campaign).filter(Campaign.demo_key == item["key"]).first()
        if existing:
            campaigns.append(existing)
            continue

        brand = Brand(workspace_id=workspace.id, name=item["brand"], category=item["category"])
        db.add(brand)
        db.flush()
        campaign = Campaign(
            brand_id=brand.id,
            name=item["campaign"],
            goal="signup",
            target_audience=item["audience"],
            primary_kpi="CVR",
            source="official_demo",
            demo_key=item["key"],
        )
        db.add(campaign)
        db.flush()
        db.add(AdAsset(campaign_id=campaign.id, asset_type="copy", source_label="官方中文广告样例", content=item["ad_copy"]))
        db.add(
            LandingPage(
                campaign_id=campaign.id,
                label=f'{item["brand"]} 官方落地页',
                url=f"{base_url}/demo-landing/{item['key']}",
            )
        )
        multiplier = 1 + index * 0.08
        for row in BASE_METRICS:
            metric = row.copy()
            metric["impressions"] = round(metric["impressions"] * multiplier)
            metric["clicks"] = round(metric["clicks"] * multiplier)
            metric["conversions"] = max(1, round(metric["conversions"] * (1 - index * 0.06)))
            metric["spend"] = round(metric["spend"] * multiplier, 2)
            metric["revenue"] = round(metric["revenue"] * (1 + index * 0.03), 2)
            db.add(PerformanceMetric(campaign_id=campaign.id, **metric))
        campaigns.append(campaign)
    db.commit()
    return campaigns


def reset_official_demos(db: Session) -> list[Campaign]:
    for campaign in db.query(Campaign).all():
        db.delete(campaign)
    db.commit()
    db.query(Brand).delete()
    db.query(Workspace).delete()
    db.query(RateLimitEvent).delete()
    db.commit()
    return create_official_demos(db)
