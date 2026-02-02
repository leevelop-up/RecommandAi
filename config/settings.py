from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # MariaDB 설정
    MARIADB_HOST: str = Field(default="localhost")
    MARIADB_PORT: int = Field(default=3306)
    MARIADB_USER: str = Field(default="root")
    MARIADB_PASSWORD: str = Field(default="")
    MARIADB_DATABASE: str = Field(default="recommandstock")

    @property
    def MARIADB_URL(self) -> str:
        return f"mysql+pymysql://{self.MARIADB_USER}:{self.MARIADB_PASSWORD}@{self.MARIADB_HOST}:{self.MARIADB_PORT}/{self.MARIADB_DATABASE}"

    # Redis 설정
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)

    # OpenAI API (벡터화용)
    OPENAI_API_KEY: Optional[str] = Field(default=None)

    # Google Gemini API (AI 추천용 - Free tier)
    GEMINI_API_KEY: Optional[str] = Field(default=None)

    # xAI (Grok) API
    XAI_API_KEY: Optional[str] = Field(default=None)

    # Groq API (초고속 무료 AI)
    GROQ_API_KEY: Optional[str] = Field(default=None)

    # AI 엔진 선택 (gemini, xai, groq)
    AI_ENGINE: str = Field(default="gemini", description="AI 엔진 선택: gemini, xai(grok), 또는 groq")

    # Alpha Vantage API (미국 주식)
    ALPHA_VANTAGE_API_KEY: Optional[str] = Field(default=None)

    # 네이버 API (뉴스 검색)
    NAVER_CLIENT_ID: Optional[str] = Field(default=None)
    NAVER_CLIENT_SECRET: Optional[str] = Field(default=None)

    # 스크래핑 설정
    SCRAPE_DELAY: float = Field(default=1.0, description="스크래핑 간 딜레이(초)")
    REQUEST_TIMEOUT: int = Field(default=30, description="요청 타임아웃(초)")

    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FILE: str = Field(default="logs/recommandai.log")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
