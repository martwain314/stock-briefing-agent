"""
스케줄러 모듈

정기 브리핑 스케줄링 및 실시간 뉴스 모니터링을 담당합니다.
APScheduler 인스턴스와 뉴스 중복 감지 상태를 관리하므로 클래스로 구성합니다.
"""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from src.collector.news_collector import collect_all_news
from src.collector.market_collector import collect_all_market_data
from src.analyzer.briefing_engine import generate_briefing, generate_quick_alert
from src.common.types import CollectedData, NewsArticle

# 중요 키워드 목록 (실시간 알림 트리거)
ALERT_KEYWORDS = [
    # 경제 이벤트
    "금리",
    "기준금리",
    "긴급",
    "폭락",
    "폭등",
    "서킷브레이커",
    "사이드카",
    "상한가",
    "하한가",
    # 정치/정책
    "계엄",
    "탄핵",
    "대통령",
    "비상",
    "전쟁",
    # 글로벌
    "연준",
    "fed",
    "트럼프",
    "관세",
    "제재",
    # 산업
    "반도체",
    "ai",
    "배터리",
    "원유",
]


class SchedulerService:
    """스케줄러 서비스

    APScheduler 인스턴스, 관심 종목 목록, 뉴스 중복 감지용 Set 등을 관리합니다.
    """

    def __init__(self, watchlist: list[str], send_message_fn, send_briefing_fn):
        """
        Args:
            watchlist: 관심 종목 리스트
            send_message_fn: 텔레그램 메시지 발송 함수 (async)
            send_briefing_fn: 브리핑 결과 발송 함수 (async)
        """
        self.watchlist = watchlist
        self.send_message = send_message_fn
        self.send_briefing = send_briefing_fn
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self._seen_headlines: set[str] = set()

    async def _collect_all_data(self) -> CollectedData:
        """전체 데이터를 수집

        Returns:
            수집된 전체 데이터
        """
        news, (markets, indicators, watchlist_items) = await asyncio.gather(
            collect_all_news(),
            collect_all_market_data(self.watchlist),
        )

        return CollectedData(
            news=news,
            markets=markets,
            watchlist=watchlist_items,
            indicators=indicators,
            collected_at=datetime.now().isoformat(),
        )

    async def _run_briefing(self, briefing_type: str) -> None:
        """정기 브리핑을 실행

        Args:
            briefing_type: "morning" 또는 "evening"
        """
        label = "오전" if briefing_type == "morning" else "저녁"
        logger.info(f"📅 {label} 정기 브리핑 시작")

        try:
            data = await self._collect_all_data()
            briefing = await generate_briefing(data, briefing_type)
            await self.send_briefing(briefing)
        except Exception as e:
            logger.error(f"{label} 브리핑 실패: {e}")
            await self.send_message(f"⚠️ {label} 브리핑 생성 실패. 로그를 확인하세요.")

    async def _monitor_news(self) -> None:
        """실시간 뉴스를 모니터링하고 중요 뉴스 감지 시 알림"""
        try:
            logger.debug("실시간 뉴스 모니터링 중...")
            news = await collect_all_news()
            await self._check_for_alerts(news)
        except Exception as e:
            logger.error(f"실시간 모니터링 오류: {e}")

    async def _check_for_alerts(self, news: list[NewsArticle]) -> None:
        """새 뉴스 중 알림이 필요한 것을 체크하여 발송

        Args:
            news: 수집된 뉴스 목록
        """
        for article in news:
            if article.title in self._seen_headlines:
                continue
            self._seen_headlines.add(article.title)

            # Set 크기 관리 (최근 500개만 유지)
            if len(self._seen_headlines) > 500:
                to_remove = list(self._seen_headlines)[:100]
                for item in to_remove:
                    self._seen_headlines.discard(item)

            # 중요 키워드 매칭
            title_lower = article.title.lower()
            matched = [kw for kw in ALERT_KEYWORDS if kw.lower() in title_lower]

            if matched:
                logger.info(f"🚨 중요 뉴스 감지: {article.title}")

                try:
                    analysis = await generate_quick_alert(
                        article.title,
                        f"출처: {article.source}\n요약: {article.summary}\n카테고리: {article.category}",
                    )
                    alert_message = (
                        f"🚨 *실시간 알림*\n\n"
                        f"📰 *{article.title}*\n"
                        f"출처: {article.source}\n\n"
                        f"{analysis}\n\n"
                        f"🔗 [기사 원문]({article.url})"
                    )
                except Exception:
                    alert_message = (
                        f"🚨 *실시간 알림*\n\n"
                        f"📰 *{article.title}*\n"
                        f"출처: {article.source}\n"
                        f"키워드: {', '.join(matched)}\n\n"
                        f"🔗 [기사 원문]({article.url})"
                    )

                await self.send_message(alert_message)

    async def _initialize_seen_headlines(self) -> None:
        """초기 뉴스를 수집하여 중복 방지용 Set을 채움"""
        try:
            news = await collect_all_news()
            for article in news:
                self._seen_headlines.add(article.title)
            logger.info(f"기존 뉴스 {len(self._seen_headlines)}건 등록 (중복 방지)")
        except Exception as e:
            logger.warning(f"초기 뉴스 수집 실패: {e}")

    def start(
        self,
        morning_hour: int,
        morning_minute: int,
        evening_hour: int,
        evening_minute: int,
        monitor_interval_minutes: int,
    ) -> None:
        """스케줄러를 시작

        Args:
            morning_hour: 오전 브리핑 시간 (시)
            morning_minute: 오전 브리핑 시간 (분)
            evening_hour: 저녁 브리핑 시간 (시)
            evening_minute: 저녁 브리핑 시간 (분)
            monitor_interval_minutes: 실시간 모니터링 간격 (분)
        """
        # 오전 브리핑 (평일만)
        self.scheduler.add_job(
            self._run_briefing,
            CronTrigger(
                hour=morning_hour, minute=morning_minute, day_of_week="mon-fri"
            ),
            args=["morning"],
            id="morning_briefing",
        )

        # 저녁 브리핑 (평일만)
        self.scheduler.add_job(
            self._run_briefing,
            CronTrigger(
                hour=evening_hour, minute=evening_minute, day_of_week="mon-fri"
            ),
            args=["evening"],
            id="evening_briefing",
        )

        # 실시간 뉴스 모니터링
        self.scheduler.add_job(
            self._monitor_news,
            IntervalTrigger(minutes=monitor_interval_minutes),
            id="news_monitor",
        )

        # 시작 전 기존 뉴스 수집 (중복 방지)
        asyncio.get_event_loop().create_task(self._initialize_seen_headlines())

        self.scheduler.start()
        logger.info(
            f"스케줄러 시작: 오전({morning_hour:02d}:{morning_minute:02d}), "
            f"저녁({evening_hour:02d}:{evening_minute:02d}), "
            f"모니터링({monitor_interval_minutes}분 간격)"
        )
