-- ============================================================
-- RecommandAi 데이터베이스 테이블 생성 스크립트
-- ============================================================

-- 데이터베이스 생성 (선택사항)
-- CREATE DATABASE IF NOT EXISTS recommandai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE recommandai;

-- ============================================================
-- 1. 테마 정보 테이블 (themes)
-- ============================================================
CREATE TABLE IF NOT EXISTS themes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'PK',
    theme_code VARCHAR(50) NOT NULL UNIQUE COMMENT '네이버 테마 코드',
    theme_name VARCHAR(200) NOT NULL COMMENT '테마명',
    stock_count INT DEFAULT 0 COMMENT '관련주 갯수',
    theme_score DECIMAL(5,2) DEFAULT 0.0 COMMENT '테마 점수 (0-100)',
    change_rate VARCHAR(20) COMMENT '테마 등락률 (예: +5.2%)',
    daily_change DECIMAL(10,2) DEFAULT 0.0 COMMENT '일일 변동 (숫자)',
    avg_return_rate DECIMAL(10,2) DEFAULT 0.0 COMMENT '평균 수익률 (%)',
    news_count INT DEFAULT 0 COMMENT '뉴스 건수',
    rank INT DEFAULT 0 COMMENT '순위',
    is_active BOOLEAN DEFAULT TRUE COMMENT '활성 여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '등록날짜',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정날짜',

    INDEX idx_theme_code (theme_code),
    INDEX idx_theme_score (theme_score DESC),
    INDEX idx_rank (rank),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='테마 정보 테이블';

-- ============================================================
-- 2. 종목 정보 테이블 (stocks)
-- ============================================================
CREATE TABLE IF NOT EXISTS stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'PK',
    stock_code VARCHAR(20) NOT NULL UNIQUE COMMENT '종목코드/티커',
    stock_name VARCHAR(200) NOT NULL COMMENT '종목명',
    country CHAR(2) DEFAULT 'KR' COMMENT '국가 (KR/US)',
    market VARCHAR(20) COMMENT '시장 (KOSPI/KOSDAQ/NYSE 등)',
    sector VARCHAR(100) COMMENT '섹터',
    current_price DECIMAL(15,2) DEFAULT 0.0 COMMENT '현재가',
    price_change DECIMAL(15,2) DEFAULT 0.0 COMMENT '전일대비 상승값',
    change_rate VARCHAR(20) COMMENT '등락률 (예: +2.5%)',
    bid_price DECIMAL(15,2) DEFAULT 0.0 COMMENT '매수호가',
    ask_price DECIMAL(15,2) DEFAULT 0.0 COMMENT '매도호가',
    volume BIGINT DEFAULT 0 COMMENT '거래량',
    market_cap BIGINT DEFAULT 0 COMMENT '시가총액',
    per DECIMAL(10,2) COMMENT 'PER (주가수익비율)',
    pbr DECIMAL(10,2) COMMENT 'PBR (주가순자산비율)',
    eps DECIMAL(15,2) COMMENT 'EPS (주당순이익)',
    dividend_yield DECIMAL(5,2) COMMENT '배당률 (%)',
    week52_high DECIMAL(15,2) COMMENT '52주 최고가',
    week52_low DECIMAL(15,2) COMMENT '52주 최저가',
    analyst_rating VARCHAR(50) COMMENT '애널리스트 평가',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '등록날짜',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '수정날짜',

    INDEX idx_stock_code (stock_code),
    INDEX idx_country (country),
    INDEX idx_market (market),
    INDEX idx_sector (sector),
    INDEX idx_current_price (current_price DESC),
    INDEX idx_market_cap (market_cap DESC),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='종목 정보 테이블';

