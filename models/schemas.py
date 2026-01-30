"""
Pydantic 스키마 (데이터 검증 및 직렬화)
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 주식 기본 정보 ====================

class StockBase(BaseModel):
    ticker: str
    name: str
    market: str
    country: str = "KR"


class StockCreate(StockBase):
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None


class StockResponse(StockBase):
    id: int
    sector: Optional[str] = None
    industry: Optional[str] = None
    is_active: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 주가 데이터 ====================

class StockPriceBase(BaseModel):
    ticker: str
    date: date
    open: Optional[int] = None
    high: Optional[int] = None
    low: Optional[int] = None
    close: int
    volume: Optional[int] = None
    change_rate: Optional[float] = None


class StockPriceCreate(StockPriceBase):
    pass


class StockPriceResponse(StockPriceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 실시간 주가 ====================

class StockRealtimeBase(BaseModel):
    ticker: str
    current_price: int
    change: Optional[int] = None
    change_rate: Optional[float] = None
    open: Optional[int] = None
    high: Optional[int] = None
    low: Optional[int] = None
    volume: Optional[int] = None


class StockRealtimeCreate(StockRealtimeBase):
    pass


class StockRealtimeResponse(StockRealtimeBase):
    name: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 펀더멘탈 ====================

class StockFundamentalBase(BaseModel):
    ticker: str
    date: date
    market_cap: Optional[int] = None
    shares: Optional[int] = None
    per: Optional[float] = None
    pbr: Optional[float] = None
    eps: Optional[float] = None
    bps: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    dividend_yield: Optional[float] = None


class StockFundamentalCreate(StockFundamentalBase):
    pass


class StockFundamentalResponse(StockFundamentalBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 뉴스 ====================

class StockNewsBase(BaseModel):
    ticker: Optional[str] = None
    title: str
    description: Optional[str] = None
    link: Optional[str] = None
    source: Optional[str] = None
    published_at: Optional[datetime] = None


class StockNewsCreate(StockNewsBase):
    sentiment: Optional[float] = None


class StockNewsResponse(StockNewsBase):
    id: int
    sentiment: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 시장 지수 ====================

class MarketIndexBase(BaseModel):
    index_code: str
    name: Optional[str] = None
    date: date
    value: float
    change: Optional[float] = None
    change_rate: Optional[float] = None


class MarketIndexCreate(MarketIndexBase):
    pass


class MarketIndexResponse(MarketIndexBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== 통합 응답 ====================

class StockDetailResponse(BaseModel):
    """종목 상세 정보 (통합)"""
    stock: StockResponse
    realtime: Optional[StockRealtimeResponse] = None
    fundamental: Optional[StockFundamentalResponse] = None
    recent_prices: List[StockPriceResponse] = []
    news: List[StockNewsResponse] = []


class MarketSummaryResponse(BaseModel):
    """시장 요약 정보"""
    indices: List[MarketIndexResponse] = []
    top_gainers: List[StockRealtimeResponse] = []
    top_losers: List[StockRealtimeResponse] = []
    most_active: List[StockRealtimeResponse] = []
    recent_news: List[StockNewsResponse] = []
