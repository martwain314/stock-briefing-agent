"""
애플리케이션 환경 변수 설정

pydantic-settings를 사용하여 .env 파일에서 설정을 로드합니다.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class AppSettings(BaseSettings):
    """애플리케이션 전체 설정"""

    # API Keys
    gemini_api_key: str = Field(..., description="Google Gemini API Key")
    telegram_bot_token: str = Field(..., description="Telegram Bot Token")
    telegram_chat_id: str = Field(..., description="Telegram Chat ID")

    # 브리핑 스케줄
    morning_brief_time: str = Field(
        default="08:00", description="오전 브리핑 시간 (HH:MM)"
    )
    evening_brief_time: str = Field(
        default="18:00", description="저녁 브리핑 시간 (HH:MM)"
    )

    # 실시간 모니터링
    monitor_interval_minutes: int = Field(default=30, description="모니터링 간격 (분)")

    # 관심 종목
    watchlist: str = Field(
        default="KODEX 200,TIGER 나스닥100",
        description="관심 종목 목록 (콤마 구분)",
    )

    # 로그
    log_level: str = Field(default="INFO", description="로그 레벨")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_watchlist(self) -> list[str]:
        """관심 종목 리스트를 반환

        Returns:
            콤마로 구분된 관심 종목 문자열을 리스트로 변환하여 반환
        """
        return [item.strip() for item in self.watchlist.split(",")]

    def get_morning_hour_minute(self) -> tuple[int, int]:
        """오전 브리핑 시간을 (시, 분) 튜플로 반환

        Returns:
            (hour, minute) 형태의 튜플
        """
        parts = self.morning_brief_time.split(":")
        return int(parts[0]), int(parts[1])

    def get_evening_hour_minute(self) -> tuple[int, int]:
        """저녁 브리핑 시간을 (시, 분) 튜플로 반환

        Returns:
            (hour, minute) 형태의 튜플
        """
        parts = self.evening_brief_time.split(":")
        return int(parts[0]), int(parts[1])


def load_settings() -> AppSettings:
    """환경 변수에서 설정을 로드

    Returns:
        AppSettings 인스턴스

    Raises:
        ValidationError: 필수 환경 변수가 누락된 경우
    """
    return AppSettings()
