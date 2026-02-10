"""
JSON 데이터를 MariaDB에 삽입하는 스크립트

실행 방법:
    python database/insert_data.py
    python database/insert_data.py --clear  # 기존 데이터 삭제 후 삽입
"""
import sys
import os
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 프로젝트 루트 경로 추가
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import pymysql
from loguru import logger
from config.settings import get_settings


class DataInserter:
    """JSON 데이터 → DB 삽입"""

    def __init__(self):
        self.settings = get_settings()
        self.connection = None
        self.cursor = None

    def connect(self):
        """DB 연결"""
        try:
            self.connection = pymysql.connect(
                host=self.settings.MARIADB_HOST,
                port=self.settings.MARIADB_PORT,
                user=self.settings.MARIADB_USER,
                password=self.settings.MARIADB_PASSWORD,
                database=self.settings.MARIADB_DATABASE,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.connection.cursor()
            logger.info(f"✅ DB 연결 성공: {self.settings.MARIADB_HOST}:{self.settings.MARIADB_PORT}")
            return True
        except Exception as e:
            logger.error(f"❌ DB 연결 실패: {e}")
            return False

    def disconnect(self):
        """DB 연결 해제"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("DB 연결 종료")

    def clear_tables(self):
        """기존 데이터 삭제"""
        try:
            logger.warning("⚠️  기존 데이터 삭제 중...")

            # 외래키 체크 비활성화
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            # 테이블 삭제 (역순)
            tables = ['return_history', 'news', 'theme_stocks', 'stocks', 'themes']
            for table in tables:
                self.cursor.execute(f"TRUNCATE TABLE {table}")
                logger.info(f"  ✅ {table} 테이블 초기화")

            # 외래키 체크 활성화
            self.cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            self.connection.commit()
            logger.info("✅ 모든 테이블 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"❌ 테이블 초기화 실패: {e}")
            self.connection.rollback()
            return False

    def parse_change_rate(self, rate_str: str) -> float:
        """등락률 문자열 → float 변환"""
        try:
            # "+5.2%", "-3.1%" → 5.2, -3.1
            nums = re.findall(r'-?\d+\.?\d*', str(rate_str))
            return float(nums[0]) if nums else 0.0
        except Exception:
            return 0.0

    def insert_themes(self, themes_data: Dict) -> Dict[str, int]:
        """테마 데이터 삽입"""
        logger.info("\n[1/5] 테마 데이터 삽입 중...")

        theme_id_map = {}  # theme_code → id 매핑
        themes = themes_data.get('themes', [])

        # 중복 제거: theme_code 기준으로 첫 번째 항목만 사용
        seen_codes = set()
        unique_themes = []
        duplicates = 0
        for theme in themes:
            code = theme.get('code')
            if code not in seen_codes:
                seen_codes.add(code)
                unique_themes.append(theme)
            else:
                duplicates += 1

        logger.info(f"  전체 테마: {len(themes)}개, 중복 제거: {duplicates}개, 유니크: {len(unique_themes)}개")

        sql = """
        INSERT INTO themes (
            theme_code, theme_name, stock_count, theme_score,
            change_rate, daily_change, news_count, rank, is_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        inserted = 0
        for theme in unique_themes:
            try:
                theme_code = theme.get('code')
                theme_name = theme.get('name')
                stock_count = theme.get('stock_count', 0)
                theme_score = theme.get('score', 0.0)
                change_rate = theme.get('change_rate', '0%')
                daily_change = self.parse_change_rate(change_rate)
                news_count = len(theme.get('news', []))
                rank = theme.get('rank', 0)

                self.cursor.execute(sql, (
                    theme_code, theme_name, stock_count, theme_score,
                    change_rate, daily_change, news_count, rank, True
                ))

                # theme_code → id 매핑 저장
                theme_id_map[theme_code] = self.cursor.lastrowid
                inserted += 1

                if inserted % 100 == 0:
                    logger.info(f"  진행: {inserted}/{len(unique_themes)} 테마")

            except Exception as e:
                logger.error(f"  테마 삽입 실패 ({theme_name}): {e}")

        self.connection.commit()
        logger.info(f"✅ 테마 삽입 완료: {inserted}개")
        return theme_id_map

    def insert_stocks(self, stocks_data: Dict, themes_data: Dict) -> Dict[str, str]:
        """종목 데이터 삽입 (기존 스키마: ticker, kr_name, en_name, sector, market)"""
        logger.info("\n[2/5] 종목 데이터 삽입 중...")

        stock_ticker_set = set()  # ticker 중복 체크용

        # 기존 테이블 스키마에 맞춤: ticker(PK), kr_name, en_name, sector, market
        sql = """
        INSERT INTO stocks (
            ticker, kr_name, en_name, sector, market
        ) VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            kr_name = VALUES(kr_name),
            en_name = VALUES(en_name),
            sector = VALUES(sector),
            market = VALUES(market),
            updated_at = CURRENT_TIMESTAMP
        """

        inserted = 0

        # 1. rising_stocks.json에서 한국 종목
        korea_stocks = stocks_data.get('korea_stocks', [])
        for stock in korea_stocks:
            try:
                ticker = stock.get('ticker')
                kr_name = stock.get('name')

                if not ticker or ticker in stock_ticker_set:
                    continue

                self.cursor.execute(sql, (
                    ticker,
                    kr_name,
                    None,  # en_name
                    stock.get('sector', ''),
                    stock.get('market', 'KOSPI')
                ))

                stock_ticker_set.add(ticker)
                inserted += 1

            except Exception as e:
                logger.error(f"  종목 삽입 실패 ({kr_name}): {e}")

        # 2. rising_stocks.json에서 미국 종목
        usa_stocks = stocks_data.get('usa_stocks', [])
        for stock in usa_stocks:
            try:
                ticker = stock.get('ticker')
                en_name = stock.get('name')

                if not ticker or ticker in stock_ticker_set:
                    continue

                # kr_name이 NOT NULL이므로 빈 문자열 또는 en_name 사용
                self.cursor.execute(sql, (
                    ticker,
                    en_name,  # kr_name (NOT NULL이므로 en_name 사용)
                    en_name,
                    stock.get('sector', ''),
                    'NYSE'
                ))

                stock_ticker_set.add(ticker)
                inserted += 1

            except Exception as e:
                logger.error(f"  종목 삽입 실패 ({en_name}): {e}")

        # 3. rising_themes.json에서 테마 관련주 (중복 제거)
        seen_codes = set()
        themes = themes_data.get('themes', [])
        for theme in themes:
            for tier_key in ['tier1_stocks', 'tier2_stocks', 'tier3_stocks']:
                for stock in theme.get(tier_key, []):
                    try:
                        ticker = stock.get('ticker') or stock.get('code')
                        kr_name = stock.get('name')

                        if not ticker or ticker in stock_ticker_set:
                            continue

                        self.cursor.execute(sql, (
                            ticker,
                            kr_name,
                            None,
                            '',
                            'KOSPI'
                        ))

                        stock_ticker_set.add(ticker)
                        inserted += 1

                    except Exception as e:
                        logger.error(f"  테마 관련주 삽입 실패 ({kr_name}): {e}")

        self.connection.commit()
        logger.info(f"✅ 종목 삽입 완료: {inserted}개")
        return stock_ticker_set

    def insert_theme_stocks(self, themes_data: Dict, theme_id_map: Dict, stock_ticker_set: set):
        """테마-종목 연결 데이터 삽입"""
        logger.info("\n[3/5] 테마-종목 연결 데이터 삽입 중...")

        sql = """
        INSERT INTO theme_stocks (
            theme_id, stock_id, stock_code, stock_name, tier,
            stock_price, stock_change_rate
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        inserted = 0
        skipped = 0
        stock_id_counter = 1  # stock_id를 순차적으로 증가시킴

        # 중복 제거를 위한 theme_code 필터
        seen_codes = set()
        unique_themes = []
        for theme in themes_data.get('themes', []):
            code = theme.get('code')
            if code not in seen_codes:
                seen_codes.add(code)
                unique_themes.append(theme)

        for theme in unique_themes:
            theme_code = theme.get('code')
            theme_id = theme_id_map.get(theme_code)

            if not theme_id:
                continue

            tier_map = {
                'tier1_stocks': 1,
                'tier2_stocks': 2,
                'tier3_stocks': 3,
            }

            for tier_key, tier_num in tier_map.items():
                for stock in theme.get(tier_key, []):
                    try:
                        stock_code = stock.get('ticker') or stock.get('code')
                        stock_name = stock.get('name')

                        if not stock_code:
                            continue

                        # stock_code가 stocks 테이블에 있는지 확인
                        if stock_code not in stock_ticker_set:
                            skipped += 1
                            continue

                        # stock_id는 순차적으로 증가하는 값 사용 (UNIQUE 제약 회피)
                        self.cursor.execute(sql, (
                            theme_id, stock_id_counter, stock_code, stock_name, tier_num,
                            stock.get('price', 0), stock.get('change_rate', '0%')
                        ))

                        stock_id_counter += 1
                        inserted += 1

                    except pymysql.IntegrityError as e:
                        # 중복 데이터 무시
                        logger.debug(f"  중복 스킵: {stock_name} - {e}")
                    except Exception as e:
                        logger.error(f"  연결 데이터 삽입 실패 ({stock_name}): {e}")

        self.connection.commit()
        logger.info(f"✅ 테마-종목 연결 완료: {inserted}개 (스킵: {skipped}개)")

    def insert_news(self, news_data: Dict, themes_data: Dict, theme_id_map: Dict, stock_id_map: Dict):
        """뉴스 데이터 삽입 (기존 스키마에 맞춤)"""
        logger.info("\n[4/5] 뉴스 데이터 삽입 중...")

        # 기존 테이블 스키마: title, description, link, source, published, ticker
        sql = """
        INSERT INTO news (
            title, link, source, description, published, ticker
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        inserted = 0

        # 1. 일반 뉴스
        articles = news_data.get('articles', [])
        for article in articles[:100]:  # 최대 100개만
            try:
                link = article.get('link', '')
                # link 컬럼이 VARCHAR(500)이므로 500자로 제한
                if len(link) > 500:
                    link = link[:500]

                self.cursor.execute(sql, (
                    article.get('title'),
                    link,
                    article.get('source') or article.get('_source'),
                    article.get('description', ''),
                    None,  # published
                    None   # ticker
                ))
                inserted += 1
            except pymysql.IntegrityError:
                # 중복 링크 무시
                pass
            except Exception as e:
                logger.error(f"  뉴스 삽입 실패: {e}")

        # 2. 테마별 뉴스 (ticker는 해당 테마의 대표 종목 코드 사용)
        themes = themes_data.get('themes', [])
        for theme in themes:
            theme_code = theme.get('code')

            # 해당 테마의 1차 관련주 중 첫 번째 종목 코드 가져오기
            tier1_stocks = theme.get('tier1_stocks', [])
            ticker = None
            if tier1_stocks:
                ticker = tier1_stocks[0].get('ticker') or tier1_stocks[0].get('code')

            for news_item in theme.get('news', [])[:5]:  # 테마당 최대 5개
                try:
                    link = news_item.get('link', '')
                    # link 컬럼이 VARCHAR(500)이므로 500자로 제한
                    if len(link) > 500:
                        link = link[:500]

                    self.cursor.execute(sql, (
                        news_item.get('title'),
                        link,
                        'Google News',
                        news_item.get('description', ''),
                        None,
                        ticker
                    ))
                    inserted += 1
                except pymysql.IntegrityError:
                    pass
                except Exception as e:
                    logger.error(f"  테마 뉴스 삽입 실패: {e}")

        self.connection.commit()
        logger.info(f"✅ 뉴스 삽입 완료: {inserted}개")

    def run(self, clear_first: bool = False):
        """전체 프로세스 실행"""
        logger.info("=" * 70)
        logger.info("  JSON 데이터 → DB 삽입 시작")
        logger.info("=" * 70)

        # DB 연결
        if not self.connect():
            return False

        try:
            # 기존 데이터 삭제 (옵션)
            if clear_first:
                if not self.clear_tables():
                    return False

            # JSON 파일 로드
            scrap_dir = Path(ROOT_DIR) / "output" / "scrap"

            logger.info("\n📂 JSON 파일 로드 중...")
            with open(scrap_dir / "rising_themes.json", "r", encoding="utf-8") as f:
                themes_data = json.load(f)
            logger.info(f"  ✅ rising_themes.json: {len(themes_data.get('themes', []))}개 테마")

            with open(scrap_dir / "rising_stocks.json", "r", encoding="utf-8") as f:
                stocks_data = json.load(f)
            logger.info(f"  ✅ rising_stocks.json: 한국 {len(stocks_data.get('korea_stocks', []))}개, 미국 {len(stocks_data.get('usa_stocks', []))}개")

            with open(scrap_dir / "news_summary.json", "r", encoding="utf-8") as f:
                news_data = json.load(f)
            logger.info(f"  ✅ news_summary.json: {news_data.get('total_count', 0)}개 기사")

            # 데이터 삽입
            theme_id_map = self.insert_themes(themes_data)
            stock_ticker_set = self.insert_stocks(stocks_data, themes_data)
            self.insert_theme_stocks(themes_data, theme_id_map, stock_ticker_set)
            self.insert_news(news_data, themes_data, theme_id_map, stock_ticker_set)

            logger.info("\n" + "=" * 70)
            logger.info("  ✅ 모든 데이터 삽입 완료!")
            logger.info("=" * 70)

            # 통계 출력
            self.print_statistics()

            return True

        except Exception as e:
            logger.error(f"❌ 데이터 삽입 중 오류 발생: {e}")
            self.connection.rollback()
            return False
        finally:
            self.disconnect()

    def print_statistics(self):
        """DB 통계 출력"""
        try:
            stats = []

            self.cursor.execute("SELECT COUNT(*) as cnt FROM themes")
            stats.append(f"테마: {self.cursor.fetchone()['cnt']}개")

            self.cursor.execute("SELECT COUNT(*) as cnt FROM stocks")
            stats.append(f"종목: {self.cursor.fetchone()['cnt']}개")

            self.cursor.execute("SELECT COUNT(*) as cnt FROM theme_stocks")
            stats.append(f"테마-종목 연결: {self.cursor.fetchone()['cnt']}개")

            self.cursor.execute("SELECT COUNT(*) as cnt FROM news")
            stats.append(f"뉴스: {self.cursor.fetchone()['cnt']}개")

            logger.info("\n📊 DB 통계:")
            for stat in stats:
                logger.info(f"  - {stat}")

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")


def setup_logger():
    """로거 설정"""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<7} | {message}"
    )


def main():
    parser = argparse.ArgumentParser(description="JSON 데이터를 DB에 삽입")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="기존 데이터를 삭제한 후 삽입"
    )
    args = parser.parse_args()

    setup_logger()

    inserter = DataInserter()
    success = inserter.run(clear_first=args.clear)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
