"""
데이터베이스 모델 (Pydantic)
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class Stock(BaseModel):
    """종목 정보"""
    ticker: str
    kr_name: Optional[str] = None
    en_name: Optional[str] = None
    sector: Optional[str] = None
    market: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Theme(BaseModel):
    """테마 정보"""
    id: int
    theme_code: str
    theme_name: str
    stock_count: int = 0
    theme_score: float = 0.0
    change_rate: Optional[str] = None
    daily_change: float = 0.0
    avg_return_rate: float = 0.0
    news_count: int = 0
    rank: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ThemeStock(BaseModel):
    """테마-종목 연결"""
    id: int
    theme_id: int
    stock_id: int
    stock_code: str
    stock_name: str
    tier: int
    stock_price: float = 0.0
    stock_change_rate: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NewsItem(BaseModel):
    """뉴스 정보"""
    id: int
    title: str
    description: Optional[str] = None
    link: str
    source: Optional[str] = None
    published: Optional[datetime] = None
    ticker: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ThemeDetail(Theme):
    """테마 상세 (관련주 포함)"""
    tier1_stocks: List[ThemeStock] = []
    tier2_stocks: List[ThemeStock] = []
    tier3_stocks: List[ThemeStock] = []
    news: List[NewsItem] = []


class ThemesResponse(BaseModel):
    """테마 목록 응답"""
    themes: List[Theme]
    total: int


class NewsResponse(BaseModel):
    """뉴스 목록 응답"""
    news: List[NewsItem]
    total_count: int
    collected_at: str
