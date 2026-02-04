"""
Weekly Recommendation 데이터 보강
- 테마 카테고리 매핑
- 실시간 주가 데이터 추가 (optional)
- RecommandStock 프론트엔드 형식으로 변환
"""
import json
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Dict, List, Optional


def load_theme_categories() -> Dict[str, str]:
    """수집된 테마 카테고리 로드"""
    category_file = Path("data/theme_categories.json")

    if not category_file.exists():
        logger.warning(f"테마 카테고리 파일 없음: {category_file}")
        return {}

    with open(category_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 테마명 -> 카테고리 매핑
    category_map = {}
    for theme in data.get("themes", []):
        theme_name = theme["name"]
        category = theme.get("category", "기타")
        theme_id = theme.get("id", "")

        category_map[theme_name] = {
            "id": theme_id,
            "category": category
        }

    logger.info(f"테마 카테고리 {len(category_map)}개 로드")
    return category_map


def generate_theme_description(theme_name: str, news_count: int, change_rate: str) -> str:
    """테마 설명 자동 생성"""
    descriptions = {
        "AI": "인공지능 관련 기술 및 서비스가 주목받고 있는 테마입니다.",
        "반도체": "반도체 제조 및 장비 관련 기업들의 실적이 개선되고 있습니다.",
        "전지": "2차전지 및 배터리 소재 관련 수요가 증가하고 있습니다.",
        "배터리": "전기차 배터리 관련 기업들이 성장하고 있습니다.",
        "방산": "방위산업 및 국방 관련 수주가 증가하고 있습니다.",
        "우주": "우주항공산업 육성 정책으로 관련주가 주목받고 있습니다.",
        "바이오": "바이오 의약품 개발 진행으로 관심이 높아지고 있습니다.",
        "게임": "게임 산업의 성장과 함께 관련주가 주목받고 있습니다.",
        "건설": "건설 및 부동산 관련 정책으로 관심이 증가하고 있습니다.",
    }

    base_desc = f"{theme_name} 관련 종목들이 시장의 관심을 받고 있습니다."

    # 키워드 기반 설명
    for keyword, desc in descriptions.items():
        if keyword in theme_name:
            base_desc = desc
            break

    # 뉴스와 등락률 정보 추가
    if news_count and news_count > 0:
        base_desc += f" 최근 {news_count}건의 관련 뉴스가 보도되었으며, "
    else:
        base_desc += " "

    if "+" in str(change_rate):
        base_desc += f"평균 {change_rate} 상승세를 보이고 있습니다."
    elif "-" in str(change_rate):
        base_desc += f"평균 {change_rate} 조정을 받고 있습니다."
    else:
        base_desc += "보합세를 보이고 있습니다."

    return base_desc


def find_best_category_match(theme_name: str, category_map: Dict) -> Dict:
    """테마명과 가장 유사한 카테고리 찾기"""
    # 정확히 일치하는 경우
    if theme_name in category_map:
        return category_map[theme_name]

    # 부분 일치하는 경우 (가장 긴 일치)
    best_match = None
    best_length = 0

    for cat_theme_name, cat_info in category_map.items():
        # 양방향으로 확인
        if cat_theme_name in theme_name or theme_name in cat_theme_name:
            match_length = min(len(cat_theme_name), len(theme_name))
            if match_length > best_length:
                best_length = match_length
                best_match = cat_info

    if best_match:
        return best_match

    # 매칭 실패 시 기본값
    return {
        "id": theme_name.lower().replace(" ", "-")[:30],
        "category": "기타"
    }


def enrich_weekly_recommendation(input_file: Path, output_file: Path):
    """Weekly Recommendation JSON 보강"""
    logger.info("=" * 60)
    logger.info(f"데이터 보강 시작: {input_file.name}")
    logger.info("=" * 60)

    # 1. 원본 데이터 로드
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 2. 테마 카테고리 로드
    category_map = load_theme_categories()

    # 3. Hot Themes 중복 제거
    seen_themes = set()
    unique_themes = []

    for theme in data.get("hot_themes", []):
        theme_name = theme.get("name", "")
        if theme_name and theme_name not in seen_themes:
            seen_themes.add(theme_name)
            unique_themes.append(theme)

    logger.info(f"중복 제거: {len(data.get('hot_themes', []))}개 → {len(unique_themes)}개")

    # 4. Hot Themes 보강
    enriched_themes = []

    for i, theme in enumerate(unique_themes[:30]):  # 상위 30개
        theme_name = theme.get("name", "")
        logger.info(f"  [{i+1}/30] 테마 보강: {theme_name}")

        # 카테고리 매칭
        cat_info = find_best_category_match(theme_name, category_map)

        # 등락률 파싱
        change_rate_str = str(theme.get("change_rate", "0%"))
        try:
            change_percent = float(change_rate_str.replace("%", "").replace("+", "").strip())
        except:
            change_percent = 0.0

        # 점수
        score = theme.get("score", 0)

        # 보강된 테마 데이터
        enriched_theme = {
            "id": cat_info["id"],
            "name": theme_name,
            "rank": i + 1,
            "score": score,
            "previousScore": max(0, score - 10),  # 임시: 이전 점수는 -10
            "changePercent": change_percent,
            "trend": "up" if change_percent > 0 else ("down" if change_percent < 0 else "stable"),
            "category": cat_info["category"],
            "description": generate_theme_description(
                theme_name,
                theme.get("news_count"),
                change_rate_str
            ),
        }

        # 관련주 수 계산
        tier1_stocks = theme.get("tier1_stocks", [])
        tier2_stocks = theme.get("tier2_stocks", [])
        tier3_stocks = theme.get("tier3_stocks", [])

        enriched_theme["relatedStockCount"] = len(tier1_stocks) + len(tier2_stocks) + len(tier3_stocks)

        # Top 종목 (tier1에서 3개)
        top_stock_names = [s.get("name", "") for s in tier1_stocks[:3] if s.get("name")]
        enriched_theme["topStocks"] = top_stock_names

        # 뉴스 수
        enriched_theme["newsCount"] = theme.get("news_count") or 0

        # 평균 수익률 (임시: 등락률 기반)
        enriched_theme["avgReturn"] = round(change_percent, 2)

        # 티어별 관련주 상세 정보 (간소화)
        enriched_theme["relatedStocks"] = {
            "tier1": [
                {
                    "name": s.get("name", ""),
                    "ticker": s.get("ticker", ""),
                    "changeRate": s.get("change_rate", "0%"),
                    "tier": "1차",
                    "isPremium": False
                }
                for s in tier1_stocks[:10]  # 상위 10개
            ],
            "tier2": [
                {
                    "name": s.get("name", ""),
                    "ticker": s.get("ticker", ""),
                    "changeRate": s.get("change_rate", "0%"),
                    "tier": "2차",
                    "isPremium": False
                }
                for s in tier2_stocks[:10]
            ],
            "tier3": [
                {
                    "name": s.get("name", ""),
                    "ticker": s.get("ticker", ""),
                    "changeRate": s.get("change_rate", "0%"),
                    "tier": "3차",
                    "isPremium": True  # 3차는 프리미엄
                }
                for s in tier3_stocks[:10]
            ]
        }

        enriched_themes.append(enriched_theme)

    # 4. 최종 데이터 구성
    enriched_data = {
        "generated_at": datetime.now().isoformat(),
        "source_file": input_file.name,
        "data_version": "1.0",
        "themes": enriched_themes,
        "weekly_recommendations": data.get("weekly_recommendations", [])[:30],
        "ai_analysis": data.get("ai_recommendations", {}),
        "market_overview": data.get("market_overview", {}),
    }

    # 5. 저장
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)

    logger.success(f"✅ 데이터 보강 완료: {output_file}")
    logger.info(f"   테마: {len(enriched_themes)}개")
    logger.info(f"   추천 종목: {len(enriched_data['weekly_recommendations'])}개")

    # 6. 카테고리별 통계
    category_counts = {}
    for theme in enriched_themes:
        cat = theme["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    logger.info("\n📊 카테고리별 테마 분포:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   {cat}: {count}개")

    return enriched_data


def main():
    """메인 함수"""
    # 최신 weekly JSON 찾기
    output_dir = Path("output")
    weekly_files = sorted(output_dir.glob("weekly_recommendation_*.json"), reverse=True)

    if not weekly_files:
        logger.error("weekly_recommendation JSON 파일을 찾을 수 없습니다")
        logger.info("먼저 python run_weekly_recommendation.py 를 실행하세요")
        return

    latest_file = weekly_files[0]

    # 보강된 데이터 저장 경로
    enriched_file = output_dir / f"enriched_{latest_file.name}"

    # 데이터 보강 실행
    enriched_data = enrich_weekly_recommendation(latest_file, enriched_file)

    logger.success("\n" + "=" * 60)
    logger.success("✨ 모든 데이터 보강 완료!")
    logger.success("=" * 60)
    logger.info(f"원본 파일: {latest_file}")
    logger.info(f"보강 파일: {enriched_file}")
    logger.info(f"\n다음 단계:")
    logger.info(f"  1. API 서버 시작: python web_server.py")
    logger.info(f"  2. 보강된 데이터 확인: cat {enriched_file}")


if __name__ == "__main__":
    main()
