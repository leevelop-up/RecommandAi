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
        # AI 결과에서 Gemini 분석 추출
        gemini_data = ai_result.get("ai_recommendations", {}).get("gemini", {})
        themes_analysis = gemini_data.get("top_themes_analysis", [])
        top_picks = gemini_data.get("top_10_picks", [])

        theme_id_map = {}  # 테마명 -> DB ID 매핑

        for theme in themes_analysis:
            theme_name = theme.get("theme", "")
            # rating을 점수로 변환 (매우 강세=100, 강세=80, 중립=50 등)
            rating = theme.get("rating", "")
            theme_score = {"매우 강세": 100, "강세": 80, "중립": 50, "약세": 30}.get(rating, 70)

            # theme_code 생성 (테마명의 알파벳/숫자만 사용)
            import re
            theme_code = re.sub(r'[^a-zA-Z0-9가-힣]', '', theme_name)[:50]

            # 테마 INSERT or UPDATE
            cursor.execute("""
                INSERT INTO themes (theme_code, theme_name, theme_score, is_active, created_at)
                VALUES (%s, %s, %s, TRUE, NOW())
                ON DUPLICATE KEY UPDATE
                    theme_score = VALUES(theme_score),
                    is_active = TRUE,
                    updated_at = NOW()
            """, (theme_code, theme_name, theme_score))

            # 방금 INSERT/UPDATE한 테마 ID 가져오기
            cursor.execute("SELECT id FROM themes WHERE theme_name = %s", (theme_name,))
            theme_id = cursor.fetchone()[0]
            theme_id_map[theme_name] = theme_id

            logger.info(f"  테마 저장: {theme_name} (ID: {theme_id}, 점수: {theme_score})")

        # 3. 종목 저장
        for theme in themes_analysis:
            theme_name = theme.get("theme", "")
            theme_id = theme_id_map.get(theme_name)

            if not theme_id:
                continue

            # 이 테마의 기존 종목 삭제
            cursor.execute("DELETE FROM theme_stocks WHERE theme_id = %s", (theme_id,))

            # recommended_stocks에서 종목 정보 가져오기
            recommended_stocks = theme.get("recommended_stocks", [])

            for stock_name in recommended_stocks:
                # top_10_picks에서 상세 정보 찾기
                stock_detail = None
                for pick in top_picks:
                    if pick.get("name") == stock_name:
                        stock_detail = pick
                        break

                if stock_detail:
                    stock_code = stock_detail.get("ticker", "")
                    stock_price = float(stock_detail.get("entry_price", "0").replace(",", ""))
                    target_return = stock_detail.get("target_return", "0%")
                    tier = 1 if stock_detail.get("rank", 999) <= 3 else 2
                else:
                    # 상세 정보 없으면 기본값
                    stock_code = ""
                    stock_price = 0
                    target_return = ""
                    tier = 3

                # stock_code로 stocks 테이블 확인
                cursor.execute("SELECT ticker FROM stocks WHERE ticker = %s", (stock_code,))
                stock_exists = cursor.fetchone()

                if stock_code and stock_exists:
                    # ticker를 숫자 ID로 변환 (해시)
                    stock_id = abs(hash(stock_code)) % (10 ** 18)  # bigint(20) 범위 내

                    cursor.execute("""
                        INSERT INTO theme_stocks (theme_id, stock_id, stock_code, stock_name, stock_price, stock_change_rate, tier)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (theme_id, stock_id, stock_code, stock_name, stock_price, target_return, tier))
                else:
                    logger.warning(f"  ⚠️ {stock_name} ({stock_code}) - stocks 테이블에 없거나 코드 없음, 건너뜀")

            logger.info(f"  종목 저장: {theme_name} - {len(recommended_stocks)}개")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"✅ DB 저장 완료: {len(themes_analysis)}개 테마")
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
