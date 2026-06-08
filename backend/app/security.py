import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.database import settings
from app.models import RateLimitEvent


def is_admin_request(request: Request) -> bool:
    token = request.headers.get("x-admin-token", "")
    return bool(settings.admin_seed_token and token and token == settings.admin_seed_token)


def require_admin(request: Request) -> None:
    if not is_admin_request(request):
        raise HTTPException(status_code=404, detail="Not found")


def visitor_hash(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    return hashlib.sha256(f"{settings.rate_limit_salt}:{address}".encode()).hexdigest()


def enforce_rate_limit(
    db: Session,
    request: Request,
    action: str,
    hourly_limit: int,
    daily_limit: int | None = None,
) -> None:
    if is_admin_request(request):
        return
    now = datetime.now(UTC).replace(tzinfo=None)
    hashed = visitor_hash(request)
    base = db.query(RateLimitEvent).filter(
        RateLimitEvent.visitor_hash == hashed,
        RateLimitEvent.action == action,
    )
    if base.filter(RateLimitEvent.created_at >= now - timedelta(hours=1)).count() >= hourly_limit:
        raise HTTPException(status_code=429, detail="操作过于频繁，请一小时后再试。")
    if daily_limit and base.filter(RateLimitEvent.created_at >= now - timedelta(days=1)).count() >= daily_limit:
        raise HTTPException(status_code=429, detail="今日体验次数已用完，请明天再试。")

    db.add(RateLimitEvent(visitor_hash=hashed, action=action, created_at=now))
    db.query(RateLimitEvent).filter(RateLimitEvent.created_at < now - timedelta(days=2)).delete()
    db.commit()
