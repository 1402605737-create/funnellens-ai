import json
import math
import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.ai_client import DeepSeekClient
from app.crawler import fetch_landing_page
from app.database import settings
from app.models import (
    AIAnalysisRun,
    AgentAction,
    AgentTask,
    Campaign,
    ClaimPageMapping,
    CreativeClaim,
    EvidenceItem,
    Experiment,
    PageSection,
    PageSnapshot,
    Recommendation,
)


SYSTEM_PROMPT = """You are FunnelLens AI, a vertical growth audit agent.
You diagnose conversion gaps between ad creatives, landing pages, and performance data.
Return only valid JSON. Do not include markdown."""


def is_chinese_locale(locale: str | None) -> bool:
    return (locale or "zh-CN").lower().startswith("zh")


def add_action(
    db: Session,
    task: AgentTask,
    step_order: int,
    tool_name: str,
    input_summary: str,
    output_summary: str,
    status: str = "success",
    requires_human_review: bool = False,
) -> AgentAction:
    action = AgentAction(
        task_id=task.id,
        step_order=step_order,
        tool_name=tool_name,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
        requires_human_review=requires_human_review,
    )
    db.add(action)
    db.flush()
    return action


async def run_growth_audit(db: Session, campaign: Campaign, locale: str = "zh-CN") -> Campaign:
    zh = is_chinese_locale(locale)
    clear_previous_analysis(db, campaign)
    campaign.status = "running"
    db.flush()

    objective = (
        "诊断这条中文广告到落地页的转化链路，找出承诺不一致、转化阻力和可执行实验。"
        if zh
        else "Diagnose why this ad-to-landing-page funnel may have weak conversion and produce experiments."
    )
    task = AgentTask(campaign_id=campaign.id, objective=objective, status="running")
    db.add(task)
    db.flush()

    ad_text = campaign.ad_assets[0].content if campaign.ad_assets else ""
    landing_page = campaign.landing_pages[0] if campaign.landing_pages else None
    landing_url = landing_page.url if landing_page else ""
    metrics_summary = summarize_metrics(campaign)

    add_action(
        db,
        task,
        1,
        "任务规划器" if zh else "Task Planner",
        "广告目标、广告文案、落地页 URL、投放指标" if zh else "Campaign objective, ad text, landing page URL, and metrics",
        (
            "已规划工具链：素材承诺抽取、落地页抓取、指标汇总、承诺匹配、证据记录、实验生成。"
            if zh
            else "Planned tools: creative extraction, landing-page crawl, metrics summary, claim matching, evidence logging, experiment generation."
        ),
    )

    page_data = await fetch_landing_page(landing_url)
    add_action(
        db,
        task,
        2,
        "落地页抓取器" if zh else "Landing Page Crawler",
        landing_url,
        (
            f"抓取完成：HTTP {page_data['status_code']}，抽取 {len(page_data['text'])} 个文本字符。"
            if zh
            else f"Fetched status {page_data['status_code']} with {len(page_data['text'])} text characters."
        ),
        status="warning" if page_data["error"] else "success",
    )
    snapshot = None
    if landing_page:
        snapshot = PageSnapshot(
            landing_page_id=landing_page.id,
            title=page_data["title"],
            final_url=page_data["final_url"],
            status_code=page_data["status_code"],
            text_excerpt=page_data["text"][:6000],
            raw_html_excerpt=page_data["html_excerpt"],
            crawl_error=page_data["error"],
        )
        db.add(snapshot)
        for section in page_data["sections"]:
            db.add(PageSection(landing_page_id=landing_page.id, **section))
        db.flush()

    add_action(
        db,
        task,
        3,
        "投放指标分析器" if zh else "Metrics Analyzer",
        f"{len(campaign.metrics)} 行日级投放数据" if zh else f"{len(campaign.metrics)} daily metric rows",
        format_metrics_summary(metrics_summary, locale),
    )

    ai_result, raw_response, used_fallback = await call_or_fallback(
        ad_text=ad_text,
        page_data=page_data,
        campaign=campaign,
        metrics_summary=metrics_summary,
        locale=locale,
    )
    db.add(
        AIAnalysisRun(
            campaign_id=campaign.id,
            provider="deepseek",
            model=settings.deepseek_model,
            raw_response=raw_response,
            used_fallback=used_fallback,
        )
    )
    add_action(
        db,
        task,
        4,
        "DeepSeek 增长推理器" if zh else "DeepSeek Growth Reasoner",
        f"模型={settings.deepseek_model}" if zh else f"Model={settings.deepseek_model}",
        (
            "未检测到可用 DeepSeek 结果，已使用本地确定性规则生成中文演示结果。"
            if used_fallback and zh
            else "Used deterministic fallback."
            if used_fallback
            else "已解析 DeepSeek 返回的结构化 JSON。"
            if zh
            else "Parsed structured JSON response from DeepSeek."
        ),
        status="warning" if used_fallback else "success",
    )

    persist_analysis(db, campaign, ai_result, page_data, snapshot, locale)
    add_action(
        db,
        task,
        5,
        "证据记录器" if zh else "Evidence Logger",
        "承诺映射和落地页片段" if zh else "Claim mappings and page excerpts",
        (
            f"已存储 {len(ai_result.get('mappings', []))} 条承诺映射和证据。"
            if zh
            else f"Stored {len(ai_result.get('mappings', []))} claim mappings and evidence items."
        ),
    )
    add_action(
        db,
        task,
        6,
        "实验方案生成器" if zh else "Experiment Generator",
        "诊断结论、证据、评分和投放数据" if zh else "Diagnosis, evidence, scores, and performance data",
        (
            f"已生成 {len(ai_result.get('experiments', []))} 个可执行实验 brief。"
            if zh
            else f"Generated {len(ai_result.get('experiments', []))} experiment briefs."
        ),
        requires_human_review=True,
    )

    scores = ai_result.get("funnel_scores", {})
    campaign.message_match_score = bounded_score(scores.get("message_match", 0))
    campaign.cta_friction_score = bounded_score(scores.get("cta_friction", 0))
    campaign.trust_proof_score = bounded_score(scores.get("trust_proof", 0))
    campaign.mobile_readiness_score = bounded_score(scores.get("mobile_readiness", 0))
    campaign.experiment_priority_score = bounded_score(scores.get("experiment_priority", 0))
    campaign.diagnosis = ai_result.get("diagnosis", "")
    campaign.status = "analyzed"
    task.status = "completed"
    task.final_summary = campaign.diagnosis
    db.commit()
    db.refresh(campaign)
    return campaign


