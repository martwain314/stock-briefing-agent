"""
AI 브리핑 생성 엔진

Google Gemini API를 사용하여 수집된 데이터 기반 투자 브리핑을 생성합니다.
상태를 가지지 않으므로 모듈 함수로 구성
"""

import re
from datetime import datetime

from google import genai
from loguru import logger

from src.common.types import BriefingResult, CollectedData

# 모듈 레벨 클라이언트 (init 시 설정)
_client: genai.Client | None = None

_SYSTEM_PROMPT = """당신은 개인 투자자를 위한 전문 투자 브리핑 비서입니다.

역할:
- 수집된 경제/정치/시장 데이터를 분석하여 투자에 영향을 미치는 핵심 인사이트를 제공합니다
- ETF와 개별 주식 투자자 관점에서 실용적인 정보를 전달합니다
- 한국어로 간결하고 명확하게 브리핑합니다

브리핑 원칙:
1. 핵심 먼저: 가장 중요한 정보를 맨 앞에
2. 투자 영향도 중심: "이 뉴스가 시장에 어떤 영향을 주는가"를 항상 분석
3. 섹터/업종 연결: 뉴스가 어떤 섹터/ETF에 영향을 주는지 연결
4. 감성 편향 배제: 사실 기반 중립적 분석, 과도한 낙관/비관 금지
5. 실행 가능한 인사이트: 단순 정보 나열이 아닌, "그래서 어떻게 해야 하는가"

출력 형식 (텔레그램 메시지):
- 이모지를 활용하여 가독성 확보
- 섹션별로 구분하여 읽기 쉽게
- 핵심 포인트는 불릿으로 정리
- 너무 길지 않게 (텔레그램 메시지 1개에 들어갈 분량)"""

_BULLISH_KEYWORDS = ["상승", "반등", "호재", "강세", "회복", "매수", "긍정", "성장"]
_BEARISH_KEYWORDS = ["하락", "급락", "악재", "약세", "위험", "매도", "부정", "침체"]

# Gemini 모델명
_MODEL_NAME = "gemini-2.0-flash"


def init_analyzer(api_key: str) -> None:
    """AI 분석 엔진을 초기화

    Args:
        api_key: Google Gemini API Key
    """
    global _client
    _client = genai.Client(api_key=api_key)
    logger.info("Gemini AI 분석 엔진 초기화 완료")


def _format_data_for_prompt(data: CollectedData) -> str:
    """수집된 데이터를 프롬프트용 텍스트로 포맷

    Args:
        data: 수집된 전체 데이터

    Returns:
        프롬프트에 삽입할 포맷팅된 텍스트
    """
    sections: list[str] = []

    if data.markets:
        sections.append("[ 시장 지수 ]")
        for m in data.markets:
            sign = "+" if m.change_percent >= 0 else ""
            sections.append(
                f"  {m.name}: {m.current_price:,.0f} ({sign}{m.change_percent}%)"
            )

    if data.indicators:
        sections.append("\n[ 경제 지표 ]")
        for ind in data.indicators:
            sections.append(f"  {ind.name}: {ind.value} {ind.change or ''}")

    if data.watchlist:
        sections.append("\n[ 관심 종목 ]")
        for w in data.watchlist:
            sign = "+" if w.change_percent >= 0 else ""
            sections.append(f"  {w.name}: {w.price:,.0f}원 ({sign}{w.change_percent}%)")

    if data.news:
        sections.append("\n[ 주요 뉴스 ]")
        for article in data.news:
            sections.append(
                f"  [{article.category}] {article.title} ({article.source})"
            )
            if article.summary:
                sections.append(f"    > {article.summary}")

    return "\n".join(sections)


def _extract_highlights(content: str) -> list[str]:
    """브리핑에서 핵심 포인트를 추출

    Args:
        content: AI 생성 브리핑 텍스트

    Returns:
        핵심 포인트 문자열 목록 (최대 5개)
    """
    highlights: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if any(ch in stripped for ch in ["•", "-", "▶"]) and len(stripped) > 10:
            highlights.append(stripped)
    return highlights[:5]


