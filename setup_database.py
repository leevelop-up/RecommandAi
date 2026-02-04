"""
기존 MariaDB에 recommandstock 데이터베이스와 테이블 생성
"""
import pymysql
from pathlib import Path
from loguru import logger

# 접속 정보
DB_CONFIG = {
    'host': 'leevelop.com',
    'port': 2906,
    'user': 'merong2969',
    'password': 'Seung0075!',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def setup_database():
    """데이터베이스와 테이블 생성"""
    logger.info("=" * 60)
    logger.info("MariaDB 데이터베이스 설정 시작")
    logger.info("=" * 60)

    try:
        # 1. MariaDB 접속 (데이터베이스 지정 없이)
        logger.info(f"MariaDB 접속 중... {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 2. 데이터베이스 생성
        logger.info("데이터베이스 생성 중...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS recommandstock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.success("✅ recommandstock 데이터베이스 생성 완료")

        # 3. 데이터베이스 선택
        cursor.execute("USE recommandstock")

        # 4. 스키마 파일 읽기
        schema_file = Path("db/schema.sql")
        if not schema_file.exists():
            logger.error(f"스키마 파일 없음: {schema_file}")
            return False

        logger.info(f"스키마 파일 로드 중: {schema_file}")
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # 5. SQL 문 정리 (주석 제거)
        lines = []
        for line in schema_sql.split('\n'):
            line = line.strip()
            # 주석 라인 제거
            if line.startswith('--') or not line:
                continue
            lines.append(line)

        # 세미콜론으로 분리
        cleaned_sql = ' '.join(lines)
        statements = [s.strip() for s in cleaned_sql.split(';') if s.strip()]

        logger.info(f"SQL 문 {len(statements)}개 실행 중...")
        for i, statement in enumerate(statements, 1):
            # CREATE USER 관련 문은 건너뛰기 (이미 존재)
            if 'CREATE USER' in statement.upper() or 'GRANT' in statement.upper() or 'FLUSH PRIVILEGES' in statement.upper():
                logger.debug(f"  [{i}/{len(statements)}] 사용자 관련 SQL 건너뛰기")
                continue

            try:
                cursor.execute(statement)
                logger.info(f"  [{i}/{len(statements)}] 실행 완료")
            except Exception as e:
                logger.warning(f"  [{i}/{len(statements)}] 실행 실패: {str(e)[:150]}")

        conn.commit()
        logger.success(f"✅ 테이블 스키마 적용 완료")

        # 6. 생성된 테이블 확인
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        logger.info("\n📊 생성된 테이블:")
        for table in tables:
            table_name = list(table.values())[0]
            logger.info(f"  - {table_name}")

        cursor.close()
        conn.close()

        logger.success("\n" + "=" * 60)
        logger.success("✅ 데이터베이스 설정 완료!")
        logger.success("=" * 60)
        logger.info(f"접속 정보:")
        logger.info(f"  jdbc:mariadb://{DB_CONFIG['host']}:{DB_CONFIG['port']}/recommandstock")
        logger.info(f"  User: {DB_CONFIG['user']}")
        logger.info(f"  Database: recommandstock")

        return True

    except pymysql.Error as e:
        logger.error(f"❌ MariaDB 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        return False


if __name__ == "__main__":
    success = setup_database()

    if success:
        logger.info("\n✨ 다음 단계:")
        logger.info("  1. docker-compose.yml 업데이트 완료")
        logger.info("  2. NAS에 적용: docker-compose up -d")
    else:
        logger.error("\n❌ 설정 실패")
