-- RecommandStock DB 스키마
-- JSON 파일 구조와 완전히 호환되도록 설계

-- 사용자 생성 및 권한 부여
CREATE USER IF NOT EXISTS 'merong2969'@'%' IDENTIFIED BY 'cpz8377!@#';
GRANT ALL PRIVILEGES ON recommand_stock.* TO 'merong2969'@'%';
FLUSH PRIVILEGES;

-- 종목 마스터 테이블
CREATE TABLE IF NOT EXISTS stocks (
    ticker VARCHAR(20) PRIMARY KEY,
    kr_name VARCHAR(100) NOT NULL,
    en_name VARCHAR(100),
    sector VARCHAR(50),
    market VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- AI 추천 결과 (메타 정보)
CREATE TABLE IF NOT EXISTS ai_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    generated_at TIMESTAMP NOT NULL,
    engine VARCHAR(50),
    market_summary TEXT,
    market_sentiment VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_generated_at (generated_at)
);

-- 추천 종목 상세
CREATE TABLE IF NOT EXISTS recommendation_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recommendation_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    price DECIMAL(15, 2),
    change_amount DECIMAL(15, 2),
    change_percent DECIMAL(8, 4),
    recommendation VARCHAR(20),
    score INT,
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (recommendation_id) REFERENCES ai_recommendations(id) ON DELETE CASCADE,
    INDEX idx_ticker (ticker)
);

-- 뉴스
CREATE TABLE IF NOT EXISTS news (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    link VARCHAR(500) UNIQUE NOT NULL,
    source VARCHAR(100),
    published TIMESTAMP,
    ticker VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ticker (ticker),
    INDEX idx_published (published)
);
