import argparse
import asyncio

from app.agent import run_growth_audit
from app.database import SessionLocal, init_db
from app.sample_data import create_official_demos, reset_official_demos


async def seed(clear_all: bool, analyze: bool) -> None:
    init_db()
    with SessionLocal() as db:
        if clear_all:
            campaigns = reset_official_demos(db)
        else:
            campaigns = create_official_demos(db)
        print(f"official_demos={len(campaigns)}")
        if analyze:
            for campaign in campaigns:
                print(f"analyzing={campaign.demo_key}")
                await run_growth_audit(db, campaign, locale="zh-CN")
            print("analysis_complete=true")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear-all", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()
    asyncio.run(seed(clear_all=args.clear_all, analyze=args.analyze))
