"""
데이터베이스 연결
"""
import pymysql
from contextlib import contextmanager
from config.settings import get_settings
from loguru import logger

settings = get_settings()


def get_db_connection():
    """DB 연결 생성"""
    return pymysql.connect(
        host=settings.MARIADB_HOST,
        port=settings.MARIADB_PORT,
        user=settings.MARIADB_USER,
        password=settings.MARIADB_PASSWORD,
        database=settings.MARIADB_DATABASE,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


@contextmanager
def get_db():
    """DB 연결 컨텍스트 매니저"""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def test_connection():
    """DB 연결 테스트"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            logger.info("✅ DB 연결 성공")
            return True
    except Exception as e:
        logger.error(f"❌ DB 연결 실패: {e}")
        return False
