"""
AI 분석 결과를 데이터베이스에 저장
"""
import json
from pathlib import Path
from datetime import datetime
from loguru import logger
import pymysql
import os


def get_latest_ai_result() -> dict:
    """output/ai/에서 가장 최근 JSON 파일 로드"""
    ai_dir = Path("output/ai")

    if not ai_dir.exists():
        raise FileNotFoundError(f"{ai_dir} 디렉토리가 없습니다")

    json_files = list(ai_dir.glob("weekly_recommendation_*.json"))

    if not json_files:
        raise FileNotFoundError(f"{ai_dir}에 JSON 파일이 없습니다")

    # 가장 최근 파일
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"✅ {latest_file.name} 로드 완료")
    return data


def save_to_database(ai_result: dict):
    """AI 분석 결과를 DB에 저장"""
    try:
        # DB 연결
        conn = pymysql.connect(
            host=os.getenv("MARIADB_HOST", "localhost"),
            port=int(os.getenv("MARIADB_PORT", 3306)),
            user=os.getenv("MARIADB_USER", "root"),
            password=os.getenv("MARIADB_PASSWORD", ""),
            database=os.getenv("MARIADB_DATABASE", "recommandstock"),
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        # 1. 기존 데이터 비활성화 (오늘 날짜가 아닌 것)
        today = datetime.now().date()
        cursor.execute("""
            UPDATE themes
            SET is_active = FALSE
            WHERE DATE(created_at) != %s
        """, (today,))

        # 2. 테마 저장
        themes_data = ai_result.get("themes", [])
        theme_id_map = {}  # 테마명 -> DB ID 매핑

        for theme in themes_data:
            theme_name = theme.get("theme_name", "")
            theme_score = theme.get("theme_score", 0)
            theme_summary = theme.get("theme_summary", "")

            # 테마 INSERT or UPDATE
            cursor.execute("""
                INSERT INTO themes (theme_name, theme_score, theme_summary, is_active, created_at)
                VALUES (%s, %s, %s, TRUE, NOW())
                ON DUPLICATE KEY UPDATE
                    theme_score = VALUES(theme_score),
                    theme_summary = VALUES(theme_summary),
                    is_active = TRUE,
                    created_at = NOW()
            """, (theme_name, theme_score, theme_summary))

            # 방금 INSERT/UPDATE한 테마 ID 가져오기
            cursor.execute("SELECT id FROM themes WHERE theme_name = %s", (theme_name,))
            theme_id = cursor.fetchone()[0]
            theme_id_map[theme_name] = theme_id

            logger.info(f"  테마 저장: {theme_name} (ID: {theme_id}, 점수: {theme_score})")

        # 3. 종목 저장
        for theme in themes_data:
            theme_name = theme.get("theme_name", "")
            theme_id = theme_id_map.get(theme_name)

            if not theme_id:
                continue

            # 이 테마의 기존 종목 삭제
            cursor.execute("DELETE FROM theme_stocks WHERE theme_id = %s", (theme_id,))

            stocks = theme.get("stocks", [])
            for stock in stocks:
                stock_code = stock.get("stock_code", "")
                stock_name = stock.get("stock_name", "")
                stock_price = stock.get("stock_price", 0)
                stock_change_rate = stock.get("stock_change_rate", "")
                tier = stock.get("tier", 3)

                cursor.execute("""
                    INSERT INTO theme_stocks (theme_id, stock_code, stock_name, stock_price, stock_change_rate, tier)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (theme_id, stock_code, stock_name, stock_price, stock_change_rate, tier))

            logger.info(f"  종목 저장: {theme_name} - {len(stocks)}개")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ DB 저장 완료: {len(themes_data)}개 테마")
        return True

    except Exception as e:
        logger.error(f"❌ DB 저장 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """메인 실행"""
    logger.info("[DB 저장] 시작")

    # 최신 AI 결과 로드
    ai_result = get_latest_ai_result()

    # DB에 저장
    save_to_database(ai_result)

    logger.info("[DB 저장] 완료")


if __name__ == "__main__":
    main()
