"""
텔레그램 봇 모듈

텔레그램 명령어 처리 및 메시지 발송을 담당합니다.
python-telegram-bot의 Application을 상태로 관리하므로 클래스로 구성합니다.
"""

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from loguru import logger

from src.collector.news_collector import collect_all_news
from src.collector.market_collector import collect_all_market_data
from src.analyzer.briefing_engine import generate_briefing, generate_quick_alert
from src.common.types import BriefingResult, CollectedData


class TelegramBotService:
    """텔레그램 봇 서비스

    봇 Application 인스턴스와 채팅 ID, 관심 종목 등 상태를 관리합니다.
    """

    def __init__(self, token: str, chat_id: str, watchlist: list[str]):
        self.chat_id = chat_id
        self.watchlist = watchlist
        self.app = Application.builder().token(token).build()
        self._register_handlers()
        logger.info("텔레그램 봇 초기화 완료")

    def _register_handlers(self) -> None:
        """텔레그램 명령어 핸들러를 등록"""
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("brief", self._cmd_brief))
        self.app.add_handler(CommandHandler("market", self._cmd_market))
        self.app.add_handler(CommandHandler("watchlist", self._cmd_watchlist))
        self.app.add_handler(CommandHandler("add", self._cmd_add))
        self.app.add_handler(CommandHandler("remove", self._cmd_remove))
        self.app.add_handler(CommandHandler("list", self._cmd_list))
        self.app.add_handler(CommandHandler("ask", self._cmd_ask))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        logger.info("텔레그램 명령어 등록 완료")

    def _is_authorized(self, update: Update) -> bool:
        """인가된 사용자인지 확인

        Args:
            update: 텔레그램 업데이트 객체

        Returns:
            인가된 사용자이면 True
        """
        if not update.effective_chat:
            return False
        msg_chat_id = str(update.effective_chat.id)
        if msg_chat_id != self.chat_id:
            logger.warning(f"미인가 접근: {msg_chat_id}")
            return False
        return True

    async def _cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """봇 시작 명령어"""
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "🤖 *투자 브리핑 에이전트 활성화*\n\n"
            "사용 가능한 명령어:\n"
            "/brief - 즉시 브리핑 받기\n"
            "/market - 현재 시장 현황\n"
            "/watchlist - 관심 종목 시세\n"
            "/add [종목명] - 관심 종목 추가\n"
            "/remove [종목명] - 관심 종목 제거\n"
            "/list - 관심 종목 목록\n"
            "/ask [질문] - AI에게 투자 관련 질문\n"
            "/help - 도움말",
            parse_mode="Markdown",
        )

    async def _cmd_brief(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """즉시 브리핑 명령어"""
        if not self._is_authorized(update):
            return
        await update.message.reply_text("📡 데이터 수집 중... 잠시만 기다려주세요.")

        try:
            collected = await self._collect_all_data()
            briefing = await generate_briefing(collected, "on-demand")
            await self.send_briefing(briefing)
        except Exception as e:
            logger.error(f"즉시 브리핑 실패: {e}")
            await update.message.reply_text("⚠️ 브리핑 생성 중 오류가 발생했습니다.")

    async def _cmd_market(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """시장 현황 명령어"""
        if not self._is_authorized(update):
            return
        await update.message.reply_text("📊 시장 데이터 조회 중...")

        try:
            markets, indicators, _ = await collect_all_market_data(self.watchlist)

            message = "📊 *현재 시장 현황*\n\n"
            for m in markets:
                emoji = "🔴" if m.change_percent >= 0 else "🔵"
                sign = "+" if m.change_percent >= 0 else ""
                message += f"{emoji} *{m.name}*: {m.current_price:,.0f} ({sign}{m.change_percent}%)\n"

            if indicators:
                message += "\n💹 *주요 지표*\n"
                for ind in indicators:
                    message += f"  {ind.name}: {ind.value} {ind.change or ''}\n"

            await self.send_message(message)
        except Exception as e:
            logger.error(f"시장 현황 조회 실패: {e}")
            await update.message.reply_text("⚠️ 시장 데이터 조회 실패")

    async def _cmd_watchlist(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """관심 종목 시세 명령어"""
        if not self._is_authorized(update):
            return

        try:
            from src.collector.market_collector import collect_watchlist

            items = await collect_watchlist(self.watchlist)

            message = "📋 *관심 종목 현황*\n\n"
            for item in items:
                emoji = "📈" if item.change_percent >= 0 else "📉"
                sign = "+" if item.change_percent >= 0 else ""
                message += f"{emoji} *{item.name}*\n"
                message += f"   {item.price:,.0f}원 ({sign}{item.change_percent}%)\n\n"

            await self.send_message(message)
        except Exception as e:
            logger.error(f"관심종목 조회 실패: {e}")
            await update.message.reply_text("⚠️ 관심 종목 조회 실패")

    async def _cmd_add(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """관심 종목 추가 명령어"""
        if not self._is_authorized(update):
            return

        name = " ".join(context.args) if context.args else ""
        if not name:
            await update.message.reply_text("사용법: /add [종목명]")
            return

        if name not in self.watchlist:
            self.watchlist.append(name)
            await update.message.reply_text(
                f"✅ *{name}* 관심 종목에 추가\n현재: {', '.join(self.watchlist)}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"ℹ️ *{name}*은(는) 이미 관심 종목에 있습니다.", parse_mode="Markdown"
            )

    async def _cmd_remove(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """관심 종목 제거 명령어"""
        if not self._is_authorized(update):
            return

        name = " ".join(context.args) if context.args else ""
        if not name:
            await update.message.reply_text("사용법: /remove [종목명]")
            return

        if name in self.watchlist:
            self.watchlist.remove(name)
            await update.message.reply_text(
                f"🗑️ *{name}* 관심 종목에서 제거\n현재: {', '.join(self.watchlist)}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"ℹ️ *{name}*은(는) 관심 종목에 없습니다.", parse_mode="Markdown"
            )

    async def _cmd_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """관심 종목 목록 명령어"""
        if not self._is_authorized(update):
            return

        if not self.watchlist:
            await update.message.reply_text(
                "📋 관심 종목이 없습니다. /add [종목명]으로 추가하세요."
            )
        else:
            items = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(self.watchlist))
            await update.message.reply_text(
                f"📋 *관심 종목 목록*\n\n{items}", parse_mode="Markdown"
            )

    async def _cmd_ask(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """AI 질문 명령어"""
        if not self._is_authorized(update):
            return

        question = " ".join(context.args) if context.args else ""
        if not question:
            await update.message.reply_text("사용법: /ask [질문]")
            return

        await update.message.reply_text("🤔 분석 중...")

        try:
            answer = await generate_quick_alert(question, "사용자의 투자 관련 질문")
            await self.send_message(f"💡 *AI 답변*\n\n{answer}")
        except Exception as e:
            logger.error(f"AI 질문 응답 실패: {e}")
            await update.message.reply_text("⚠️ AI 응답 생성 실패")

    async def _cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """도움말 명령어"""
        if not self._is_authorized(update):
            return
        await update.message.reply_text(
            "📖 *도움말*\n\n"
            "🔹 /brief - 지금 바로 전체 브리핑\n"
            "🔹 /market - 주요 지수/지표 현황\n"
            "🔹 /watchlist - 관심 종목 시세\n"
            "🔹 /add [종목명] - 관심 종목 추가\n"
            "🔹 /remove [종목명] - 관심 종목 제거\n"
            "🔹 /list - 관심 종목 목록 보기\n"
            "🔹 /ask [질문] - AI에게 투자 관련 질문\n\n"
            "⏰ 자동 브리핑: 평일 오전/저녁\n"
            "🔔 실시간 모니터링: 30분 간격으로 중요 뉴스 감지",
            parse_mode="Markdown",
        )

    async def _collect_all_data(self) -> CollectedData:
        """전체 데이터를 수집

        Returns:
            수집된 전체 데이터
        """
        import asyncio
        from datetime import datetime

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

    async def send_message(self, text: str) -> None:
        """텔레그램 메시지를 발송

        4096자 초과 시 분할하여 전송합니다.

        Args:
            text: 발송할 메시지 텍스트
        """
        try:
            if len(text) > 4000:
                chunks = _split_message(text, 4000)
                for chunk in chunks:
                    await self.app.bot.send_message(
                        chat_id=self.chat_id, text=chunk, parse_mode="Markdown"
                    )
            else:
                await self.app.bot.send_message(
                    chat_id=self.chat_id, text=text, parse_mode="Markdown"
                )
        except Exception:
            # Markdown 파싱 실패 시 일반 텍스트로 재시도
            try:
                await self.app.bot.send_message(chat_id=self.chat_id, text=text)
            except Exception as e:
                logger.error(f"텔레그램 메시지 전송 실패: {e}")

    async def send_briefing(self, briefing: BriefingResult) -> None:
        """브리핑 결과를 텔레그램으로 전송

        Args:
            briefing: AI 브리핑 결과
        """
        sentiment_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(
            briefing.sentiment, "🟡"
        )
        header_map = {
            "morning": "☀️ 오전 장전 브리핑",
            "evening": "🌙 장마감 리뷰",
            "alert": "🚨 긴급 알림",
            "on-demand": "📋 투자 브리핑",
        }
        header = header_map.get(briefing.type, "📋 투자 브리핑")

        message = f"{header} {sentiment_emoji}\n{'─' * 20}\n\n{briefing.content}"
        await self.send_message(message)
        logger.info(f"브리핑 전송 완료 ({briefing.type})")


def _split_message(text: str, max_length: int) -> list[str]:
    """긴 메시지를 줄바꿈 기준으로 분할

    Args:
        text: 원본 메시지
        max_length: 최대 문자 수

    Returns:
        분할된 메시지 목록
    """
    chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    return chunks