def clear_previous_analysis(db: Session, campaign: Campaign) -> None:
    for model in [ClaimPageMapping, CreativeClaim, EvidenceItem, Recommendation, Experiment, AIAnalysisRun]:
        db.query(model).filter(model.campaign_id == campaign.id).delete()
    landing_ids = [page.id for page in campaign.landing_pages]
    if landing_ids:
        db.query(PageSection).filter(PageSection.landing_page_id.in_(landing_ids)).delete()
        db.query(PageSnapshot).filter(PageSnapshot.landing_page_id.in_(landing_ids)).delete()
    db.flush()


async def call_or_fallback(
    ad_text: str,
    page_data: dict[str, Any],
    campaign: Campaign,
    metrics_summary: dict[str, Any],
    locale: str,
) -> tuple[dict[str, Any], str, bool]:
    client = DeepSeekClient()
    user_prompt = build_user_prompt(ad_text, page_data, campaign, metrics_summary, locale)
    result, raw_response, used_fallback = await client.complete_json(SYSTEM_PROMPT, user_prompt)
    if result and validate_ai_result(result):
        return normalize_ai_result(result), raw_response, used_fallback

    fallback = heuristic_analysis(ad_text, page_data, campaign, metrics_summary, locale)
    raw = raw_response if raw_response else json.dumps(fallback, ensure_ascii=False)
    return fallback, raw, True


