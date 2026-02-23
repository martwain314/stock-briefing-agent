"""
공통 데이터 타입 정의

모든 모듈에서 공유하는 Pydantic 모델을 정의합니다.
"""

from typing import Optional, Literal
from pydantic import BaseModel


class NewsArticle(BaseModel):
    """뉴스 기사"""

    title: str
    summary: str
    url: str
    source: str
    published_at: str
    category: Literal[
        "economy", "politics", "market", "industry", "global", "policy", "trend"
    ]


class MarketData(BaseModel):
    """시장 지수 데이터"""

    name: str
    current_price: float
    change_percent: float
    change_amount: float
    volume: Optional[int] = None
    updated_at: str


class WatchlistItem(BaseModel):
    """관심 종목 시세"""

    name: str
    code: Optional[str] = None
    price: float
    change_percent: float
    change_amount: float


class EconomicIndicator(BaseModel):
    """주요 경제 지표"""

    name: str
    value: str
    change: Optional[str] = None
    description: Optional[str] = None


class CollectedData(BaseModel):
    """수집된 전체 데이터"""

    news: list[NewsArticle]
    markets: list[MarketData]
    watchlist: list[WatchlistItem]
    indicators: list[EconomicIndicator]
    collected_at: str


class BriefingResult(BaseModel):
    """AI 브리핑 결과"""

    type: Literal["morning", "evening", "alert", "on-demand"]
    content: str
    highlights: list[str]
    sentiment: Literal["bullish", "bearish", "neutral"]
    generated_at: str
