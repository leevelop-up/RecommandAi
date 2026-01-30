"""
주식 데이터 모델 (SQLAlchemy)
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    DateTime,
    Text,
    Date,
    Index,
    Enum,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Stock(Base):
    """종목 기본 정보"""

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    market = Column(String(20), nullable=False)  # KOSPI, KOSDAQ, NYSE, NASDAQ
    country = Column(String(10), default="KR")  # KR, US
    sector = Column(String(100))
    industry = Column(String(100))
    description = Column(Text)
    website = Column(String(255))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_stock_market", "market"),
        Index("idx_stock_country", "country"),
    )


class StockPrice(Base):
    """주가 데이터 (일봉)"""

    __tablename__ = "stock_prices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(BigInteger)
    high = Column(BigInteger)
    low = Column(BigInteger)
    close = Column(BigInteger, nullable=False)
    volume = Column(BigInteger)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_price_ticker_date", "ticker", "date", unique=True),
    )


class StockRealtime(Base):
    """실시간 주가 (Redis 캐시용 백업)"""

    __tablename__ = "stock_realtime"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    current_price = Column(BigInteger, nullable=False)
    change = Column(BigInteger)
    change_rate = Column(Float)
    open = Column(BigInteger)
    high = Column(BigInteger)
    low = Column(BigInteger)
    volume = Column(BigInteger)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_realtime_ticker", "ticker"),
    )


class StockFundamental(Base):
    """펀더멘탈 데이터"""

    __tablename__ = "stock_fundamentals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)

    # 시가총액
    market_cap = Column(BigInteger)
    shares = Column(BigInteger)

    # 밸류에이션
    per = Column(Float)
    pbr = Column(Float)
    psr = Column(Float)
    peg = Column(Float)

    # 수익성
    eps = Column(Float)
    bps = Column(Float)
    roe = Column(Float)
    roa = Column(Float)

    # 배당
    dividend_yield = Column(Float)
    dividend_rate = Column(Float)

    # 기타
    beta = Column(Float)
    fifty_two_week_high = Column(BigInteger)
    fifty_two_week_low = Column(BigInteger)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_fundamental_ticker_date", "ticker", "date", unique=True),
    )


class StockNews(Base):
    """주식 뉴스"""

    __tablename__ = "stock_news"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), index=True)  # NULL이면 시장 전체 뉴스
    title = Column(String(500), nullable=False)
    description = Column(Text)
    link = Column(String(1000))
    source = Column(String(100))
    published_at = Column(DateTime)
    sentiment = Column(Float)  # -1 ~ 1 (부정 ~ 긍정)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_news_ticker", "ticker"),
        Index("idx_news_published", "published_at"),
    )


class MarketIndex(Base):
    """시장 지수"""

    __tablename__ = "market_indices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    index_code = Column(String(20), nullable=False)  # KOSPI, KOSDAQ, SPX, DJI, IXIC
    name = Column(String(100))
    date = Column(Date, nullable=False)
    value = Column(Float, nullable=False)
    change = Column(Float)
    change_rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_index_code_date", "index_code", "date", unique=True),
    )


class InvestorTrading(Base):
    """투자자별 매매동향"""

    __tablename__ = "investor_trading"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, index=True)
    date = Column(Date, nullable=False)
    foreign_net = Column(BigInteger)  # 외국인 순매수
    institution_net = Column(BigInteger)  # 기관 순매수
    individual_net = Column(BigInteger)  # 개인 순매수
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_investor_ticker_date", "ticker", "date", unique=True),
    )