def build_user_prompt(
    ad_text: str,
    page_data: dict[str, Any],
    campaign: Campaign,
    metrics_summary: dict[str, Any],
    locale: str,
) -> str:
    zh = is_chinese_locale(locale)
    schema = {
        "creative_claims": [
            {"text": "string", "claim_type": "hook|benefit|offer|audience|time|proof|cta", "confidence": 0.0, "risk_level": "low|medium|high"}
        ],
        "mappings": [
            {
                "claim_index": 0,
                "status": "matched|weak_match|missing|conflict",
                "evidence_text": "string",
                "risk": "string",
                "reasoning": "string",
                "confidence": 0.0,
            }
        ],
        "funnel_scores": {
            "message_match": 0,
            "cta_friction": 0,
            "trust_proof": 0,
            "mobile_readiness": 0,
            "experiment_priority": 0,
        },
        "diagnosis": "string",
        "recommendations": [
            {"title": "string", "description": "string", "priority": "high|medium|low", "confidence": 0.0}
        ],
        "experiments": [
            {
                "title": "string",
                "hypothesis": "string",
                "change_summary": "string",
                "success_metric": "string",
                "priority": "high|medium|low",
                "effort": "low|medium|high",
                "confidence": 0.0,
            }
        ],
    }
    language_rule = "请使用简体中文输出所有面向用户的字段。" if zh else "Use English for all user-facing fields."
    context_title = "中文开发者广告投放漏斗" if zh else "Ad funnel"
    return f"""
Context: {context_title}
Output language rule: {language_rule}

Campaign:
- Brand: {campaign.brand.name}
- Category: {campaign.brand.category}
- Goal: {campaign.goal}
- Target audience: {campaign.target_audience}
- Primary KPI: {campaign.primary_kpi}

Ad creative text:
{ad_text}

Landing page:
- URL: {page_data.get('final_url') or page_data.get('url')}
- Title: {page_data.get('title')}
- Crawl error: {page_data.get('error') or 'none'}
- Text excerpt:
{page_data.get('text', '')[:9000]}

Performance summary:
{json.dumps(metrics_summary, ensure_ascii=False)}

Return JSON that matches this schema:
{json.dumps(schema, ensure_ascii=False)}

Rules:
- Do not invent evidence. If the landing page text does not prove a claim, mark it missing or weak_match.
- Tie each recommendation to ad-to-page conversion friction.
- Use concise product-manager wording for a Chinese growth team.
- Scores should be 0 to 100, where higher means stronger performance for match/trust/mobile and higher urgency for cta_friction/experiment_priority.
"""


def validate_ai_result(result: dict[str, Any]) -> bool:
    return isinstance(result.get("creative_claims"), list) and isinstance(result.get("mappings"), list)


def normalize_ai_result(result: dict[str, Any]) -> dict[str, Any]:
    result.setdefault("creative_claims", [])
    result.setdefault("mappings", [])
    result.setdefault("funnel_scores", {})
    result.setdefault("diagnosis", "")
    result.setdefault("recommendations", [])
    result.setdefault("experiments", [])
    return result


def persist_analysis(
    db: Session,
    campaign: Campaign,
    result: dict[str, Any],
    page_data: dict[str, Any],
    snapshot: PageSnapshot | None,
    locale: str,
) -> None:
    zh = is_chinese_locale(locale)
    claim_rows: list[CreativeClaim] = []
    for claim in result.get("creative_claims", [])[:8]:
        row = CreativeClaim(
            campaign_id=campaign.id,
            text=str(claim.get("text", ""))[:1000],
            claim_type=str(claim.get("claim_type", "benefit"))[:80],
            confidence=float_or_default(claim.get("confidence"), 0.6),
            risk_level=str(claim.get("risk_level", "medium"))[:40],
        )
        db.add(row)
        db.flush()
        claim_rows.append(row)

    source_url = page_data.get("final_url") or page_data.get("url") or ""
    for mapping in result.get("mappings", [])[:10]:
        claim_index = int_or_default(mapping.get("claim_index"), 0)
        if not claim_rows:
            continue
        claim = claim_rows[max(0, min(claim_index, len(claim_rows) - 1))]
        status = str(mapping.get("status", "missing"))[:40]
        evidence_text = str(mapping.get("evidence_text", ""))[:1400]
        reasoning = str(mapping.get("reasoning", ""))[:1400]
        risk = str(mapping.get("risk", ""))[:1000]
        confidence = float_or_default(mapping.get("confidence"), 0.5)
        db.add(
            ClaimPageMapping(
                campaign_id=campaign.id,
                claim_id=claim.id,
                status=status,
                evidence_text=evidence_text,
                risk=risk,
                reasoning=reasoning,
                confidence=confidence,
            )
        )
        missing_quote = (
            f"落地页没有找到可验证证据：{claim.text}"
            if zh
            else f"No landing-page evidence found for: {claim.text}"
        )
        db.add(
            EvidenceItem(
                campaign_id=campaign.id,
                source_type="landing_page" if evidence_text else "missing_evidence",
                source_url=source_url,
                quote=evidence_text or missing_quote,
                interpretation=reasoning or risk,
                confidence=confidence,
            )
        )

    if snapshot and snapshot.crawl_error:
        db.add(
            EvidenceItem(
                campaign_id=campaign.id,
                source_type="crawler_error",
                source_url=source_url,
                quote=snapshot.crawl_error[:1000],
                interpretation="落地页抓取失败，需要人工复核页面。" if zh else "Landing page could not be fetched reliably. A human should verify the page manually.",
                confidence=0.9,
            )
        )

    for item in result.get("recommendations", [])[:8]:
        db.add(
            Recommendation(
                campaign_id=campaign.id,
                title=str(item.get("title", "提升漏斗清晰度" if zh else "Improve funnel clarity"))[:180],
                description=str(item.get("description", ""))[:2000],
                priority=str(item.get("priority", "medium"))[:40],
                confidence=float_or_default(item.get("confidence"), 0.6),
            )
        )

    for item in result.get("experiments", [])[:8]:
        db.add(
            Experiment(
                campaign_id=campaign.id,
                title=str(item.get("title", "落地页实验" if zh else "Landing page experiment"))[:180],
                hypothesis=str(item.get("hypothesis", ""))[:2000],
                change_summary=str(item.get("change_summary", ""))[:2000],
                success_metric=str(item.get("success_metric", "CVR"))[:120],
                priority=str(item.get("priority", "medium"))[:40],
                effort=str(item.get("effort", "medium"))[:40],
                confidence=float_or_default(item.get("confidence"), 0.6),
            )
        )
    db.flush()


