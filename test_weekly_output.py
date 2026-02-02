"""
금주 추천 출력 테스트 스크립트
실제 데이터 수집 없이 샘플 데이터로 JSON/TXT 파일 생성 테스트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime
from pathlib import Path

# run_weekly_recommendation의 save_results 함수 사용
from run_weekly_recommendation import save_results


def create_sample_data():
    """샘플 데이터 생성"""
    return {
        "generated_at": datetime.now().isoformat(),
        "schedule_time": "09:00",
        "market_overview": {
            "korea": {
                "KOSPI": {
                    "value": "2,580.50",
                    "change": "+15.30",
                    "change_rate": "+0.60"
                },
                "KOSDAQ": {
                    "value": "850.20",
                    "change": "+8.50",
                    "change_rate": "+1.01"
                }
            },
            "usa": {
                "S&P 500": {
                    "price": "4,850.20",
                    "change": "+25.30",
                    "change_percent": "+0.52"
                },
                "NASDAQ": {
                    "price": "15,200.50",
                    "change": "+100.50",
                    "change_percent": "+0.67"
                }
            }
        },
        "hot_themes": [
            {
                "rank": 1,
                "name": "AI반도체",
                "code": "001",
                "score": 87.5,
                "change_rate": "+3.2%",
                "daily_change": 3.2,
                "stock_count": 45,
                "tier1_stocks": [
                    {"name": "삼성전자", "ticker": "005930", "price": 75000, "change_rate": "+2.1%"},
                    {"name": "SK하이닉스", "ticker": "000660", "price": 150000, "change_rate": "+3.5%"},
                ],
                "tier2_stocks": [
                    {"name": "LG전자", "ticker": "066570", "price": 120000, "change_rate": "+1.8%"},
                ],
                "tier3_stocks": [
                    {"name": "삼성SDI", "ticker": "006400", "price": 450000, "change_rate": "+0.5%"},
                ],
                "news": [
                    {"title": "AI 반도체 시장 급성장, 삼성전자 HBM3 수주 확대"},
                    {"title": "SK하이닉스, 엔비디아와 차세대 AI 칩 개발 협력"},
                ]
            },
            {
                "rank": 2,
                "name": "2차전지",
                "code": "002",
                "score": 82.3,
                "change_rate": "+2.8%",
                "daily_change": 2.8,
                "stock_count": 38,
                "tier1_stocks": [
                    {"name": "LG에너지솔루션", "ticker": "373220", "price": 450000, "change_rate": "+3.2%"},
                    {"name": "삼성SDI", "ticker": "006400", "price": 450000, "change_rate": "+2.9%"},
                ],
                "tier2_stocks": [
                    {"name": "포스코퓨처엠", "ticker": "003670", "price": 300000, "change_rate": "+2.1%"},
                ],
                "tier3_stocks": [
                    {"name": "에코프로비엠", "ticker": "247540", "price": 200000, "change_rate": "+1.5%"},
                ],
                "news": [
                    {"title": "2차전지 수출 사상 최대, 북미 수요 급증"},
                    {"title": "LG에너지솔루션, 美 전기차 업체와 대규모 계약 체결"},
                ]
            }
        ],
        "weekly_recommendations": [
            {
                "ticker": "005930",
                "name": "삼성전자",
                "country": "KR",
                "current_price": 75000,
                "daily_change": 1500,
                "daily_change_rate": "+2.0%",
                "market_cap": "450조",
                "per": "15.2",
                "pbr": "1.8",
                "dividend_yield": "2.3%",
                "analyst_rating": {
                    "rating": "매수",
                    "target_price": "85,000원",
                    "analysts_count": 25,
                    "source": "네이버증권"
                },
                "chart_6m": {
                    "available": True,
                    "period": "6M",
                    "current": 75000,
                    "high_6m": 78000,
                    "low_6m": 65000,
                    "chart_url": "https://finance.naver.com/item/fchart.naver?code=005930"
                },
                "news": [
                    {"title": "삼성전자, HBM3E 양산 본격화... AI 반도체 수주 확대"},
                    {"title": "갤럭시 S25 사전예약 돌풍, 전작 대비 30% 증가"},
                ],
                "investment_points": [
                    "HBM3E 양산으로 AI 반도체 시장 선점",
                    "갤럭시 S25 흥행으로 모바일 부문 실적 개선",
                    "메모리 반도체 가격 반등 기대"
                ],
                "sector": "IT/반도체",
                "volume": 15000000,
                "score": 85.5
            },
            {
                "ticker": "NVDA",
                "name": "NVIDIA",
                "country": "US",
                "current_price": 880.50,
                "daily_change": 15.30,
                "daily_change_rate": "+1.77%",
                "market_cap": "$2.2T",
                "per": "45.5",
                "pbr": "22.3",
                "dividend_yield": "0.05%",
                "analyst_rating": {
                    "rating": "Strong Buy",
                    "target_price": "$1,050",
                    "analysts_count": 42,
                    "source": "Yahoo Finance"
                },
                "chart_6m": {
                    "available": True,
                    "period": "6M",
                    "current": 880.50,
                    "high_52w": 950.00,
                    "low_52w": 650.00,
                    "chart_url": "https://finance.yahoo.com/quote/NVDA/chart"
                },
                "news": [
                    {"title": "NVIDIA unveils next-gen Blackwell AI chips with 30% performance boost"},
                    {"title": "Major cloud providers expand NVIDIA GPU orders for AI infrastructure"},
                ],
                "investment_points": [
                    "AI chip demand continues to surge with Blackwell launch",
                    "Strong partnership ecosystem with major tech companies",
                    "Data center revenue growth accelerating"
                ],
                "sector": "Technology/Semiconductors",
                "volume": 45000000,
                "score": 88.2
            }
        ],
        "ai_recommendations": {
            "gemini": {
                "engine": "gemini",
                "analyzed_at": datetime.now().isoformat(),
                "market_analysis": {
                    "overall_sentiment": "긍정적",
                    "korea_outlook": "한국 시장은 AI 반도체와 2차전지 중심으로 견조한 상승세를 보이고 있습니다. 특히 HBM 수요 증가와 전기차 시장 확대가 긍정적 요인으로 작용하고 있습니다.",
                    "usa_outlook": "미국 시장은 빅테크 중심의 실적 개선과 AI 투자 확대로 강세를 지속하고 있습니다. 연준의 금리 인하 기대감도 긍정적입니다.",
                    "key_trends": [
                        "AI 반도체 수요 급증",
                        "전기차 및 2차전지 시장 확대",
                        "빅테크 실적 개선"
                    ],
                    "risks": [
                        "글로벌 경기 둔화 우려",
                        "반도체 재고 조정 가능성"
                    ]
                },
                "top_themes_analysis": [
                    {
                        "theme": "AI반도체",
                        "rating": "매우 강세",
                        "reasoning": "HBM3E 양산 본격화와 AI 서버 수요 급증으로 강력한 상승 모멘텀을 보유하고 있습니다.",
                        "recommended_stocks": ["삼성전자", "SK하이닉스", "NVIDIA"]
                    }
                ],
                "top_10_picks": [
                    {
                        "rank": 1,
                        "ticker": "NVDA",
                        "name": "NVIDIA",
                        "country": "US",
                        "action": "적극매수",
                        "target_return": "15-20%",
                        "reasoning": "AI 칩 시장의 절대 강자로서 Blackwell 아키텍처 출시와 데이터센터 수요 급증으로 실적 성장이 지속될 전망입니다. 클라우드 업체들의 대규모 주문이 확정되어 있습니다.",
                        "entry_price": "$860-880",
                        "target_price": "$1,050",
                        "stop_loss": "$800",
                        "investment_period": "중기(3개월)"
                    },
                    {
                        "rank": 2,
                        "ticker": "005930",
                        "name": "삼성전자",
                        "country": "KR",
                        "action": "매수",
                        "target_return": "10-15%",
                        "reasoning": "HBM3E 양산으로 AI 메모리 시장 점유율을 확대하고 있으며, 갤럭시 S25 흥행으로 모바일 부문도 개선되고 있습니다. 배당 수익률도 매력적입니다.",
                        "entry_price": "73,000-75,000원",
                        "target_price": "85,000원",
                        "stop_loss": "70,000원",
                        "investment_period": "중기(3개월)"
                    }
                ],
                "sector_recommendations": [
                    {
                        "sector": "AI/반도체",
                        "rating": "비중확대",
                        "reasoning": "AI 투자 확대와 메모리 반도체 가격 반등으로 업황 개선이 뚜렷합니다."
                    }
                ],
                "risk_warning": "반도체 업황은 변동성이 크며, 글로벌 경기 둔화 시 수요 감소 위험이 있습니다. 또한 미중 무역 갈등 재개 가능성도 주의해야 합니다.",
                "investment_strategy": "AI와 2차전지 중심의 포트폴리오를 구축하되, 빅테크와 국내 대형주로 안정성을 확보하는 전략을 권장합니다. 단기 변동성에 대비해 분할 매수를 실시하고, 10-15% 손절 라인을 설정하세요."
            },
            "groq": {
                "engine": "groq",
                "analyzed_at": datetime.now().isoformat(),
                "market_analysis": {
                    "overall_sentiment": "매우 긍정적",
                    "korea_outlook": "한국 시장은 AI 반도체 슈퍼사이클 진입으로 강력한 상승 모멘텀을 보유하고 있습니다. 2차전지도 북미 수요 확대로 호황이 지속될 전망입니다.",
                    "usa_outlook": "미국 시장은 AI 혁명의 중심에 있으며, 빅테크의 막강한 실적이 시장을 견인하고 있습니다. 금리 인하 사이클 진입 시 추가 상승 여력이 큽니다.",
                    "key_trends": [
                        "AI 혁명 가속화",
                        "HBM 메모리 슈퍼사이클",
                        "전기차 대중화"
                    ],
                    "risks": [
                        "밸류에이션 부담",
                        "지정학적 리스크"
                    ]
                },
                "top_themes_analysis": [
                    {
                        "theme": "AI반도체",
                        "rating": "강세",
                        "reasoning": "생성형 AI 확산과 데이터센터 투자 급증으로 반도체 수요가 폭발적으로 증가하고 있습니다.",
                        "recommended_stocks": ["NVIDIA", "삼성전자", "SK하이닉스"]
                    }
                ],
                "top_10_picks": [
                    {
                        "rank": 1,
                        "ticker": "005930",
                        "name": "삼성전자",
                        "country": "KR",
                        "action": "적극매수",
                        "target_return": "20-25%",
                        "reasoning": "HBM3E 독점 공급으로 AI 메모리 시장을 장악하고 있으며, 파운드리 사업도 턴어라운드 중입니다. 현재 밸류에이션은 역사적 저점 수준입니다.",
                        "entry_price": "74,000-76,000원",
                        "target_price": "90,000원",
                        "stop_loss": "68,000원",
                        "investment_period": "장기(6개월+)"
                    },
                    {
                        "rank": 2,
                        "ticker": "NVDA",
                        "name": "NVIDIA",
                        "country": "US",
                        "action": "매수",
                        "target_return": "12-18%",
                        "reasoning": "AI 칩 시장 점유율 90% 이상으로 독점적 지위를 유지하고 있습니다. Blackwell 출시로 성능과 수익성이 모두 개선됩니다.",
                        "entry_price": "$870-890",
                        "target_price": "$1,000",
                        "stop_loss": "$820",
                        "investment_period": "중기(3개월)"
                    }
                ],
                "sector_recommendations": [
                    {
                        "sector": "AI/반도체",
                        "rating": "비중확대",
                        "reasoning": "AI 투자 붐이 본격화되면서 반도체 슈퍼사이클이 시작되었습니다."
                    }
                ],
                "risk_warning": "AI 테마주의 밸류에이션이 높은 수준이므로 단기 조정 가능성에 유의해야 합니다. 기술주 특성상 변동성이 크므로 리스크 관리가 필수적입니다.",
                "investment_strategy": "AI 반도체를 핵심 포지션으로 하되, 2차전지와 빅테크로 분산 투자하세요. Gemini보다 공격적인 목표가를 제시하므로, 장기 투자 관점에서 삼성전자 비중을 높이는 것을 추천합니다."
            }
        }
    }


def main():
    print("=" * 100)
    print("  📊 금주 추천 출력 테스트")
    print("=" * 100)
    print("\n샘플 데이터로 JSON/TXT 파일 생성 테스트...\n")

    # 샘플 데이터 생성
    sample_data = create_sample_data()

    # 파일 저장
    output_dir = Path(__file__).parent / "output"
    json_file, txt_file = save_results(sample_data, output_dir)

    print("\n" + "=" * 100)
    print("  ✅ 파일 생성 완료!")
    print("=" * 100)
    print(f"\n📄 JSON 파일: {json_file}")
    print(f"📄 TXT 파일:  {txt_file}")
    print("\n생성된 파일을 확인해보세요:")
    print(f"  cat {txt_file}")
    print(f"  cat {json_file} | jq")
    print()


if __name__ == "__main__":
    main()
