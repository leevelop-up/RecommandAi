"""
데이터베이스 유틸리티 (MariaDB, Redis)
"""
import json
from typing import Optional, Any, List
from datetime import datetime, timedelta
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import redis
from loguru import logger

from config import get_settings
from models import Base


settings = get_settings()


# ==================== MariaDB ====================

class MariaDBClient:
    """MariaDB 데이터베이스 클라이언트"""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """엔진 및 세션 팩토리 초기화"""
        try:
            self._engine = create_engine(
                settings.MARIADB_URL,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False,
            )
            self._session_factory = sessionmaker(
                bind=self._engine,
                autocommit=False,
                autoflush=False,
            )
            logger.info("MariaDB 연결 초기화 완료")
        except Exception as e:
            logger.error(f"MariaDB 연결 실패: {e}")
            raise

    def create_tables(self):
        """테이블 생성"""
        try:
            Base.metadata.create_all(self._engine)
            logger.info("테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {e}")
            raise

    @contextmanager
    def get_session(self):
        """세션 컨텍스트 매니저"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"DB 트랜잭션 실패: {e}")
            raise
        finally:
            session.close()

    def get_session_direct(self) -> Session:
        """직접 세션 반환 (수동 관리 필요)"""
        return self._session_factory()


# ==================== Redis ====================

class RedisClient:
    """Redis 클라이언트 (캐시 및 실시간 데이터)"""

    _instance = None
    _client = None

    # 키 프리픽스
    PREFIX_REALTIME = "stock:realtime:"
    PREFIX_NEWS = "stock:news:"
    PREFIX_INDEX = "market:index:"
    PREFIX_TOP = "market:top:"

    # TTL (초)
    TTL_REALTIME = 60  # 1분
    TTL_NEWS = 3600  # 1시간
    TTL_INDEX = 300  # 5분
    TTL_TOP = 300  # 5분

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Redis 클라이언트 초기화"""
        try:
            self._client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
            # 연결 테스트
            self._client.ping()
            logger.info("Redis 연결 초기화 완료")
        except Exception as e:
            logger.error(f"Redis 연결 실패: {e}")
            raise

    @property
    def client(self) -> redis.Redis:
        return self._client

    # ==================== 실시간 주가 ====================

    def set_realtime_price(self, ticker: str, data: dict, ttl: int = None):
        """실시간 주가 저장"""
        key = f"{self.PREFIX_REALTIME}{ticker}"
        data["updated_at"] = datetime.now().isoformat()
        self._client.setex(
            key,
            ttl or self.TTL_REALTIME,
            json.dumps(data, ensure_ascii=False),
        )

    def get_realtime_price(self, ticker: str) -> Optional[dict]:
        """실시간 주가 조회"""
        key = f"{self.PREFIX_REALTIME}{ticker}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    def get_realtime_prices(self, tickers: List[str]) -> dict:
        """여러 종목 실시간 주가 조회"""
        pipe = self._client.pipeline()
        for ticker in tickers:
            pipe.get(f"{self.PREFIX_REALTIME}{ticker}")
        results = pipe.execute()

        return {
            ticker: json.loads(data) if data else None
            for ticker, data in zip(tickers, results)
        }

    # ==================== 뉴스 캐시 ====================

    def set_news_cache(self, ticker: str, news_list: list, ttl: int = None):
        """뉴스 캐시 저장"""
        key = f"{self.PREFIX_NEWS}{ticker}"
        self._client.setex(
            key,
            ttl or self.TTL_NEWS,
            json.dumps(news_list, ensure_ascii=False),
        )

    def get_news_cache(self, ticker: str) -> Optional[list]:
        """뉴스 캐시 조회"""
        key = f"{self.PREFIX_NEWS}{ticker}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    # ==================== 시장 지수 ====================

    def set_market_index(self, index_code: str, data: dict, ttl: int = None):
        """시장 지수 저장"""
        key = f"{self.PREFIX_INDEX}{index_code}"
        data["updated_at"] = datetime.now().isoformat()
        self._client.setex(
            key,
            ttl or self.TTL_INDEX,
            json.dumps(data, ensure_ascii=False),
        )

    def get_market_index(self, index_code: str) -> Optional[dict]:
        """시장 지수 조회"""
        key = f"{self.PREFIX_INDEX}{index_code}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    # ==================== 상위 종목 ====================

    def set_top_stocks(self, category: str, stocks: list, ttl: int = None):
        """상위 종목 저장 (rise, fall, volume)"""
        key = f"{self.PREFIX_TOP}{category}"
        self._client.setex(
            key,
            ttl or self.TTL_TOP,
            json.dumps(stocks, ensure_ascii=False),
        )

    def get_top_stocks(self, category: str) -> Optional[list]:
        """상위 종목 조회"""
        key = f"{self.PREFIX_TOP}{category}"
        data = self._client.get(key)
        return json.loads(data) if data else None

    # ==================== 유틸리티 ====================

    def delete_pattern(self, pattern: str):
        """패턴에 맞는 키 삭제"""
        keys = self._client.keys(pattern)
        if keys:
            self._client.delete(*keys)

    def flush_cache(self, prefix: str = None):
        """캐시 삭제"""
        if prefix:
            self.delete_pattern(f"{prefix}*")
        else:
            self._client.flushdb()


# ==================== 전역 인스턴스 ====================

def get_mariadb() -> MariaDBClient:
    """MariaDB 클라이언트 인스턴스 반환"""
    return MariaDBClient()


def get_redis() -> RedisClient:
    """Redis 클라이언트 인스턴스 반환"""
    return RedisClient()