def heuristic_analysis(
    ad_text: str,
    page_data: dict[str, Any],
    campaign: Campaign,
    metrics_summary: dict[str, Any],
    locale: str,
) -> dict[str, Any]:
    zh = is_chinese_locale(locale)
    claims = extract_claims(ad_text, campaign)
    page_text = page_data.get("text", "")
    mappings = []
    status_scores = []
    for index, claim in enumerate(claims):
        evidence, overlap = best_evidence(claim["text"], page_text)
        status = "matched" if overlap >= 0.3 else "weak_match" if overlap >= 0.12 else "missing"
        claim_lower = claim["text"].lower()
        page_lower = page_text.lower()
        if any(term in claim_lower for term in ["free", "trial", "免费", "试用"]) and any(term in page_lower for term in ["购买", "付款", "checkout", "buy now"]):
            status = "conflict"
        score = {"matched": 1.0, "weak_match": 0.55, "missing": 0.15, "conflict": 0.05}[status]
        status_scores.append(score)
        mappings.append(
            {
                "claim_index": index,
                "status": status,
                "evidence_text": evidence if status != "missing" else "",
                "risk": risk_for_status(status, claim["text"], zh),
                "reasoning": reasoning_for_status(status, claim["text"], evidence, zh),
                "confidence": round(0.62 + min(overlap, 0.3), 2),
            }
        )

    text_lower = page_text.lower()
    cta_terms = ["start", "try", "book", "sign up", "get", "demo", "buy", "注册", "试用", "立即", "预约", "开始", "免费"]
    proof_terms = ["review", "testimonial", "case", "customer", "security", "trusted", "rating", "用户评价", "案例", "认证", "客户", "数据", "团队"]
    mobile_terms = ["responsive", "mobile", "app", "手机", "移动端", "小程序", "随时"]

    message_match = round(100 * (sum(status_scores) / max(len(status_scores), 1)))
    cta_presence = any(term in text_lower for term in cta_terms)
    cta_friction = 38 if cta_presence else 74
    trust_proof = 76 if any(term in text_lower for term in proof_terms) else 46
    mobile_readiness = 70 if any(term in text_lower for term in mobile_terms) else 58
    metric_pressure = 12 if metrics_summary.get("cvr", 0) < 0.02 else 4
    experiment_priority = min(96, 100 - message_match + cta_friction / 2 + metric_pressure)

    missing_count = sum(1 for item in mappings if item["status"] in {"missing", "conflict"})
    if zh:
        diagnosis = (
            f"当前中文开发者广告漏斗存在 {missing_count} 个高风险承诺断点。"
            f"广告与落地页匹配度为 {message_match}/100，当前 CVR 为 {metrics_summary.get('cvr_percent', 'n/a')}。"
            "优先处理首屏承接、CTA 语义和可信证据，避免用户点击后发现页面没有兑现广告承诺。"
        )
        recommendations = [
            {
                "title": "把最强广告承诺放进落地页首屏",
                "description": "将广告里最能触发点击的承诺直接放到首屏标题或副标题，让中文开发者在进入页面后的 3 秒内确认没有走错页面。",
                "priority": "high",
                "confidence": 0.74,
            },
            {
                "title": "把泛 CTA 改成结果导向 CTA",
                "description": "避免只写“预约演示”或“了解更多”，改成与广告目标一致的动作，例如“免费生成广告诊断”或“开始 7 天试用”。",
                "priority": "high" if not cta_presence else "medium",
                "confidence": 0.7,
            },
            {
                "title": "补充中文开发者可信证据",
                "description": "在首个转化按钮附近加入真实案例、指标改善、客户评价或安全说明，降低试用前的不确定感。",
                "priority": "medium",
                "confidence": 0.64,
            },
        ]
        strongest_claim = claims[0]["text"] if claims else "核心广告承诺"
        experiments = [
            {
                "title": "首屏承诺一致性实验",
                "hypothesis": f"如果落地页首屏直接复述“{strongest_claim}”，中文开发者会更快确认产品价值，注册转化率会提升。",
                "change_summary": "重写首屏标题/副标题，加入广告承诺、一个量化结果和一个明确试用按钮。",
                "success_metric": "CVR 提升 >= 10%",
                "priority": "high",
                "effort": "low",
                "confidence": 0.72,
            },
            {
                "title": "免费试用 CTA 文案实验",
                "hypothesis": "如果 CTA 明确写出免费试用和低门槛，点击后的注册完成率会高于泛化 CTA。",
                "change_summary": "测试“开始 7 天免费试用”对比当前 CTA，并在移动端首屏保留主按钮。",
                "success_metric": "点击到注册完成率",
                "priority": "medium",
                "effort": "low",
                "confidence": 0.66,
            },
            {
                "title": "中文开发者案例证据实验",
                "hypothesis": "如果在首屏下方展示中文开发者团队案例和成本改善数据，表单提交率会提升。",
                "change_summary": "加入 2 条中文客户评价、1 个真实指标、1 张产品工作台截图。",
                "success_metric": "表单完成率",
                "priority": "medium",
                "effort": "medium",
                "confidence": 0.61,
            },
        ]
    else:
        diagnosis = (
            f"The funnel shows {missing_count} high-risk ad-to-page mismatch point(s). "
            f"Message match is {message_match}/100, and the current CVR is {metrics_summary.get('cvr_percent', 'n/a')}. "
            "Prioritize first-screen copy, CTA clarity, and proof blocks."
        )
        recommendations = [
            {
                "title": "Mirror the strongest ad promise in the landing-page hero",
                "description": "Move the highest-intent ad claim into the first-screen headline or subheadline so the click expectation is confirmed immediately.",
                "priority": "high",
                "confidence": 0.74,
            },
            {
                "title": "Turn weak CTAs into outcome-led CTAs",
                "description": "Replace generic CTA copy with a verb that matches the campaign goal and product outcome.",
                "priority": "high" if not cta_presence else "medium",
                "confidence": 0.7,
            },
            {
                "title": "Add proof near the first conversion action",
                "description": "Place testimonials, examples, or trust badges near the primary CTA to reduce uncertainty before conversion.",
                "priority": "medium",
                "confidence": 0.64,
            },
        ]
        strongest_claim = claims[0]["text"] if claims else "the core ad promise"
        experiments = [
            {
                "title": "Hero message-match rewrite",
                "hypothesis": f"If the landing page hero directly repeats '{strongest_claim}', users will feel they reached the expected page and CVR will improve.",
                "change_summary": "Rewrite hero headline/subheadline to mirror the ad promise and add one supporting proof line.",
                "success_metric": "CVR lift >= 10%",
                "priority": "high",
                "effort": "low",
                "confidence": 0.72,
            }
        ]

    return {
        "creative_claims": claims,
        "mappings": mappings,
        "funnel_scores": {
            "message_match": message_match,
            "cta_friction": round(cta_friction),
            "trust_proof": round(trust_proof),
            "mobile_readiness": round(mobile_readiness),
            "experiment_priority": round(experiment_priority),
        },
        "diagnosis": diagnosis,
        "recommendations": recommendations,
        "experiments": experiments,
    }


