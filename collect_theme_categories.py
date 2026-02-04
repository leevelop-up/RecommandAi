"""
실제 주식 데이터에서 테마와 카테고리를 수집
- pykrx로 업종 정보 수집
- 네이버 금융에서 테마 목록 크롤링
- AI로 카테고리 자동 분류
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import Dict, List
from pathlib import Path
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()


def crawl_naver_themes() -> List[Dict]:
    """네이버 금융에서 테마 목록 크롤링"""
    logger.info("네이버 금융 테마 수집 시작...")

    url = "https://finance.naver.com/sise/theme.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        themes = []
        table = soup.select_one('table.type_1')

        if not table:
            logger.error("테마 테이블을 찾을 수 없습니다")
            return []

        rows = table.select('tr')[2:]  # 헤더 제외

        for row in rows:
            cols = row.select('td')
            if len(cols) < 4:
                continue

            # 테마명
            theme_link = cols[0].select_one('a')
            if not theme_link:
                continue

            theme_name = theme_link.text.strip()
            theme_url = theme_link.get('href', '')

            # 등락률
            change_elem = cols[2]
            change_text = change_elem.text.strip()

            # 거래량
            volume_elem = cols[3]
            volume_text = volume_elem.text.strip()

            themes.append({
                "name": theme_name,
                "url": f"https://finance.naver.com{theme_url}",
                "change_rate": change_text,
                "volume": volume_text,
            })

        logger.success(f"네이버 금융 테마 {len(themes)}개 수집 완료")
        return themes

    except Exception as e:
        logger.error(f"네이버 금융 크롤링 실패: {e}")
        return []


def categorize_themes_with_ai(themes: List[Dict]) -> List[Dict]:
    """AI를 사용하여 테마를 카테고리별로 분류"""
    logger.info("AI로 테마 카테고리 분류 시작...")

    # Gemini API 사용
    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google.generativeai 모듈 없음. 규칙 기반 분류 사용")
        return classify_themes_by_rules(themes)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY 없음. 기본 분류 사용")
        return classify_themes_by_rules(themes)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # 테마명 리스트 준비
        theme_names = [t["name"] for t in themes[:50]]  # 최대 50개

        prompt = f"""
다음은 한국 주식 시장의 테마 목록입니다. 각 테마를 적절한 카테고리로 분류해주세요.

테마 목록:
{', '.join(theme_names)}

다음 카테고리 중 하나로 분류:
- IT: 정보기술, AI, 반도체, 소프트웨어, 인터넷, 게임
- 에너지: 전지, 배터리, 신재생에너지, 태양광, 수소
- 방위산업: 방산, 국방, 우주항공, 드론
- 헬스케어: 바이오, 제약, 의료기기, 건강식품
- 금융: 은행, 증권, 보험, 핀테크
- 제조: 자동차, 로봇, 기계, 조선
- 유통: 이커머스, 물류, 유통
- 엔터: 게임, 엔터테인먼트, 미디어, 콘텐츠
- 건설: 부동산, 건설, 인프라
- 소재: 화학, 철강, 소재
- 기타: 위 카테고리에 속하지 않는 것

