"""
즉시 브리핑 CLI 명령어

터미널에서 바로 브리핑을 확인할 수 있는 CLI 도구입니다.
사용법: python -m src.commands.brief_now
"""

import asyncio
from datetime import datetime

from dotenv import load_dotenv

from src.common.config import load_settings
from src.common.logger import setup_logger
from src.analyzer.briefing_engine import init_analyzer, generate_briefing
from src.collector.news_collector import collect_all_news
from src.collector.market_collector import collect_all_market_data
from src.common.types import CollectedData


async def brief_now() -> None:
    """CLI에서 즉시 브리핑을 실행"""
    load_dotenv()
    settings = load_settings()
    setup_logger(settings.log_level)

    print("📡 데이터 수집 중...\n")

    init_analyzer(settings.gemini_api_key)
    watchlist = settings.get_watchlist()

    # 데이터 수집
    news, (markets, indicators, watchlist_items) = await asyncio.gather(
        collect_all_news(),
        collect_all_market_data(watchlist),
    )

    collected = CollectedData(
        news=news,
        markets=markets,
        watchlist=watchlist_items,
        indicators=indicators,
        collected_at=datetime.now().isoformat(),
    )

    print(
        f"✅ 수집 완료: 뉴스 {len(news)}건, "
        f"지수 {len(markets)}개, 종목 {len(watchlist_items)}개\n"
    )
    print("🤖 AI 브리핑 생성 중...\n")

    briefing = await generate_briefing(collected, "on-demand")

    print("=" * 50)
    print(briefing.content)
    print("=" * 50)
    print(f"\n심리: {briefing.sentiment} | 생성: {briefing.generated_at}")


def main() -> None:
    """엔트리포인트"""
    asyncio.run(brief_now())


if __name__ == "__main__":
    main()