def extract_claims(ad_text: str, campaign: Campaign) -> list[dict[str, Any]]:
    chunks = [
        chunk.strip(" -•\t")
        for chunk in re.split(r"[\n。.!?；;]+", ad_text or "")
        if len(chunk.strip(" -•\t")) >= 4
    ]
    if not chunks:
        chunks = [campaign.goal, campaign.target_audience or campaign.brand.category]

    claims = []
    for chunk in chunks[:6]:
        claim_type = "benefit"
        lower = chunk.lower()
        if any(term in lower for term in ["free", "discount", "trial", "优惠", "免费", "试用", "无需信用卡"]):
            claim_type = "offer"
        elif any(term in lower for term in ["minute", "hour", "秒", "分钟", "小时", "快速"]):
            claim_type = "time"
        elif any(term in lower for term in ["for ", "适合", "面向", "专为", "开发者", "团队"]):
            claim_type = "audience"
        elif any(term in lower for term in ["start", "try", "book", "立即", "开始", "预约"]):
            claim_type = "cta"
        claims.append({"text": chunk[:500], "claim_type": claim_type, "confidence": 0.68, "risk_level": "medium"})
    return claims


def best_evidence(claim: str, page_text: str) -> tuple[str, float]:
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[。.!?])\s+|\n+", page_text) if sentence.strip()]
    if not sentences and page_text:
        sentences = [page_text[:600]]
    claim_tokens = token_set(claim)
    best = ""
    best_overlap = 0.0
    for sentence in sentences[:80]:
        overlap = jaccard(claim_tokens, token_set(sentence))
        if overlap > best_overlap:
            best = sentence[:600]
            best_overlap = overlap
    return best, best_overlap