def _detect_sentiment(content: str) -> str:
    """브리핑 텍스트에서 전반적 시장 심리를 감지

    Args:
        content: AI 생성 브리핑 텍스트

    Returns:
        "bullish", "bearish", "neutral" 중 하나
    """
    lower = content.lower()
    bullish_count = sum(len(re.findall(kw, lower)) for kw in _BULLISH_KEYWORDS)
    bearish_count = sum(len(re.findall(kw, lower)) for kw in _BEARISH_KEYWORDS)

    if bullish_count > bearish_count * 1.5:
        return "bullish"
    if bearish_count > bullish_count * 1.5:
        return "bearish"
    return "neutral"


async def generate_briefing(
    data: CollectedData,
    briefing_type: str,
) -> BriefingResult:
    """수집된 데이터를 기반으로 AI 브리핑을 생성

    Args:
        data: 수집된 전체 데이터
        briefing_type: 브리핑 유형 ("morning", "evening", "alert", "on-demand")

    Returns:
        AI 브리핑 결과

    Raises:
        RuntimeError: 분석 엔진이 초기화되지 않은 경우
    """
    if _client is None:
        raise RuntimeError(
            "분석 엔진이 초기화되지 않았습니다. init_analyzer()를 먼저 호출하세요."
        )

    type_labels = {
        "morning": "오전 장전 브리핑",
        "evening": "장마감 리뷰",
        "alert": "긴급 알림",
        "on-demand": "요약 브리핑",
    }
    time_label = type_labels.get(briefing_type, "요약 브리핑")
    now = datetime.now()
    data_context = _format_data_for_prompt(data)

    user_prompt = f"""현재 시간: {now.strftime("%Y년 %m월 %d일 %H:%M")} (KST)
브리핑 유형: {time_label}

===== 수집된 데이터 =====
{data_context}
===========================

위 데이터를 기반으로 {time_label}을 작성해주세요.

다음 구조로 브리핑을 작성하세요:

1. 📊 시장 현황 (주요 지수 및 변동)
2. 📰 오늘의 핵심 뉴스 (투자 영향도 높은 뉴스 3-5개, 각각 시장 영향 분석 포함)
3. 🌍 글로벌 이슈 (해외 시장 및 국제 정세 중 투자 관련)
4. 🏛️ 정치/정책 동향 (시장에 영향 줄 수 있는 정치적 이슈)
5. 💡 투자 인사이트 (위 정보를 종합한 실행 가능한 제안)
6. 📋 관심 종목 현황 (관심 종목 시세 요약)

마지막에 전체 시장 심리를 한 줄로 요약해주세요."""

    try:
        logger.info(f"AI 브리핑 생성 중... ({time_label})")

        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=f"{_SYSTEM_PROMPT}\n\n{user_prompt}",
            config=genai.types.GenerateContentConfig(
                max_output_tokens=2000,
                temperature=0.7,
            ),
        )

        content = response.text or ""
        highlights = _extract_highlights(content)
        sentiment = _detect_sentiment(content)

        logger.info(f"AI 브리핑 생성 완료 ({len(content)}자)")

        return BriefingResult(
            type=briefing_type,
            content=content,
            highlights=highlights,
            sentiment=sentiment,
            generated_at=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"AI 브리핑 생성 실패: {e}")
        raise


async def generate_quick_alert(headline: str, context: str) -> str:
    """실시간 알림용 빠른 분석을 생성

    Args:
        headline: 뉴스 헤드라인
        context: 추가 맥락 정보

    Returns:
        AI 분석 텍스트

    Raises:
        RuntimeError: 분석 엔진이 초기화되지 않은 경우
    """
    if _client is None:
        raise RuntimeError("분석 엔진이 초기화되지 않았습니다.")

    try:
        prompt = f"""투자자를 위한 빠른 뉴스 분석 비서입니다. 핵심만 간결하게 전달하세요. 한국어로 답변하세요.

속보/중요 뉴스가 감지되었습니다:

제목: {headline}
맥락: {context}

다음을 간결하게 분석해주세요:
1. 핵심 내용 (1-2줄)
2. 시장 영향 (상승/하락/중립)
3. 영향 받는 섹터/종목
4. 투자자 대응 제안 (1줄)"""

        response = _client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                max_output_tokens=500,
                temperature=0.5,
            ),
        )

        return response.text or ""
    except Exception as e:
        logger.error(f"빠른 분석 실패: {e}")
        return f"⚠️ 알림: {headline}\n(AI 분석 일시적 오류)"
