"""
데이터 파일 목록 및 상세 정보 API
"""
import os
import json
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, HTTPException
from loguru import logger

router = APIRouter(prefix="/data-files", tags=["data-files"])

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def get_file_info(filepath: str) -> Dict:
    """파일 정보 추출"""
    try:
        # 파일 통계
        stat = os.stat(filepath)
        file_size = stat.st_size
        modified_time = datetime.fromtimestamp(stat.st_mtime)

        # JSON 내용 로드
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 기본 정보
        filename = os.path.basename(filepath)
        file_type = "recommendation" if "ai_recommendation" in filename else "growth"

        info = {
            "filename": filename,
            "filepath": filepath,
            "fileType": file_type,
            "fileSize": file_size,
            "fileSizeFormatted": format_file_size(file_size),
            "modifiedAt": modified_time.isoformat(),
            "generatedAt": data.get("generated_at", ""),
            "engine": data.get("engine", "unknown"),
        }

        # 추천 데이터 상세
        if file_type == "recommendation":
            korea_recs = data.get("recommendations", {}).get("korea", [])
            usa_recs = data.get("recommendations", {}).get("usa", [])

            info.update({
                "stockCount": {
                    "korea": len(korea_recs),
                    "usa": len(usa_recs),
                    "total": len(korea_recs) + len(usa_recs),
                },
                "topPicksCount": len(data.get("top_picks", [])),
                "sectorsCount": len(data.get("sector_analysis", [])),
                "marketSentiment": data.get("market_overview", {}).get("sentiment", "neutral"),
                "marketTrend": data.get("market_overview", {}).get("trend", "neutral"),
            })

        # 급등 예측 데이터 상세
        elif file_type == "growth":
            korea_picks = data.get("korea_picks", [])
            usa_picks = data.get("usa_picks", [])
            theme_picks = data.get("theme_picks", [])

            info.update({
                "stockCount": {
                    "korea": len(korea_picks),
                    "usa": len(usa_picks),
                    "total": len(korea_picks) + len(usa_picks),
                },
                "themesCount": len(theme_picks),
            })

        return info

    except Exception as e:
        logger.error(f"파일 정보 추출 실패: {filepath}: {e}")
        return None


def format_file_size(size_bytes: int) -> str:
    """파일 크기 포맷팅"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.get("/list")
def list_data_files():
    """생성된 데이터 파일 목록 조회"""
    try:
        if not os.path.exists(OUTPUT_DIR):
            return {"files": []}

        files = []

        # ai_recommendation 파일들
        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith(".json") and (
                filename.startswith("ai_recommendation_") or
                filename.startswith("growth_prediction_")
            ):
                filepath = os.path.join(OUTPUT_DIR, filename)
                file_info = get_file_info(filepath)
                if file_info:
                    files.append(file_info)

        # 수정 시간 기준 내림차순 정렬
        files.sort(key=lambda x: x["modifiedAt"], reverse=True)

        return {
            "files": files,
            "totalCount": len(files),
            "outputDir": OUTPUT_DIR,
        }

    except Exception as e:
        logger.error(f"파일 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail/{filename}")
def get_file_detail(filename: str):
    """특정 파일 상세 정보 조회"""
    try:
        filepath = os.path.join(OUTPUT_DIR, filename)

        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
    except Exception as e:
        logger.error(f"파일 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