def token_set(text: str) -> set[str]:
    lowered = (text or "").lower()
    tokens = {token for token in re.findall(r"[a-zA-Z0-9]+", lowered) if len(token) >= 2}
    for segment in re.findall(r"[\u4e00-\u9fff]+", lowered):
        if len(segment) == 1:
            tokens.add(segment)
        else:
            tokens.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def risk_for_status(status: str, claim: str, zh: bool) -> str:
    if zh:
        if status == "matched":
            return "低风险：落地页有清晰证据承接该广告承诺。"
        if status == "weak_match":
            return "中风险：落地页部分承接，但表达不够显眼或不够直接。"
        if status == "conflict":
            return "高风险：落地页信息可能与广告承诺冲突。"
        return f"高风险：用户点击时期望看到“{claim}”，但落地页没有明确兑现。"
    if status == "matched":
        return "Low risk: the page provides a visible support point for the ad claim."
    if status == "weak_match":
        return "Medium risk: the page partially supports the claim, but the evidence may not be visible or explicit enough."
    if status == "conflict":
        return "High risk: the landing page may contradict the ad promise."
    return f"High risk: users click expecting '{claim}', but the page does not clearly confirm it."


def reasoning_for_status(status: str, claim: str, evidence: str, zh: bool) -> str:
    if zh:
        if status == "missing":
            return "没有在落地页文本中找到能直接证明该广告承诺的内容。"
        return f"系统将广告承诺“{claim}”与落地页证据进行匹配：{evidence[:260]}"
    if status == "missing":
        return "No clear landing-page text was found for this ad claim."
    return f"The claim '{claim}' was compared against this landing-page evidence: {evidence[:260]}"


def summarize_metrics(campaign: Campaign) -> dict[str, Any]:
    total = Counter()
    for row in campaign.metrics:
        total["impressions"] += row.impressions
        total["clicks"] += row.clicks
        total["conversions"] += row.conversions
        total["spend"] += row.spend
        total["revenue"] += row.revenue

    impressions = total["impressions"]
    clicks = total["clicks"]
    conversions = total["conversions"]
    spend = float(total["spend"])
    revenue = float(total["revenue"])
    ctr = clicks / impressions if impressions else 0
    cvr = conversions / clicks if clicks else 0
    cpa = spend / conversions if conversions else math.inf
    roas = revenue / spend if spend else 0
    return {
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": round(spend, 2),
        "revenue": round(revenue, 2),
        "ctr": ctr,
        "ctr_percent": f"{ctr * 100:.2f}%",
        "cvr": cvr,
        "cvr_percent": f"{cvr * 100:.2f}%",
        "cpa": None if math.isinf(cpa) else round(cpa, 2),
        "roas": round(roas, 2),
    }


def format_metrics_summary(summary: dict[str, Any], locale: str = "zh-CN") -> str:
    if is_chinese_locale(locale):
        return (
            f"CTR {summary.get('ctr_percent')}，CVR {summary.get('cvr_percent')}，"
            f"CPA {summary.get('cpa')}，ROAS {summary.get('roas')}。"
        )
    return (
        f"CTR {summary.get('ctr_percent')}, CVR {summary.get('cvr_percent')}, "
        f"CPA {summary.get('cpa')}, ROAS {summary.get('roas')}."
    )


def bounded_score(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0
    return max(0, min(100, numeric))


def float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