JSON 형식으로 출력:
{{
  "테마명": "카테고리",
  ...
}}
"""

        response = model.generate_content(prompt)
        result_text = response.text.strip()

        # JSON 파싱
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        category_map = json.loads(result_text)

        # 테마에 카테고리 추가
        for theme in themes:
            theme["category"] = category_map.get(theme["name"], "기타")

        logger.success(f"AI 카테고리 분류 완료: {len(category_map)}개")
        return themes

    except Exception as e:
        logger.error(f"AI 분류 실패: {e}")
        return classify_themes_by_rules(themes)


def classify_themes_by_rules(themes: List[Dict]) -> List[Dict]:
    """규칙 기반으로 테마 카테고리 분류"""
    logger.info("규칙 기반 테마 분류 시작...")

    # 키워드 기반 카테고리 매핑
    category_keywords = {
        "IT": ["AI", "반도체", "메모리", "시스템반도체", "소프트웨어", "인터넷", "클라우드",
               "빅데이터", "사이버", "메타버스", "NFT", "블록체인"],
        "에너지": ["전지", "배터리", "태양광", "풍력", "수소", "신재생", "ESS"],
        "방위산업": ["방산", "국방", "우주", "항공", "드론", "위성"],
        "헬스케어": ["바이오", "제약", "의료", "진단", "치료제", "백신", "병원"],
        "금융": ["은행", "증권", "보험", "카드", "핀테크", "금융"],
        "제조": ["자동차", "전기차", "로봇", "기계", "조선", "철강"],
        "유통": ["이커머스", "물류", "배송", "유통", "리테일"],
        "엔터": ["게임", "엔터", "콘텐츠", "미디어", "방송", "음악", "영화"],
        "건설": ["부동산", "건설", "인프라", "스마트시티", "리모델링"],
        "소재": ["화학", "소재", "신소재", "플라스틱", "섬유"],
    }

    for theme in themes:
        theme_name = theme["name"]
        assigned = False

        for category, keywords in category_keywords.items():
            if any(keyword in theme_name for keyword in keywords):
                theme["category"] = category
                assigned = True
                break

        if not assigned:
            theme["category"] = "기타"

    logger.success(f"규칙 기반 분류 완료: {len(themes)}개")
    return themes


def generate_theme_slug(theme_name: str) -> str:
    """테마명을 URL 친화적인 slug로 변환"""
    # 자주 사용되는 한글-영어 매핑
    common_translations = {
        "AI": "ai",
        "인공지능": "ai",
        "반도체": "semiconductor",
        "메모리": "memory",
        "전지": "battery",
        "배터리": "battery",
        "2차전지": "secondary-battery",
        "방산": "defense",
        "국방": "defense",
        "우주": "space",
        "항공": "aerospace",
        "바이오": "bio",
        "제약": "pharmaceutical",
        "자동차": "automobile",
        "전기차": "ev",
        "게임": "game",
        "엔터": "entertainment",
        "부동산": "real-estate",
        "건설": "construction",
        "로봇": "robot",
        "드론": "drone",
    }

    # 가장 긴 매칭부터 시도
    for kr, en in sorted(common_translations.items(), key=lambda x: len(x[0]), reverse=True):
        if kr in theme_name:
            # 나머지 부분도 변환
            remaining = theme_name.replace(kr, "")
            if remaining:
                for kr2, en2 in common_translations.items():
                    if kr2 in remaining:
                        return f"{en}-{en2}"
            return en

    # 매핑 없으면 단순 변환
    import unicodedata
    slug = theme_name.lower()
    slug = ''.join(c if c.isalnum() or c in ['-', ' '] else '' for c in slug)
    slug = slug.replace(' ', '-')
    return slug[:50]  # 최대 50자


def save_theme_categories(output_file: Path = Path("data/theme_categories.json")):
    """테마 카테고리 데이터 수집 및 저장"""
    logger.info("=" * 60)
    logger.info("테마 카테고리 수집 시작")
    logger.info("=" * 60)

    # 1. 네이버 금융에서 테마 크롤링
    themes = crawl_naver_themes()

    if not themes:
        logger.error("테마를 수집하지 못했습니다")
        return

    # 상위 30개만 선택 (거래량 기준 정렬)
    themes = themes[:30]

    # 2. AI로 카테고리 분류
    themes = categorize_themes_with_ai(themes)

    # 3. Slug 생성
    for theme in themes:
        theme["id"] = generate_theme_slug(theme["name"])

    # 4. 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "collected_at": __import__('datetime').datetime.now().isoformat(),
            "total_count": len(themes),
            "themes": themes
        }, f, ensure_ascii=False, indent=2)

    logger.success(f"✅ 테마 카테고리 저장 완료: {output_file}")
    logger.info(f"총 {len(themes)}개 테마 수집")

    # 카테고리별 통계
    category_counts = {}
    for theme in themes:
        cat = theme.get("category", "기타")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    logger.info("\n📊 카테고리별 통계:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {cat}: {count}개")

    return themes


if __name__ == "__main__":
    themes = save_theme_categories()

    # 결과 미리보기
    if themes:
        logger.info("\n✨ 수집된 테마 샘플 (상위 5개):")
        for i, theme in enumerate(themes[:5], 1):
            logger.info(f"\n{i}. {theme['name']}")
            logger.info(f"   ID: {theme['id']}")
            logger.info(f"   카테고리: {theme['category']}")
            logger.info(f"   등락률: {theme['change_rate']}")
