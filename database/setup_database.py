"""
나스 서버에 데이터베이스 테이블을 생성하는 스크립트

실행 방법:
    python database/setup_database.py
"""
import sys
import os

# 프로젝트 루트 경로 추가
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import pymysql
from loguru import logger
from config.settings import get_settings


def setup_logger():
    """로거 설정"""
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<7} | {message}"
    )


def create_tables():
    """테이블 생성"""
    settings = get_settings()

    logger.info("=" * 70)
    logger.info("  데이터베이스 테이블 생성")
    logger.info("=" * 70)
    logger.info(f"\n📡 연결 정보:")
    logger.info(f"  Host: {settings.MARIADB_HOST}:{settings.MARIADB_PORT}")
    logger.info(f"  Database: {settings.MARIADB_DATABASE}")
    logger.info(f"  User: {settings.MARIADB_USER}")

    try:
        # DB 연결
        connection = pymysql.connect(
            host=settings.MARIADB_HOST,
            port=settings.MARIADB_PORT,
            user=settings.MARIADB_USER,
            password=settings.MARIADB_PASSWORD,
            database=settings.MARIADB_DATABASE,
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        logger.info("\n✅ DB 연결 성공")

        # SQL 파일 읽기
        sql_file = os.path.join(ROOT_DIR, "database", "create_tables.sql")

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # SQL 문 분리 및 실행
        sql_commands = sql_content.split(';')

        logger.info("\n🔨 테이블 생성 중...\n")

        for i, command in enumerate(sql_commands, 1):
            command = command.strip()

            # 빈 명령이나 주석만 있는 경우 스킵
            if not command or command.startswith('--'):
                continue

            try:
                # CREATE TABLE, CREATE VIEW 명령어 추출
                if 'CREATE TABLE' in command.upper():
                    table_match = command.upper().split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()
                    logger.info(f"  [{i}] 테이블 생성: {table_match}")
                elif 'CREATE OR REPLACE VIEW' in command.upper():
                    view_match = command.upper().split('CREATE OR REPLACE VIEW')[1].split('AS')[0].strip()
                    logger.info(f"  [{i}] 뷰 생성: {view_match}")

                cursor.execute(command)

            except pymysql.Error as e:
                if 'already exists' in str(e).lower():
                    logger.warning(f"    ⚠️  이미 존재함 (스킵)")
                else:
                    logger.error(f"    ❌ 오류: {e}")

        connection.commit()

        logger.info("\n✅ 모든 테이블 생성 완료!")

        # 생성된 테이블 확인
        logger.info("\n📊 생성된 테이블 목록:")
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table[0]}")
            count = cursor.fetchone()[0]
            logger.info(f"  - {table[0]}: {count}개 레코드")

        cursor.close()
        connection.close()

        logger.info("\n" + "=" * 70)
        logger.info("  완료! 이제 데이터를 삽입할 수 있습니다.")
        logger.info("  실행: python database/insert_data.py --clear")
        logger.info("=" * 70)

        return True

    except pymysql.Error as e:
        logger.error(f"\n❌ DB 오류: {e}")
        return False
    except FileNotFoundError:
        logger.error(f"\n❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    except Exception as e:
        logger.error(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    setup_logger()

    success = create_tables()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