-- ============================================================
-- 3. 테마-종목 연결 테이블 (theme_stocks)
-- ============================================================
CREATE TABLE IF NOT EXISTS theme_stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'PK',
    theme_id BIGINT NOT NULL COMMENT '테마 ID (FK)',
    stock_id BIGINT NOT NULL COMMENT '종목 ID (FK)',
    stock_code VARCHAR(20) NOT NULL COMMENT '종목 코드',
    stock_name VARCHAR(200) NOT NULL COMMENT '종목명',
    tier TINYINT NOT NULL COMMENT '티어 (1:1차, 2:2차, 3:3차)',
    stock_price DECIMAL(15,2) DEFAULT 0.0 COMMENT '당시 가격 (스냅샷)',
    stock_change_rate VARCHAR(20) COMMENT '해당 테마에서의 등락률',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '등록날짜',

    FOREIGN KEY (theme_id) REFERENCES themes(id) ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE,

    INDEX idx_theme_id (theme_id),
    INDEX idx_stock_id (stock_id),
    INDEX idx_tier (tier),
    INDEX idx_created_at (created_at),
    UNIQUE KEY unique_theme_stock (theme_id, stock_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='테마-종목 연결 테이블';

-- ============================================================
-- 4. 뉴스 테이블 (news)
-- ============================================================
CREATE TABLE IF NOT EXISTS news (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'PK',
    title TEXT NOT NULL COMMENT '제목',
    link VARCHAR(500) UNIQUE COMMENT '링크',
    source VARCHAR(100) COMMENT '출처',
    description TEXT COMMENT '요약/설명',
    published_at TIMESTAMP NULL COMMENT '발행일',
    theme_id BIGINT NULL COMMENT '테마 ID (FK, nullable)',
    stock_id BIGINT NULL COMMENT '종목 ID (FK, nullable)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '등록날짜',

    FOREIGN KEY (theme_id) REFERENCES themes(id) ON DELETE SET NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE SET NULL,

    INDEX idx_theme_id (theme_id),
    INDEX idx_stock_id (stock_id),
    INDEX idx_source (source),
    INDEX idx_published_at (published_at DESC),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='뉴스 테이블';

-- ============================================================
-- 5. 수익률 히스토리 테이블 (return_history)
-- ============================================================
CREATE TABLE IF NOT EXISTS return_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT 'PK',
    target_type ENUM('theme', 'stock') NOT NULL COMMENT '대상 타입 (theme/stock)',
    target_id BIGINT NOT NULL COMMENT '대상 ID (themes.id 또는 stocks.id)',
    date DATE NOT NULL COMMENT '날짜',
    return_rate DECIMAL(10,2) DEFAULT 0.0 COMMENT '수익률 (%)',
    price DECIMAL(15,2) DEFAULT 0.0 COMMENT '가격 (종목인 경우)',
    volume BIGINT DEFAULT 0 COMMENT '거래량 (종목인 경우)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '등록날짜',

    INDEX idx_target (target_type, target_id),
    INDEX idx_date (date DESC),
    INDEX idx_created_at (created_at),
    UNIQUE KEY unique_target_date (target_type, target_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='수익률 히스토리 테이블';

-- ============================================================
-- 추가 유용한 뷰 (View) 생성
-- ============================================================

-- 테마별 최고 수익률 종목 뷰
CREATE OR REPLACE VIEW v_theme_top_stocks AS
SELECT
    t.id AS theme_id,
    t.theme_name,
    ts.stock_code,
    ts.stock_name,
    ts.tier,
    s.change_rate,
    s.current_price,
    s.volume,
    ts.created_at
FROM themes t
INNER JOIN theme_stocks ts ON t.id = ts.theme_id
INNER JOIN stocks s ON ts.stock_id = s.id
WHERE ts.tier = 1  -- 1차 관련주만
ORDER BY t.theme_score DESC, s.change_rate DESC;

-- 활성 테마 순위 뷰
CREATE OR REPLACE VIEW v_active_themes_rank AS
SELECT
    id,
    theme_code,
    theme_name,
    theme_score,
    stock_count,
    change_rate,
    news_count,
    rank,
    created_at,
    updated_at
FROM themes
WHERE is_active = TRUE
ORDER BY rank ASC, theme_score DESC;

-- 종목별 소속 테마 개수 뷰
CREATE OR REPLACE VIEW v_stock_theme_count AS
SELECT
    s.id AS stock_id,
    s.stock_code,
    s.stock_name,
    s.country,
    s.current_price,
    s.change_rate,
    COUNT(ts.theme_id) AS theme_count,
    GROUP_CONCAT(DISTINCT t.theme_name SEPARATOR ', ') AS themes
FROM stocks s
LEFT JOIN theme_stocks ts ON s.id = ts.stock_id
LEFT JOIN themes t ON ts.theme_id = t.id
GROUP BY s.id, s.stock_code, s.stock_name, s.country, s.current_price, s.change_rate;

-- ============================================================
-- 완료
-- ============================================================
