"""
Stock Briefing Agent - 메인 엔트리포인트

AI 투자 브리핑 텔레그램 봇의 메인 실행 파일입니다.
"""

import asyncio
import signal

from dotenv import load_dotenv
from loguru import logger

from src.common.config import load_settings
from src.common.logger import setup_logger
from src.analyzer.briefing_engine import init_analyzer
from src.bot.telegram_bot import TelegramBotService
from src.scheduler.scheduler_service import SchedulerService


async def main() -> None:
    """애플리케이션 메인 함수"""
    load_dotenv()

    print(
        """
  ╔══════════════════════════════════════════╗
  ║   📊 Stock Briefing Agent v1.0.0        ║
  ║   AI 투자 브리핑 텔레그램 봇             ║
  ╚══════════════════════════════════════════╝
    """
    )

    # 1. 설정 로드
    settings = load_settings()
    setup_logger(settings.log_level)
    logger.info("설정 로드 완료")
    logger.info(f"관심 종목: {', '.join(settings.get_watchlist())}")

    # 2. AI 분석 엔진 초기화
    init_analyzer(settings.gemini_api_key)

    # 3. 텔레그램 봇 초기화
    bot_service = TelegramBotService(
        token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        watchlist=settings.get_watchlist(),
    )

    # 4. 스케줄러 초기화
    morning_h, morning_m = settings.get_morning_hour_minute()
    evening_h, evening_m = settings.get_evening_hour_minute()

    scheduler_service = SchedulerService(
        watchlist=settings.get_watchlist(),
        send_message_fn=bot_service.send_message,
        send_briefing_fn=bot_service.send_briefing,
    )
    scheduler_service.start(
        morning_hour=morning_h,
        morning_minute=morning_m,
        evening_hour=evening_h,
        evening_minute=evening_m,
        monitor_interval_minutes=settings.monitor_interval_minutes,
    )

    # 5. 시작 알림 전송
    async with bot_service.app:
        await bot_service.app.initialize()
        await bot_service.send_message(
            f"🤖 *투자 브리핑 에이전트 시작*\n\n"
            f"⏰ 오전 브리핑: 평일 {settings.morning_brief_time}\n"
            f"⏰ 저녁 브리핑: 평일 {settings.evening_brief_time}\n"
            f"🔔 실시간 모니터링: {settings.monitor_interval_minutes}분 간격\n"
            f"📋 관심 종목: {', '.join(settings.get_watchlist())}\n\n"
            f"/brief 명령어로 즉시 브리핑을 받을 수 있습니다."
        )

        logger.info("🚀 Stock Briefing Agent 시작 완료!")

        # 6. 봇 polling 시작
        await bot_service.app.start()
        await bot_service.app.updater.start_polling()

        # 종료 시그널 대기
        stop_event = asyncio.Event()

        def _signal_handler() -> None:
            logger.info("종료 신호 수신...")
            stop_event.set()

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _signal_handler)

        await stop_event.wait()

        # 정리
        logger.info("에이전트 종료 중...")
        await bot_service.send_message("🔴 투자 브리핑 에이전트가 종료됩니다.")
        await bot_service.app.updater.stop()
        await bot_service.app.stop()
        await bot_service.app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
