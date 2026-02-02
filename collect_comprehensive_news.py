"""
종합 뉴스 수집 자동화 프로그램
- 모든 뉴스 소스에서 데이터 수집
- MariaDB에 저장
- 텍스트 파일로 export
- AI 분석용 데이터 생성
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from pathlib import Path

from config import get_settings
from scrapers.news.comprehensive_news_scraper import ComprehensiveNewsScraper

# DB는 optional
try:
    from utils import get_mariadb
    from models import StockNews, Stock
    DB_AVAILABLE = True
except ImportError:
    logger.warning("DB 모듈을 불러올 수 없습니다. DB 저장 없이 실행됩니다.")
    DB_AVAILABLE = False


class NewsCollector:
    """뉴스 수집 및 저장 관리자"""

    def __init__(self):
        self.settings = get_settings()
        self.scraper = ComprehensiveNewsScraper(
            naver_client_id=self.settings.NAVER_CLIENT_ID,
            naver_client_secret=self.settings.NAVER_CLIENT_SECRET,
        )
        self.db = get_mariadb() if DB_AVAILABLE else None

    def collect_and_save_market_news(self) -> Dict:
        """시장 뉴스 수집 및 저장"""
        logger.info("=" * 80)
        logger.info("  시장 뉴스 수집 및 저장 시작")
        logger.info("=" * 80)

        # 1. 뉴스 수집
        news_data = self.scraper.collect_market_news()

        # 2. DB 저장
        saved_count = self._save_news_to_db(news_data, ticker=None)

        # 3. 텍스트 export
        text_file = self._export_to_text(news_data, "market_news")

        # 4. JSON 저장
        json_file = self._save_to_json(news_data, "market_news")

        result = {
            "type": "market_news",
            "total_collected": sum(len(news) for news in news_data["sources"].values()),
            "saved_to_db": saved_count,
            "text_file": text_file,
            "json_file": json_file,
        }

        logger.info(f"시장 뉴스 수집 완료: {result['total_collected']}개 수집, {saved_count}개 DB 저장")
        return result

    def collect_and_save_stock_news(self, ticker: str, stock_name: str) -> Dict:
        """종목 뉴스 수집 및 저장"""
        logger.info("=" * 80)
        logger.info(f"  종목 뉴스 수집: {stock_name}({ticker})")
        logger.info("=" * 80)

        # 1. 뉴스 수집
        news_data = self.scraper.collect_stock_news(ticker, stock_name)

        # 2. DB 저장
        saved_count = self._save_news_to_db(news_data, ticker=ticker)

        # 3. 텍스트 export
        text_file = self._export_to_text(news_data, f"stock_{ticker}_news")

        # 4. JSON 저장
        json_file = self._save_to_json(news_data, f"stock_{ticker}_news")

        result = {
            "type": "stock_news",
            "ticker": ticker,
            "stock_name": stock_name,
            "total_collected": sum(len(news) for news in news_data["sources"].values()),
            "saved_to_db": saved_count,
            "text_file": text_file,
            "json_file": json_file,
        }

        logger.info(f"종목 뉴스 수집 완료: {result['total_collected']}개 수집, {saved_count}개 DB 저장")
        return result

    def collect_and_save_keyword_news(self, keyword: str) -> Dict:
        """키워드 뉴스 수집 및 저장"""
        logger.info("=" * 80)
        logger.info(f"  키워드 뉴스 수집: '{keyword}'")
        logger.info("=" * 80)

        # 1. 뉴스 수집
        news_data = self.scraper.collect_all_news(keyword)

        # 2. DB 저장
        saved_count = self._save_news_to_db(news_data, ticker=None)

        # 3. 텍스트 export
        text_file = self._export_to_text(news_data, f"keyword_{keyword}_news")

        # 4. JSON 저장
        json_file = self._save_to_json(news_data, f"keyword_{keyword}_news")

        result = {
            "type": "keyword_news",
            "keyword": keyword,
            "total_collected": sum(len(news) for news in news_data["sources"].values()),
            "saved_to_db": saved_count,
            "text_file": text_file,
            "json_file": json_file,
        }

        logger.info(f"키워드 뉴스 수집 완료: {result['total_collected']}개 수집, {saved_count}개 DB 저장")
        return result

    def collect_all_active_stocks_news(self) -> Dict:
        """활성 종목 전체 뉴스 수집"""
        if not DB_AVAILABLE or not self.db:
            logger.error("DB를 사용할 수 없습니다. 전체 종목 수집을 건너뜁니다.")
            return {
                "type": "all_stocks_news",
                "stocks_count": 0,
                "total_collected": 0,
                "total_saved": 0,
                "results": [],
            }

        logger.info("=" * 80)
        logger.info("  전체 활성 종목 뉴스 수집 시작")
        logger.info("=" * 80)

        results = []
        total_collected = 0
        total_saved = 0

        with self.db.get_session() as session:
            # 한국 활성 종목 조회 (상위 30개)
            stocks = session.query(Stock).filter_by(country="KR", is_active=1).limit(30).all()

            for stock in stocks:
                try:
                    result = self.collect_and_save_stock_news(stock.ticker, stock.name)
                    results.append(result)
                    total_collected += result["total_collected"]
                    total_saved += result["saved_to_db"]
                except Exception as e:
                    logger.error(f"{stock.name}({stock.ticker}) 뉴스 수집 실패: {e}")

        logger.info(f"전체 종목 뉴스 수집 완료: {total_collected}개 수집, {total_saved}개 DB 저장")
        return {
            "type": "all_stocks_news",
            "stocks_count": len(results),
            "total_collected": total_collected,
            "total_saved": total_saved,
            "results": results,
        }

    def _save_news_to_db(self, news_data: Dict, ticker: Optional[str] = None) -> int:
        """뉴스 데이터를 DB에 저장"""
        if not DB_AVAILABLE or not self.db:
            logger.warning("DB를 사용할 수 없습니다. DB 저장을 건너뜁니다.")
            return 0

        saved_count = 0

        with self.db.get_session() as session:
            for source, news_list in news_data.get("sources", {}).items():
                for news in news_list:
                    # 중복 체크 (제목 기준)
                    existing = session.query(StockNews).filter_by(
                        title=news.get("title", "")
                    ).first()

                    if existing:
                        continue

                    # 발행일 파싱
                    published_at = self._parse_date(news.get("published", ""))

                    news_obj = StockNews(
                        ticker=ticker,
                        title=news.get("title", ""),
                        description=news.get("description", ""),
                        link=news.get("link", ""),
                        source=news.get("source", source),
                        published_at=published_at,
                    )

                    session.add(news_obj)
                    saved_count += 1

        logger.info(f"DB 저장 완료: {saved_count}개")
        return saved_count

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열 파싱"""
        if not date_str:
            return None

        # 다양한 형식 지원
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %Z",  # RSS 형식
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        return None

    def _export_to_text(self, news_data: Dict, filename: str) -> str:
        """뉴스를 텍스트 파일로 export"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{filename}_{timestamp}.txt"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"  뉴스 데이터 Export\n")
            f.write(f"  생성 시간: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

            total_count = 0
            for source, news_list in news_data.get("sources", {}).items():
                if not news_list:
                    continue

                f.write(f"\n[{source.upper()}] ({len(news_list)}개)\n")
                f.write("-" * 80 + "\n")

                for i, news in enumerate(news_list, 1):
                    total_count += 1
                    f.write(f"\n{i}. {news.get('title', '')}\n")

                    if news.get('description'):
                        f.write(f"   {news['description']}\n")

                    if news.get('source'):
                        f.write(f"   출처: {news['source']}\n")

                    if news.get('published'):
                        f.write(f"   발행: {news['published']}\n")

                    if news.get('link'):
                        f.write(f"   링크: {news['link']}\n")

                    f.write("\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write(f"  총 {total_count}개 뉴스\n")
            f.write("=" * 80 + "\n")

        logger.info(f"텍스트 파일 저장: {filepath}")
        return filepath

    def _save_to_json(self, news_data: Dict, filename: str) -> str:
        """뉴스를 JSON 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{filename}_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON 파일 저장: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="종합 뉴스 수집 프로그램")
    parser.add_argument("--market", action="store_true", help="시장 뉴스 수집")
    parser.add_argument("--stock", type=str, help="종목 코드 (예: 005930)")
    parser.add_argument("--stock-name", type=str, help="종목명 (예: 삼성전자)")
    parser.add_argument("--keyword", type=str, help="키워드 검색")
    parser.add_argument("--all-stocks", action="store_true", help="전체 활성 종목 뉴스 수집")

    args = parser.parse_args()

    collector = NewsCollector()

    if args.market:
        result = collector.collect_and_save_market_news()
        print(f"\n✅ 시장 뉴스 수집 완료")
        print(f"   - 수집: {result['total_collected']}개")
        print(f"   - DB 저장: {result['saved_to_db']}개")
        print(f"   - 텍스트: {result['text_file']}")
        print(f"   - JSON: {result['json_file']}")

    elif args.stock and args.stock_name:
        result = collector.collect_and_save_stock_news(args.stock, args.stock_name)
        print(f"\n✅ 종목 뉴스 수집 완료: {args.stock_name}({args.stock})")
        print(f"   - 수집: {result['total_collected']}개")
        print(f"   - DB 저장: {result['saved_to_db']}개")
        print(f"   - 텍스트: {result['text_file']}")
        print(f"   - JSON: {result['json_file']}")

    elif args.keyword:
        result = collector.collect_and_save_keyword_news(args.keyword)
        print(f"\n✅ 키워드 뉴스 수집 완료: '{args.keyword}'")
        print(f"   - 수집: {result['total_collected']}개")
        print(f"   - DB 저장: {result['saved_to_db']}개")
        print(f"   - 텍스트: {result['text_file']}")
        print(f"   - JSON: {result['json_file']}")

    elif args.all_stocks:
        result = collector.collect_all_active_stocks_news()
        print(f"\n✅ 전체 종목 뉴스 수집 완료")
        print(f"   - 종목 수: {result['stocks_count']}개")
        print(f"   - 수집: {result['total_collected']}개")
        print(f"   - DB 저장: {result['total_saved']}개")

    else:
        # 기본: 시장 뉴스
        result = collector.collect_and_save_market_news()
        print(f"\n✅ 시장 뉴스 수집 완료 (기본)")
        print(f"   - 수집: {result['total_collected']}개")
        print(f"   - DB 저장: {result['saved_to_db']}개")
        print(f"   - 텍스트: {result['text_file']}")
        print(f"   - JSON: {result['json_file']}")


if __name__ == "__main__":
    main()
